# Analytics Specification

> Document: docs/analytics-spec.md
> Project: Vascora
> Last Updated: March 2026

---

## 1. Purpose

Define the currently implemented analytics outputs built from ingested store, product, pricing, and OCS data.

---

## 2. Implemented Outputs

### 2.1 Store Coverage

Source:

- marts.store_coverage

Questions answered:

- Which stores are within Burlington radius?
- What is each store's operational footprint?
- How many active products does each store carry?

Key fields:

- store name
- address and city
- distance_km
- within_35km
- active_product_count

API:

- GET /analytics/store-coverage
- CSV: GET /analytics/export/store-coverage

### 2.2 Product Matrix

Source:

- marts.product_matrix

Questions answered:

- Which products are most commonly carried across stores?
- What products have high coverage versus niche presence?

Key fields:

- brand_name
- product_name
- category
- store_count
- ubiquity_score

API:

- GET /analytics/product-matrix
- CSV: GET /analytics/export/product-matrix

### 2.3 Price Volatility

Source:

- marts.price_volatility

Questions answered:

- Which products experience frequent price changes?
- Which products appear stable versus volatile?

Key fields:

- current_regular_price_cad
- current_sale_price_cad
- price_changes_last_30d
- price_changes_last_90d
- min and max effective price
- volatility_label

API:

- GET /analytics/price-volatility
- CSV: GET /analytics/export/price-volatility

### 2.4 New Arrivals

Source:

- marts.new_arrivals

Questions answered:

- Which OCS products are newly listed?
- Which new products are not yet available locally?

Key fields:

- ocs_sku
- product_name
- category
- days_since_first_seen
- local_store_count
- opportunity_flag

API:

- GET /analytics/new-arrivals
- CSV: GET /analytics/export/new-arrivals

---

## 3. Refresh Strategy

Analytics views are rebuilt using:

- python -m app.pipelines.refresh_marts
- or POST /analytics/refresh with X-Api-Token

Recommended sequence:

1. ingest raw tables
2. refresh marts
3. query or export outputs

---

## 4. Output Limits

Default API limits are conservative for interactive use.

- Query endpoints accept limit up to 2000
- Export endpoints accept limit up to 50000

---

## 5. Future Additions (Optional)

Sentiment analytics can be added later by introducing:

- sentiment marts view or views derived from raw.reddit_posts
- endpoint such as GET /analytics/sentiment-gap
- export path GET /analytics/export/sentiment-gap

This extension does not require changing existing endpoints.
