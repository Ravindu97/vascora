# Data Dictionary

> Document: docs/data-dictionary.md
> Project: Vascora
> Last Updated: March 2026

---

## 1. Schemas

- raw: ingestion landing tables
- marts: analytics views derived from raw

---

## 2. Raw Tables

### 2.1 raw.agco_stores

| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | Internal surrogate key |
| licence_number | VARCHAR(50) UNIQUE | Store licence identifier |
| store_name | VARCHAR(255) | Store name |
| licence_holder_name | VARCHAR(255) | Licence holder |
| street_address | VARCHAR(500) | Address |
| city | VARCHAR(100) | City |
| province | VARCHAR(50) | Province |
| postal_code | VARCHAR(10) | Postal code |
| phone_number | VARCHAR(50) | Phone |
| website_url | TEXT | Website |
| latitude | NUMERIC(10,7) | Latitude |
| longitude | NUMERIC(10,7) | Longitude |
| distance_km | NUMERIC(8,3) | Distance from Burlington center |
| within_35km | BOOLEAN | Radius inclusion flag |
| hours_of_operation | JSONB | Optional hours map |
| is_active | BOOLEAN | Active status |
| scraped_at | TIMESTAMPTZ | Ingestion timestamp |

### 2.2 raw.store_products

| Column | Type | Description |
|---|---|---|
| id | BIGSERIAL PK | Internal key |
| licence_number | VARCHAR(50) | Store linkage |
| pos_platform | VARCHAR(50) | POS platform label |
| pos_sku | VARCHAR(255) | SKU/ID |
| product_name | VARCHAR(500) | Product name |
| brand_name | VARCHAR(255) | Brand |
| category_raw | VARCHAR(100) | Category as source provides |
| thc_pct_min | NUMERIC(5,2) | THC min |
| thc_pct_max | NUMERIC(5,2) | THC max |
| cbd_pct_min | NUMERIC(5,2) | CBD min |
| cbd_pct_max | NUMERIC(5,2) | CBD max |
| weight_grams | NUMERIC(8,3) | Weight |
| unit_count | INTEGER | Unit count |
| ocs_sku | VARCHAR(100) | Matched OCS SKU if available |
| in_stock | BOOLEAN | Stock status |
| is_active | BOOLEAN | Active listing status |
| scraped_at | TIMESTAMPTZ | Ingestion timestamp |

Unique constraint:

- (licence_number, pos_sku, product_name)

### 2.3 raw.product_pricing

| Column | Type | Description |
|---|---|---|
| id | BIGSERIAL PK | Internal key |
| licence_number | VARCHAR(50) | Store linkage |
| pos_sku | VARCHAR(255) | SKU/ID |
| product_name | VARCHAR(500) | Product name |
| brand_name | VARCHAR(255) | Brand |
| regular_price_cad | NUMERIC(8,2) | Regular price |
| sale_price_cad | NUMERIC(8,2) | Sale price |
| promo_label | VARCHAR(255) | Promotion label |
| promo_start_date | DATE | Promo start |
| promo_end_date | DATE | Promo end |
| in_stock | BOOLEAN | Stock status |
| scraped_at | TIMESTAMPTZ | Snapshot timestamp |

### 2.4 raw.ocs_catalog

| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | Internal key |
| ocs_sku | VARCHAR(100) UNIQUE | OCS SKU |
| product_name | VARCHAR(500) | Product name |
| brand_name | VARCHAR(255) | Brand |
| category_raw | VARCHAR(100) | Category |
| thc_pct_min | NUMERIC(5,2) | THC min |
| thc_pct_max | NUMERIC(5,2) | THC max |
| cbd_pct_min | NUMERIC(5,2) | CBD min |
| cbd_pct_max | NUMERIC(5,2) | CBD max |
| weight_grams | NUMERIC(8,3) | Weight |
| ocs_price_cad | NUMERIC(8,2) | OCS listed price |
| first_seen_at | DATE | First seen date |
| last_seen_at | DATE | Last seen date |
| scraped_at | TIMESTAMPTZ | Ingestion timestamp |

### 2.5 raw.reddit_posts (optional future source)

| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | Internal key |
| reddit_id | VARCHAR(20) UNIQUE | Reddit post ID |
| subreddit | VARCHAR(100) | Subreddit |
| search_keyword | VARCHAR(255) | Query keyword |
| post_title | TEXT | Title |
| post_body | TEXT | Body |
| post_score | INTEGER | Score |
| comment_count | INTEGER | Comment count |
| top_comments_text | TEXT | Top comments blob |
| full_text | TEXT | Combined text |
| vader_compound | NUMERIC(5,4) | Sentiment score |
| sentiment_label | VARCHAR(10) | Label |
| posted_at | TIMESTAMPTZ | Post timestamp |
| scraped_at | TIMESTAMPTZ | Ingest timestamp |

---

## 3. Marts Views

### 3.1 marts.store_coverage

Store-level operational and inventory coverage view.

Selected fields include:

- store identity and location columns
- distance and radius flags
- active product count per store

### 3.2 marts.product_matrix

Cross-store product coverage and ubiquity view.

Selected fields include:

- brand_name, product_name, category
- store_count
- ubiquity_score
- in_stock_records

### 3.3 marts.price_volatility

Price variation view over recent windows.

Selected fields include:

- current regular and sale price
- price_changes_last_30d
- price_changes_last_90d
- min and max effective price
- volatility_label

### 3.4 marts.new_arrivals

Recent OCS arrivals with local market availability.

Selected fields include:

- product and category
- days_since_first_seen
- local_store_count
- available store names array
- opportunity_flag

---

## 4. Key Derived Logic

- Radius filtering uses within_35km from store ingestion logic.
- Ubiquity score is computed against active local store denominator.
- Volatility labels use distinct regular price counts in 30-day window.
- New-arrival opportunities are products with no local carrying stores.
