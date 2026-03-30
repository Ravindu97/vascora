CREATE SCHEMA IF NOT EXISTS marts;

CREATE OR REPLACE VIEW marts.store_coverage AS
SELECT
    s.licence_number AS store_id,
    s.store_name,
    s.licence_holder_name,
    s.street_address,
    s.city,
    s.province,
    s.postal_code,
    s.phone_number,
    s.website_url,
    s.latitude,
    s.longitude,
    s.distance_km,
    s.within_35km,
    s.hours_of_operation,
    s.is_active,
    s.scraped_at,
    COUNT(DISTINCT p.id) FILTER (WHERE p.is_active) AS active_product_count
FROM raw.agco_stores s
LEFT JOIN raw.store_products p ON p.licence_number = s.licence_number
GROUP BY
    s.licence_number,
    s.store_name,
    s.licence_holder_name,
    s.street_address,
    s.city,
    s.province,
    s.postal_code,
    s.phone_number,
    s.website_url,
    s.latitude,
    s.longitude,
    s.distance_km,
    s.within_35km,
    s.hours_of_operation,
    s.is_active,
    s.scraped_at;

CREATE OR REPLACE VIEW marts.product_matrix AS
WITH normalized AS (
    SELECT
        p.licence_number,
        COALESCE(NULLIF(TRIM(p.brand_name), ''), 'Unknown Brand') AS brand_name,
        TRIM(p.product_name) AS product_name,
        LOWER(COALESCE(NULLIF(TRIM(p.category_raw), ''), 'other')) AS category,
        COALESCE(p.ocs_sku, '') AS ocs_sku,
        p.is_active,
        p.in_stock
    FROM raw.store_products p
),
active_stores AS (
    SELECT COUNT(*)::NUMERIC AS total_active_stores
    FROM raw.agco_stores
    WHERE is_active = true
      AND within_35km = true
)
SELECT
    n.brand_name,
    n.product_name,
    n.category,
    NULLIF(n.ocs_sku, '') AS ocs_sku,
    COUNT(DISTINCT n.licence_number) FILTER (WHERE n.is_active) AS store_count,
    ROUND(
        (COUNT(DISTINCT n.licence_number) FILTER (WHERE n.is_active)
        / NULLIF((SELECT total_active_stores FROM active_stores), 0)) * 100,
        2
    ) AS ubiquity_score,
    COUNT(*) FILTER (WHERE n.in_stock) AS in_stock_records
FROM normalized n
JOIN raw.agco_stores s ON s.licence_number = n.licence_number
WHERE s.within_35km = true
  AND s.is_active = true
GROUP BY
    n.brand_name,
    n.product_name,
    n.category,
    NULLIF(n.ocs_sku, '');

CREATE OR REPLACE VIEW marts.price_volatility AS
WITH pricing_90d AS (
    SELECT
        pr.licence_number,
        pr.pos_sku,
        pr.product_name,
        pr.brand_name,
        pr.regular_price_cad,
        pr.sale_price_cad,
        pr.in_stock,
        pr.scraped_at,
        pr.scraped_at::date AS price_date
    FROM raw.product_pricing pr
    JOIN raw.agco_stores s ON s.licence_number = pr.licence_number
    WHERE s.within_35km = true
      AND s.is_active = true
      AND pr.scraped_at >= NOW() - INTERVAL '90 days'
),
current_price AS (
    SELECT DISTINCT ON (licence_number, COALESCE(pos_sku, product_name))
        licence_number,
        pos_sku,
        product_name,
        brand_name,
        regular_price_cad,
        sale_price_cad,
        scraped_at
    FROM pricing_90d
    ORDER BY licence_number, COALESCE(pos_sku, product_name), scraped_at DESC
)
SELECT
    p.licence_number,
    s.store_name,
    p.pos_sku,
    p.product_name,
    p.brand_name,
    c.regular_price_cad AS current_regular_price_cad,
    c.sale_price_cad AS current_sale_price_cad,
    COUNT(DISTINCT p.regular_price_cad) FILTER (
        WHERE p.scraped_at >= NOW() - INTERVAL '30 days'
    ) AS price_changes_last_30d,
    COUNT(DISTINCT p.regular_price_cad) AS price_changes_last_90d,
    MIN(COALESCE(p.sale_price_cad, p.regular_price_cad)) AS min_effective_price_90d,
    MAX(COALESCE(p.sale_price_cad, p.regular_price_cad)) AS max_effective_price_90d,
    MAX(p.scraped_at::date) AS last_observed_date,
    CASE
        WHEN COUNT(DISTINCT p.regular_price_cad) FILTER (
            WHERE p.scraped_at >= NOW() - INTERVAL '30 days'
        ) <= 1 THEN 'stable'
        WHEN COUNT(DISTINCT p.regular_price_cad) FILTER (
            WHERE p.scraped_at >= NOW() - INTERVAL '30 days'
        ) <= 3 THEN 'moderate'
        ELSE 'volatile'
    END AS volatility_label
FROM pricing_90d p
JOIN raw.agco_stores s ON s.licence_number = p.licence_number
LEFT JOIN current_price c
    ON c.licence_number = p.licence_number
   AND COALESCE(c.pos_sku, c.product_name) = COALESCE(p.pos_sku, p.product_name)
GROUP BY
    p.licence_number,
    s.store_name,
    p.pos_sku,
    p.product_name,
    p.brand_name,
    c.regular_price_cad,
    c.sale_price_cad;

CREATE OR REPLACE VIEW marts.new_arrivals AS
SELECT
    o.ocs_sku,
    o.product_name,
    o.brand_name,
    LOWER(COALESCE(NULLIF(TRIM(o.category_raw), ''), 'other')) AS category,
    o.ocs_price_cad,
    o.first_seen_at,
    o.last_seen_at,
    (CURRENT_DATE - o.first_seen_at) AS days_since_first_seen,
    COUNT(DISTINCT p.licence_number) FILTER (WHERE p.is_active) AS local_store_count,
    ARRAY_REMOVE(ARRAY_AGG(DISTINCT s.store_name), NULL) AS available_at_stores,
    CASE
        WHEN COUNT(DISTINCT p.licence_number) FILTER (WHERE p.is_active) = 0 THEN true
        ELSE false
    END AS opportunity_flag
FROM raw.ocs_catalog o
LEFT JOIN raw.store_products p ON p.ocs_sku = o.ocs_sku
LEFT JOIN raw.agco_stores s
    ON s.licence_number = p.licence_number
   AND s.within_35km = true
   AND s.is_active = true
WHERE o.first_seen_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
    o.ocs_sku,
    o.product_name,
    o.brand_name,
    o.category_raw,
    o.ocs_price_cad,
    o.first_seen_at,
    o.last_seen_at;
