# Data Dictionary

> **Document:** docs/data-dictionary.md
> **Project:** Vascora — MontKailash Cannabis Market Intelligence
> **Last Updated:** March 2026
> **Database:** PostgreSQL 16 + TimescaleDB
> **Schemas:** `raw` (ingestion landing) · `staging` (dbt cleaned) · `marts` (analytics-ready)

---

## Table of Contents

1. [Schema Overview](#1-schema-overview)
2. [Raw Schema — Ingestion Tables](#2-raw-schema--ingestion-tables)
   - [raw.agco_stores](#rawagco_stores)
   - [raw.google_enrichments](#rawgoogle_enrichments)
   - [raw.store_products](#rawstore_products)
   - [raw.product_pricing](#rawproduct_pricing)
   - [raw.ocs_catalog](#rawocs_catalog)
   - [raw.hibuddy_listings](#rawhibuddy_listings)
   - [raw.reddit_posts](#rawreddit_posts)
3. [Staging Schema — dbt Cleaned](#3-staging-schema--dbt-cleaned)
   - [staging.stg_stores](#stagingstg_stores)
   - [staging.stg_products](#stagingstg_products)
   - [staging.stg_pricing](#stagingstg_pricing)
   - [staging.stg_ocs_catalog](#stagingstg_ocs_catalog)
   - [staging.stg_reddit](#stagingstg_reddit)
4. [Marts Schema — Analytics Ready](#4-marts-schema--analytics-ready)
   - [marts.mart_store_coverage](#martsmart_store_coverage)
   - [marts.mart_product_matrix](#martsmart_product_matrix)
   - [marts.mart_price_volatility](#martsmart_price_volatility)
   - [marts.mart_new_arrivals](#martsmart_new_arrivals)
   - [marts.mart_sentiment_gap](#martsmart_sentiment_gap)
5. [Enumerated Value Definitions](#5-enumerated-value-definitions)
6. [Indexing Strategy](#6-indexing-strategy)

---

## 1. Schema Overview

```
raw.*          → Direct output of scrapers. No transformation. Append-with-upsert.
staging.*      → dbt staging models. Cleaned, typed, deduplicated. 1:1 with raw tables.
intermediate.* → dbt intermediate models. Cross-source joins. Not exposed to dashboard.
marts.*        → dbt mart models. Business-logic aggregations. Read by Streamlit.
```

---

## 2. Raw Schema — Ingestion Tables

### raw.agco_stores

Stores every active cannabis retail licence from the AGCO registry that falls within or near Ontario's Burlington area. Updated daily via `dag_store_discovery`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `SERIAL` | NOT NULL | Internal surrogate key |
| `licence_number` | `VARCHAR(50)` | NOT NULL | AGCO licence number — unique identifier from regulator |
| `store_name` | `VARCHAR(255)` | NOT NULL | Operating/trading name of the store |
| `licence_holder_name` | `VARCHAR(255)` | NULL | Legal entity name on the licence (corp or individual) |
| `street_address` | `VARCHAR(500)` | NOT NULL | Full civic street address |
| `city` | `VARCHAR(100)` | NOT NULL | Municipality |
| `province` | `VARCHAR(50)` | NOT NULL | Always `ON` for this pipeline |
| `postal_code` | `VARCHAR(10)` | NULL | Canadian postal code |
| `licence_status` | `VARCHAR(50)` | NOT NULL | `Active` / `Suspended` / `Revoked` |
| `licence_issue_date` | `DATE` | NULL | Date licence was first issued |
| `latitude` | `NUMERIC(10,7)` | NULL | Geocoded latitude (populated post-Nominatim run) |
| `longitude` | `NUMERIC(10,7)` | NULL | Geocoded longitude |
| `distance_km` | `NUMERIC(8,3)` | NULL | Haversine distance from Burlington centroid (43.3255, -79.7990) |
| `within_35km` | `BOOLEAN` | NULL | True if distance_km ≤ 35 |
| `google_place_id` | `VARCHAR(255)` | NULL | Google Places place_id (populated post-enrichment) |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL | UTC timestamp when this record was written |
| `source_file` | `VARCHAR(255)` | NULL | Source filename or URL if downloaded from AGCO |

**Primary key:** `licence_number`
**Upsert key:** `licence_number` — on conflict, update all fields except `id` and `licence_issue_date`

---

### raw.google_enrichments

Stores the enrichment data from Google Places API for each AGCO-identified store.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `SERIAL` | NOT NULL | Internal surrogate key |
| `licence_number` | `VARCHAR(50)` | NOT NULL | FK to `raw.agco_stores.licence_number` |
| `google_place_id` | `VARCHAR(255)` | NOT NULL | Google's canonical place identifier |
| `phone_number` | `VARCHAR(50)` | NULL | Formatted local phone number |
| `website_url` | `TEXT` | NULL | Store website URL |
| `google_maps_url` | `TEXT` | NULL | Google Maps permalink |
| `google_rating` | `NUMERIC(3,1)` | NULL | Rating out of 5.0 |
| `review_count` | `INTEGER` | NULL | Total number of Google reviews |
| `hours_of_operation` | `JSONB` | NULL | `{"Monday": "9am-9pm", "Tuesday": "9am-9pm", ...}` |
| `is_permanently_closed` | `BOOLEAN` | NOT NULL DEFAULT false | Google-reported closure flag |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL | UTC timestamp |

**Primary key:** `id`
**Upsert key:** `licence_number`

**JSONB hours example:**
```json
{
  "Monday": "10:00 AM – 9:00 PM",
  "Tuesday": "10:00 AM – 9:00 PM",
  "Wednesday": "10:00 AM – 9:00 PM",
  "Thursday": "10:00 AM – 9:00 PM",
  "Friday": "10:00 AM – 10:00 PM",
  "Saturday": "10:00 AM – 10:00 PM",
  "Sunday": "11:00 AM – 7:00 PM"
}
```

---

### raw.store_products

The raw product catalog scraped from each store's live menu. Updated daily.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `BIGSERIAL` | NOT NULL | Internal surrogate key |
| `licence_number` | `VARCHAR(50)` | NOT NULL | FK to `raw.agco_stores.licence_number` |
| `store_name` | `VARCHAR(255)` | NOT NULL | Denormalised for readability |
| `pos_platform` | `VARCHAR(50)` | NULL | `dutchie` / `jane` / `cova` / `other` |
| `pos_sku` | `VARCHAR(255)` | NULL | POS-platform internal product ID |
| `product_name` | `VARCHAR(500)` | NOT NULL | Name as listed on menu |
| `brand_name` | `VARCHAR(255)` | NULL | |
| `category_raw` | `VARCHAR(100)` | NULL | Category string as-scraped (before normalisation) |
| `thc_pct_min` | `NUMERIC(5,2)` | NULL | THC % lower bound |
| `thc_pct_max` | `NUMERIC(5,2)` | NULL | THC % upper bound (same as min if single value) |
| `cbd_pct_min` | `NUMERIC(5,2)` | NULL | CBD % lower bound |
| `cbd_pct_max` | `NUMERIC(5,2)` | NULL | CBD % upper bound |
| `weight_grams` | `NUMERIC(8,3)` | NULL | Weight in grams (null for non-weighted items like edibles) |
| `unit_count` | `INTEGER` | NULL | Pack count (e.g., 10 for pre-roll 10-pack) |
| `ocs_sku` | `VARCHAR(100)` | NULL | Matched OCS SKU (populated by `int_product_ocs_match`) |
| `in_stock` | `BOOLEAN` | NOT NULL DEFAULT true | Whether product is currently in stock |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL | UTC timestamp |
| `is_active` | `BOOLEAN` | NOT NULL DEFAULT true | Set to false when product no longer appears on menu |

**Primary key:** `id`
**Upsert key:** `(licence_number, pos_sku)` where pos_sku is not null; else `(licence_number, product_name, brand_name)`

---

### raw.product_pricing

**TimescaleDB hypertable.** Append-only time-series of daily price snapshots per product per store. Never updated — only appended. This enables complete price history queries.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `BIGSERIAL` | NOT NULL | Internal surrogate key |
| `store_product_id` | `BIGINT` | NOT NULL | FK to `raw.store_products.id` |
| `licence_number` | `VARCHAR(50)` | NOT NULL | Denormalised FK |
| `pos_sku` | `VARCHAR(255)` | NULL | Denormalised for query convenience |
| `product_name` | `VARCHAR(500)` | NOT NULL | Denormalised |
| `brand_name` | `VARCHAR(255)` | NULL | Denormalised |
| `regular_price_cad` | `NUMERIC(8,2)` | NOT NULL | Regular (non-promotional) price in CAD |
| `sale_price_cad` | `NUMERIC(8,2)` | NULL | Active promotional price. NULL if no promotion |
| `effective_price_cad` | `NUMERIC(8,2)` | NOT NULL | `COALESCE(sale_price_cad, regular_price_cad)` — actual purchase price |
| `promo_label` | `VARCHAR(255)` | NULL | Promotion name (e.g., "Flash Friday 20% off") |
| `promo_start_date` | `DATE` | NULL | Start date of promotion if visible on menu |
| `promo_end_date` | `DATE` | NULL | End date of promotion if visible on menu |
| `in_stock` | `BOOLEAN` | NOT NULL | Stock status at time of scrape |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL | UTC timestamp — **TimescaleDB partition key** |

**TimescaleDB configuration:**
```sql
SELECT create_hypertable('raw.product_pricing', 'scraped_at', chunk_time_interval => INTERVAL '1 month');
```

**Retention policy (POC):** Keep all data (no retention policy). In production, consider 12-month rolling window.

---

### raw.ocs_catalog

The Ontario Cannabis Store full product catalog, scraped daily.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `SERIAL` | NOT NULL | Internal surrogate key |
| `ocs_sku` | `VARCHAR(100)` | NOT NULL | OCS unique product identifier |
| `product_name` | `VARCHAR(500)` | NOT NULL | |
| `brand_name` | `VARCHAR(255)` | NULL | |
| `category_raw` | `VARCHAR(100)` | NULL | OCS-assigned category |
| `thc_pct_min` | `NUMERIC(5,2)` | NULL | |
| `thc_pct_max` | `NUMERIC(5,2)` | NULL | |
| `cbd_pct_min` | `NUMERIC(5,2)` | NULL | |
| `cbd_pct_max` | `NUMERIC(5,2)` | NULL | |
| `weight_grams` | `NUMERIC(8,3)` | NULL | |
| `ocs_price_cad` | `NUMERIC(8,2)` | NULL | OCS listed price (MSRP reference) |
| `is_new_arrival` | `BOOLEAN` | NOT NULL DEFAULT false | True if OCS "New" badge detected |
| `first_seen_at` | `DATE` | NOT NULL | Date first scraped from OCS |
| `last_seen_at` | `DATE` | NOT NULL | Date of most recent scrape (updated daily) |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL | UTC timestamp |

**Primary key:** `ocs_sku`
**Upsert key:** `ocs_sku` — on conflict update `last_seen_at`, `ocs_price_cad`, `is_new_arrival`

---

### raw.hibuddy_listings

Price listings from HiBuddy.ca, used as secondary validation.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `BIGSERIAL` | NOT NULL | Internal surrogate key |
| `hibuddy_store_id` | `VARCHAR(100)` | NULL | HiBuddy internal store identifier |
| `licence_number` | `VARCHAR(50)` | NULL | Matched AGCO licence number (NULL if unmatched) |
| `store_name_raw` | `VARCHAR(255)` | NOT NULL | Store name as listed on HiBuddy |
| `product_name` | `VARCHAR(500)` | NOT NULL | |
| `brand_name` | `VARCHAR(255)` | NULL | |
| `hibuddy_price_cad` | `NUMERIC(8,2)` | NULL | Price listed on HiBuddy |
| `hibuddy_updated_at` | `TIMESTAMPTZ` | NULL | When HiBuddy last updated this listing |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL | Our scrape timestamp |

---

### raw.reddit_posts

Public Reddit posts and comments collected by PRAW, with pre-computed VADER sentiment scores.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `SERIAL` | NOT NULL | Internal surrogate key |
| `reddit_id` | `VARCHAR(20)` | NOT NULL | Reddit's unique post ID (`t3_xxxx`) |
| `subreddit` | `VARCHAR(100)` | NOT NULL | Subreddit name without r/ prefix |
| `search_keyword` | `VARCHAR(255)` | NOT NULL | Keyword query that returned this post |
| `post_title` | `TEXT` | NOT NULL | |
| `post_body` | `TEXT` | NULL | Self-text of the post |
| `post_score` | `INTEGER` | NULL | Net upvotes (engagement signal) |
| `comment_count` | `INTEGER` | NULL | |
| `top_comments_text` | `TEXT` | NULL | Concatenated text of top 5 comments |
| `full_text` | `TEXT` | NOT NULL | Concatenation of title + body + top comments (used for VADER) |
| `vader_compound` | `NUMERIC(5,4)` | NULL | VADER compound score (−1.0 to +1.0) |
| `sentiment_label` | `VARCHAR(10)` | NULL | `positive` (≥0.05) / `neutral` / `negative` (≤−0.05) |
| `posted_at` | `TIMESTAMPTZ` | NOT NULL | UTC timestamp of original Reddit post |
| `scraped_at` | `TIMESTAMPTZ` | NOT NULL | Our collection timestamp |

**Primary key:** `reddit_id`
**Upsert key:** `reddit_id` — on conflict update `post_score`, `comment_count`, `scraped_at`

---

## 3. Staging Schema — dbt Cleaned

Staging models cast types, rename columns to snake_case conventions, handle nulls, and deduplicate. They do **not** join across tables.

### staging.stg_stores

Unified, cleaned store record joining AGCO data with Google enrichment.

| Column | Type | Description |
|---|---|---|
| `store_id` | `VARCHAR(50)` | = `raw.agco_stores.licence_number` |
| `store_name` | `VARCHAR(255)` | Trimmed and title-cased |
| `licence_number` | `VARCHAR(50)` | AGCO licence number |
| `licence_holder_name` | `VARCHAR(255)` | Legal entity name |
| `street_address` | `VARCHAR(500)` | |
| `city` | `VARCHAR(100)` | |
| `postal_code` | `VARCHAR(10)` | |
| `phone_number` | `VARCHAR(50)` | From Google enrichment |
| `website_url` | `TEXT` | From Google enrichment |
| `hours_of_operation` | `JSONB` | From Google enrichment |
| `google_rating` | `NUMERIC(3,1)` | |
| `google_review_count` | `INTEGER` | |
| `latitude` | `NUMERIC(10,7)` | |
| `longitude` | `NUMERIC(10,7)` | |
| `distance_km` | `NUMERIC(8,3)` | |
| `pos_platform` | `VARCHAR(50)` | Most recently detected POS platform |
| `is_active` | `BOOLEAN` | True if AGCO status = Active and not Google-closed |
| `last_scraped_at` | `TIMESTAMPTZ` | |

---

### staging.stg_products

Cleaned and normalised product records.

| Column | Type | Description |
|---|---|---|
| `product_id` | `BIGINT` | = `raw.store_products.id` |
| `store_id` | `VARCHAR(50)` | FK to `stg_stores.store_id` |
| `pos_sku` | `VARCHAR(255)` | |
| `ocs_sku` | `VARCHAR(100)` | Matched OCS SKU (may be null) |
| `product_name` | `VARCHAR(500)` | Trimmed |
| `brand_name` | `VARCHAR(255)` | Trimmed, title-cased |
| `category` | `VARCHAR(50)` | Normalised category — see [Enumerated Values](#5-enumerated-value-definitions) |
| `thc_pct_midpoint` | `NUMERIC(5,2)` | Average of min/max for sorting |
| `cbd_pct_midpoint` | `NUMERIC(5,2)` | |
| `weight_grams` | `NUMERIC(8,3)` | |
| `in_stock` | `BOOLEAN` | |
| `is_active` | `BOOLEAN` | |
| `first_seen_at` | `TIMESTAMPTZ` | Earliest `scraped_at` for this product |
| `last_seen_at` | `TIMESTAMPTZ` | Most recent `scraped_at` |

---

### staging.stg_pricing

Deduplicated daily pricing snapshots. Where multiple scrapes happened within the same day, keeps the most recent.

| Column | Type | Description |
|---|---|---|
| `pricing_id` | `BIGINT` | = `raw.product_pricing.id` |
| `product_id` | `BIGINT` | FK to `stg_products.product_id` |
| `store_id` | `VARCHAR(50)` | |
| `regular_price_cad` | `NUMERIC(8,2)` | |
| `sale_price_cad` | `NUMERIC(8,2)` | NULL if no promotion |
| `effective_price_cad` | `NUMERIC(8,2)` | Actual buy price |
| `is_on_sale` | `BOOLEAN` | True if `sale_price_cad` is not null |
| `promo_label` | `VARCHAR(255)` | |
| `promo_start_date` | `DATE` | |
| `promo_end_date` | `DATE` | |
| `price_date` | `DATE` | Date portion of `scraped_at` |
| `scraped_at` | `TIMESTAMPTZ` | |

---

### staging.stg_ocs_catalog

| Column | Type | Description |
|---|---|---|
| `ocs_sku` | `VARCHAR(100)` | |
| `product_name` | `VARCHAR(500)` | |
| `brand_name` | `VARCHAR(255)` | |
| `category` | `VARCHAR(50)` | Normalised |
| `thc_pct_midpoint` | `NUMERIC(5,2)` | |
| `cbd_pct_midpoint` | `NUMERIC(5,2)` | |
| `weight_grams` | `NUMERIC(8,3)` | |
| `ocs_price_cad` | `NUMERIC(8,2)` | |
| `days_since_first_seen` | `INTEGER` | `CURRENT_DATE - first_seen_at` |
| `is_new_arrival` | `BOOLEAN` | True if `days_since_first_seen` ≤ 30 |

---

### staging.stg_reddit

| Column | Type | Description |
|---|---|---|
| `reddit_id` | `VARCHAR(20)` | |
| `subreddit` | `VARCHAR(100)` | |
| `search_keyword` | `VARCHAR(255)` | |
| `post_title` | `TEXT` | |
| `vader_compound` | `NUMERIC(5,4)` | |
| `sentiment_label` | `VARCHAR(10)` | |
| `post_score` | `INTEGER` | |
| `posted_at` | `TIMESTAMPTZ` | |
| `brand_keyword` | `VARCHAR(255)` | Extracted brand name from `search_keyword` |
| `product_keyword` | `VARCHAR(255)` | Extracted product name from `search_keyword` |

---

## 4. Marts Schema — Analytics Ready

### marts.mart_store_coverage

One row per active store within 35 km. Used by the Store Coverage Map page.

| Column | Type | Description |
|---|---|---|
| `store_id` | `VARCHAR(50)` | |
| `store_name` | `VARCHAR(255)` | |
| `licence_number` | `VARCHAR(50)` | |
| `licence_holder_name` | `VARCHAR(255)` | |
| `full_address` | `TEXT` | Concatenated address for display |
| `city` | `VARCHAR(100)` | |
| `phone_number` | `VARCHAR(50)` | |
| `website_url` | `TEXT` | |
| `hours_of_operation` | `JSONB` | |
| `google_rating` | `NUMERIC(3,1)` | |
| `latitude` | `NUMERIC(10,7)` | |
| `longitude` | `NUMERIC(10,7)` | |
| `distance_km` | `NUMERIC(8,3)` | |
| `pos_platform` | `VARCHAR(50)` | |
| `product_count` | `INTEGER` | Total active products currently on menu |
| `last_scraped_at` | `TIMESTAMPTZ` | |

---

### marts.mart_product_matrix

One row per unique product × store combination. Used by the Product Matrix heatmap.

| Column | Type | Description |
|---|---|---|
| `product_key` | `TEXT` | Normalised `brand_name + product_name` (join key) |
| `brand_name` | `VARCHAR(255)` | |
| `product_name` | `VARCHAR(500)` | |
| `category` | `VARCHAR(50)` | |
| `store_count` | `INTEGER` | Number of stores carrying this product |
| `ubiquity_score` | `NUMERIC(5,2)` | `store_count / total_active_stores * 100` (% of market coverage) |
| `store_ids` | `TEXT[]` | Array of store_ids carrying this product |
| `avg_regular_price_cad` | `NUMERIC(8,2)` | Average regular price across all carrying stores |
| `min_regular_price_cad` | `NUMERIC(8,2)` | Lowest price in market |
| `max_regular_price_cad` | `NUMERIC(8,2)` | Highest price in market |
| `price_spread_cad` | `NUMERIC(8,2)` | `max - min` |
| `on_ocs` | `BOOLEAN` | Whether this product has a matched OCS SKU |
| `ocs_price_cad` | `NUMERIC(8,2)` | OCS reference price (null if no OCS match) |

---

### marts.mart_price_volatility

One row per product per store with rolling price change statistics. Used by Price Intelligence page.

| Column | Type | Description |
|---|---|---|
| `product_id` | `BIGINT` | |
| `store_id` | `VARCHAR(50)` | |
| `product_name` | `VARCHAR(500)` | |
| `brand_name` | `VARCHAR(255)` | |
| `category` | `VARCHAR(50)` | |
| `store_name` | `VARCHAR(255)` | |
| `current_regular_price_cad` | `NUMERIC(8,2)` | Most recent regular price |
| `current_sale_price_cad` | `NUMERIC(8,2)` | Most recent sale price (null if none) |
| `is_currently_on_sale` | `BOOLEAN` | |
| `price_changes_last_30d` | `INTEGER` | Count of distinct regular price values in last 30 days |
| `price_changes_last_90d` | `INTEGER` | |
| `volatility_label` | `VARCHAR(20)` | `stable` (0–1 change) / `moderate` (2–3) / `volatile` (4+) |
| `min_price_last_90d` | `NUMERIC(8,2)` | Lowest effective price seen in 90 days |
| `max_price_last_90d` | `NUMERIC(8,2)` | |
| `days_on_sale_last_30d` | `INTEGER` | Number of days in last 30 where sale_price was not null |
| `last_price_change_date` | `DATE` | |

---

### marts.mart_new_arrivals

OCS products first listed in the last 30 days, with their local Burlington-area availability.

| Column | Type | Description |
|---|---|---|
| `ocs_sku` | `VARCHAR(100)` | |
| `product_name` | `VARCHAR(500)` | |
| `brand_name` | `VARCHAR(255)` | |
| `category` | `VARCHAR(50)` | |
| `thc_pct_midpoint` | `NUMERIC(5,2)` | |
| `ocs_price_cad` | `NUMERIC(8,2)` | |
| `days_since_ocs_listing` | `INTEGER` | |
| `local_store_count` | `INTEGER` | Number of Burlington-area stores already carrying this product |
| `is_available_locally` | `BOOLEAN` | True if `local_store_count` > 0 |
| `available_at_stores` | `TEXT[]` | Store names carrying this product locally |
| `opportunity_flag` | `BOOLEAN` | True if `local_store_count` = 0 (MontKailash stocking opportunity) |

---

### marts.mart_sentiment_gap

One row per brand/product keyword, combining Reddit sentiment with local store availability. Used by Sentiment & Gaps page.

| Column | Type | Description |
|---|---|---|
| `keyword` | `VARCHAR(255)` | Brand or product keyword |
| `keyword_type` | `VARCHAR(20)` | `brand` or `product` |
| `total_posts` | `INTEGER` | Total Reddit posts mentioning this keyword |
| `avg_sentiment_score` | `NUMERIC(5,4)` | Average VADER compound score across all posts |
| `sentiment_label` | `VARCHAR(10)` | Dominant sentiment label |
| `positive_post_count` | `INTEGER` | |
| `negative_post_count` | `INTEGER` | |
| `total_reddit_score` | `INTEGER` | Sum of post scores (upvotes) — reach signal |
| `local_store_count` | `INTEGER` | Number of Burlington-area stores carrying related product |
| `opportunity_score` | `NUMERIC(5,2)` | `avg_sentiment_score * (1 / (local_store_count + 1))` — higher = better opportunity |
| `is_gap_opportunity` | `BOOLEAN` | True if `avg_sentiment_score` ≥ 0.2 AND `local_store_count` ≤ 2 |

---

## 5. Enumerated Value Definitions

### Product Category (normalised)

| Normalised Value | Maps From (raw variations) |
|---|---|
| `flower` | "Dried Flower", "Cannabis", "Bud", "Indica", "Sativa", "Hybrid" |
| `pre_roll` | "Pre-Roll", "Pre-Rolls", "Joint", "Joints" |
| `vape` | "Vape", "Vape Cartridge", "Pen", "510 Thread" |
| `edible` | "Edible", "Edibles", "Gummy", "Gummies", "Chocolate", "Beverage" |
| `concentrate` | "Concentrate", "Extract", "Shatter", "Wax", "Hash", "Rosin", "Resin" |
| `tincture` | "Tincture", "Oil", "Drops" |
| `topical` | "Topical", "Cream", "Lotion", "Patch" |
| `capsule` | "Capsule", "Softgel" |
| `seed` | "Seed", "Seeds" |
| `other` | Anything not matched above |

### Sentiment Label

| Value | VADER Compound Range |
|---|---|
| `positive` | ≥ 0.05 |
| `neutral` | > −0.05 and < 0.05 |
| `negative` | ≤ −0.05 |

### Volatility Label

| Value | Price Change Count (30 days) |
|---|---|
| `stable` | 0–1 distinct regular price values |
| `moderate` | 2–3 distinct regular price values |
| `volatile` | 4 or more distinct regular price values |

---

## 6. Indexing Strategy

```sql
-- Store lookup
CREATE INDEX idx_agco_stores_licence ON raw.agco_stores (licence_number);
CREATE INDEX idx_agco_stores_distance ON raw.agco_stores (distance_km) WHERE within_35km = true;

-- Product lookup
CREATE INDEX idx_store_products_licence ON raw.store_products (licence_number);
CREATE INDEX idx_store_products_sku ON raw.store_products (pos_sku) WHERE pos_sku IS NOT NULL;
CREATE INDEX idx_store_products_brand ON raw.store_products (brand_name);

-- Pricing time-series (TimescaleDB manages chunk indexes automatically)
CREATE INDEX idx_product_pricing_product ON raw.product_pricing (store_product_id, scraped_at DESC);

-- Reddit keyword search
CREATE INDEX idx_reddit_keyword ON raw.reddit_posts (search_keyword);
CREATE INDEX idx_reddit_sentiment ON raw.reddit_posts (sentiment_label, vader_compound);

-- OCS new arrivals
CREATE INDEX idx_ocs_first_seen ON raw.ocs_catalog (first_seen_at DESC);
CREATE INDEX idx_ocs_sku ON raw.ocs_catalog (ocs_sku);
```
