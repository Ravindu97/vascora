# System Architecture

> **Document:** docs/architecture.md
> **Project:** Vascora — MontKailash Cannabis Market Intelligence
> **Last Updated:** March 2026

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Layer-by-Layer Breakdown](#2-layer-by-layer-breakdown)
3. [Module Descriptions](#3-module-descriptions)
4. [Data Flow Diagram](#4-data-flow-diagram)
5. [Airflow DAG Schedule](#5-airflow-dag-schedule)
6. [Database Design Principles](#6-database-design-principles)
7. [dbt Transformation Models](#7-dbt-transformation-models)
8. [Dashboard Architecture](#8-dashboard-architecture)
9. [Infrastructure & Deployment](#9-infrastructure--deployment)
10. [Folder Structure](#10-folder-structure)

---

## 1. Architecture Overview

Vascora is structured as a classic **ELT (Extract → Load → Transform)** pipeline:

```
EXTRACT        →       LOAD          →      TRANSFORM        →     SERVE
External APIs        PostgreSQL 16          dbt-core              Streamlit
& Web Scrapers       (raw schema)       (staging → marts)        Dashboard
```

Each layer is independently deployable and testable. The pipeline is orchestrated by **Apache Airflow** running as a set of scheduled DAGs (Directed Acyclic Graphs).

---

## 2. Layer-by-Layer Breakdown

### Layer 1 — Extraction (Scrapers)

| Module | Technology | Trigger |
|---|---|---|
| AGCO Store Registry | `httpx` + `BeautifulSoup` | Daily |
| Google Places Enrichment | Google Places REST API | Daily (post-AGCO) |
| Store Menu Scrapers | Scrapy + Playwright | Daily |
| OCS New Arrivals | `httpx` + `BeautifulSoup` | Daily |
| HiBuddy Price Comparison | Scrapy + Playwright | Daily |
| Reddit Sentiment | PRAW (official Reddit SDK) | Weekly |

### Layer 2 — Raw Storage (PostgreSQL raw schema)

All extracted data lands in the `raw` PostgreSQL schema without modification. This preserves the original source data for reprocessing and debugging.

Raw tables: `raw.agco_stores`, `raw.google_enrichments`, `raw.store_products`, `raw.product_pricing`, `raw.ocs_catalog`, `raw.hibuddy_listings`, `raw.reddit_posts`

### Layer 3 — Transformation (dbt)

dbt models clean, deduplicate, join, and aggregate raw data into business-ready tables.

- **Staging models** (`stg_*`) — type casting, deduplication, null handling
- **Intermediate models** (`int_*`) — cross-source joins (e.g., matching store products to OCS SKUs)
- **Mart models** (`mart_*`) — final analytics-ready tables consumed by the dashboard

### Layer 4 — Serving (Streamlit Dashboard)

The dashboard reads directly from the `mart` schema and presents five analytical pages. It runs as a standalone Docker service.

---

## 3. Module Descriptions

### 3.1 Store Discovery Module

**Purpose:** Build and maintain the master list of all licensed cannabis retailers within 35 km of Burlington.

**Steps:**
1. Download AGCO licensed retailer list (CSV or scraped from AGCO.ca)
2. Filter to Ontario cannabis retail licence type
3. Geocode each address using **GeoPy + Nominatim** (OpenStreetMap)
4. Calculate Haversine distance from Burlington centroid (43.3255° N, 79.7990° W)
5. Filter to stores ≤ 35 km
6. Enrich each store via **Google Places API**: phone number, website URL, hours of operation, Google rating
7. Upsert into `raw.agco_stores`

**Output:** ~30–80 store records (Burlington + surrounding municipalities)

---

### 3.2 Product Catalog Scraper

**Purpose:** Collect every product each store is currently listing — both on its website and via its integrated POS menu.

**Adapter Pattern:** Most cannabis stores use one of three POS/menu platforms. Each has a dedicated adapter:

| POS Platform | Detection Method | Scraping Approach |
|---|---|---|
| Dutchie | `<iframe>` with `dutchie.com` src | Playwright (JS-rendered) |
| Jane Technologies | `<iframe>` with `iheartjane.com` src | Playwright + Jane embed API |
| Cova POS | Direct store website HTML | Scrapy + CSS selectors |
| Custom / Other | Manual mapping per store | Per-store Scrapy spider |

**Collected fields per product:**
- Product name, brand, category (flower/pre-roll/vape/edible/concentrate/topical/tincture)
- THC % range, CBD % range
- Weight / size
- SKU / product ID
- Regular price, sale price, promo label
- In-stock status

---

### 3.3 Pricing Engine

**Purpose:** Maintain a complete historical record of every price change for every product across every store.

- Runs daily, appending new pricing snapshots to `raw.product_pricing`
- TimescaleDB hypertable on `scraped_at` column enables efficient time-range queries
- dbt mart model calculates price change frequency (volatility index) per product

---

### 3.4 OCS New Product Tracker

**Purpose:** Monitor the Ontario Cannabis Store catalog for new SKUs appearing within the last 30 days that have not yet appeared in Burlington-area stores.

- Scrapes OCS.ca product listing pages daily
- Compares against known local-store product list
- Flags new arrivals as "market entry opportunities"

---

### 3.5 Reddit Sentiment Analyzer

**Purpose:** Collect public commentary about products and brands relevant to the Burlington market.

**Subreddits monitored:**
- r/TheOCS
- r/canadients
- r/OnCannabis
- r/weed (filtered to Canadian context)

**Process:**
1. PRAW searches each subreddit for product names and brand keywords
2. Post text and top-level comments are stored in `raw.reddit_posts`
3. VADER (Valence Aware Dictionary and sEntiment Reasoner) assigns a compound sentiment score (−1 to +1) to each post
4. dbt aggregates sentiment by brand and product keyword

---

### 3.6 Analytics Engine (dbt Marts)

Five mart models power the dashboard's analytical pages. See [analytics-spec.md](analytics-spec.md) for full specification.

---

## 4. Data Flow Diagram

```
┌──────────────┐    ┌──────────────┐    ┌───────────────────┐
│  AGCO.ca     │    │ Google Places│    │ Store Websites    │
│  (Registry)  │    │    API       │    │ (Dutchie/Jane/    │
└──────┬───────┘    └──────┬───────┘    │  Cova/Custom)     │
       │                   │            └────────┬──────────┘
       │                   │                     │
       ▼                   ▼                     ▼
┌──────────────────────────────────────────────────────────┐
│           Airflow DAGs (Python scrapers)                 │
│  dag_store_discovery │ dag_product_scrape               │
│  dag_pricing_sync    │ dag_ocs_tracker                  │
│  dag_reddit_sentiment                                    │
└──────────────────────────┬───────────────────────────────┘
                           │ Raw INSERT / UPSERT
                           ▼
┌──────────────────────────────────────────────────────────┐
│              PostgreSQL 16 + TimescaleDB                 │
│                    raw.* schema                          │
│  agco_stores │ google_enrichments │ store_products       │
│  product_pricing (hypertable) │ ocs_catalog              │
│  hibuddy_listings │ reddit_posts                         │
└──────────────────────────┬───────────────────────────────┘
                           │ dbt run (daily)
                           ▼
┌──────────────────────────────────────────────────────────┐
│              PostgreSQL — staging.* schema               │
│  stg_stores │ stg_products │ stg_pricing                 │
│  stg_ocs_catalog │ stg_reddit                            │
└──────────────────────────┬───────────────────────────────┘
                           │ dbt run (marts)
                           ▼
┌──────────────────────────────────────────────────────────┐
│              PostgreSQL — marts.* schema                 │
│  mart_store_coverage     │ mart_product_matrix           │
│  mart_price_volatility   │ mart_new_arrivals             │
│  mart_sentiment_gap                                      │
└──────────────────────────┬───────────────────────────────┘
                           │ SQL reads
                           ▼
                ┌─────────────────────┐
                │  Streamlit Dashboard │
                │   localhost:8501     │
                └─────────────────────┘
```

---

## 5. Airflow DAG Schedule

| DAG ID | Schedule | Approximate Runtime | Dependencies |
|---|---|---|---|
| `dag_store_discovery` | Daily 02:00 ET | 15 min | None |
| `dag_product_scrape` | Daily 03:00 ET | 60–90 min | `dag_store_discovery` complete |
| `dag_pricing_sync` | Daily 04:30 ET | 30 min | `dag_product_scrape` complete |
| `dag_ocs_tracker` | Daily 05:00 ET | 10 min | None |
| `dag_dbt_transform` | Daily 06:00 ET | 15 min | Pricing + OCS complete |
| `dag_reddit_sentiment` | Weekly Sunday 01:00 ET | 20 min | None |

All times are Eastern Time (UTC−4/−5). Pipeline is complete and dashboard refreshed by **07:00 ET daily**.

---

## 6. Database Design Principles

1. **Raw schema preserved** — Source data is never mutated after landing; all cleaning happens in dbt.
2. **TimescaleDB hypertable on `product_pricing`** — The pricing table will accumulate millions of rows over months. The hypertable partitions by `scraped_at` for efficient range queries.
3. **JSONB for hours of operation** — Store hours vary by day and change seasonally. JSONB allows flexible storage without schema changes.
4. **Upsert pattern** — Store and product tables use `INSERT ... ON CONFLICT DO UPDATE` to avoid duplicates on re-runs.
5. **Soft deletes** — Stores and products are never hard-deleted; they receive `is_active = false` when no longer found in source data.

---

## 7. dbt Transformation Models

```
dbt/models/
├── staging/
│   ├── stg_stores.sql              -- Cleans + geocodes AGCO + Google data
│   ├── stg_products.sql            -- Normalises product names + categories
│   ├── stg_pricing.sql             -- Deduplicates daily price snapshots
│   ├── stg_ocs_catalog.sql         -- OCS product list + arrival date
│   └── stg_reddit.sql              -- Cleans posts, adds VADER score
├── intermediate/
│   ├── int_store_products.sql      -- Joins stores to their product list
│   ├── int_product_ocs_match.sql   -- Fuzzy-matches local SKUs to OCS catalog
│   └── int_price_changes.sql       -- Identifies rows where price changed
└── marts/
    ├── mart_store_coverage.sql     -- All stores enriched, with distance
    ├── mart_product_matrix.sql     -- Product × store ubiquity matrix
    ├── mart_price_volatility.sql   -- Price change count, volatility index
    ├── mart_new_arrivals.sql       -- OCS SKUs < 30 days old, local availability
    └── mart_sentiment_gap.sql      -- Reddit sentiment score × local store count
```

---

## 8. Dashboard Architecture

The Streamlit app (`dashboard/app.py`) has five pages:

| Page | Data Source | Key Visualisation |
|---|---|---|
| Store Coverage Map | `mart_store_coverage` | Folium map, 35 km radius overlay |
| Product Matrix | `mart_product_matrix` | Heatmap — products vs stores |
| Price Intelligence | `mart_price_volatility` | Line chart — price history per SKU |
| New Arrivals | `mart_new_arrivals` | Table — OCS new SKUs + local availability |
| Sentiment & Gaps | `mart_sentiment_gap` | Scatter — sentiment score vs store count |

---

## 9. Infrastructure & Deployment

All services run via **Docker Compose**:

| Service | Image | Port |
|---|---|---|
| PostgreSQL + TimescaleDB | `timescale/timescaledb:latest-pg16` | 5432 |
| Airflow Webserver | `apache/airflow:2.9` | 8080 |
| Airflow Scheduler | `apache/airflow:2.9` | — |
| Airflow Worker | `apache/airflow:2.9` | — |
| Streamlit Dashboard | Custom Python 3.11 image | 8501 |
| dbt Runner | Custom Python 3.11 image | — (CLI only) |

---

## 10. Folder Structure

```
vascora/
├── README.md
├── docker-compose.yml
├── .env.example
├── airflow/
│   ├── dags/
│   │   ├── dag_store_discovery.py
│   │   ├── dag_product_scrape.py
│   │   ├── dag_pricing_sync.py
│   │   ├── dag_ocs_tracker.py
│   │   ├── dag_dbt_transform.py
│   │   └── dag_reddit_sentiment.py
│   └── plugins/
├── scrapers/
│   ├── agco/
│   │   └── agco_spider.py
│   ├── google_places/
│   │   └── places_enricher.py
│   ├── store_menus/
│   │   ├── adapters/
│   │   │   ├── dutchie_adapter.py
│   │   │   ├── jane_adapter.py
│   │   │   └── cova_adapter.py
│   │   └── menu_spider.py
│   ├── ocs/
│   │   └── ocs_spider.py
│   ├── hibuddy/
│   │   └── hibuddy_spider.py
│   └── reddit/
│       └── reddit_collector.py
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   ├── tests/
│   └── macros/
├── dashboard/
│   ├── app.py
│   ├── pages/
│   │   ├── 1_Store_Coverage.py
│   │   ├── 2_Product_Matrix.py
│   │   ├── 3_Price_Intelligence.py
│   │   ├── 4_New_Arrivals.py
│   │   └── 5_Sentiment_Gap.py
│   └── requirements.txt
└── docs/
    ├── architecture.md          ← this file
    ├── data-sources.md
    ├── data-dictionary.md
    ├── analytics-spec.md
    ├── tools.md
    └── user-guide.md
```
