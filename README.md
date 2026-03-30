# MontKailash Cannabis — Market Intelligence Platform

> **Project Code:** Vascora
> **Version:** 1.0.0 (POC)
> **Target Market:** Burlington, Ontario, Canada — 35 km radius
> **Data Refresh:** Daily automated pipeline

---

## Overview

Vascora is a competitive-intelligence data platform built for **MontKailash Cannabis**. It automatically collects, transforms, and visualises cannabis retail data across all licensed stores within a 35 km radius of Burlington, ON — giving MontKailash a daily, data-driven view of:

- Which competitors are operating and where
- What products are on shelf, at what prices, and when prices change
- Which new OCS products are entering the local market
- What public sentiment exists around specific brands and products on Reddit

---

## Business Goals

| Goal | Output |
|---|---|
| Know every competitor in the market | Enriched store list with owner/contact details |
| Understand what products are trending | Cross-store product ubiquity matrix |
| Track real-time pricing changes | Pricing time-series with volatility index |
| Spot new products before competitors shelf them | OCS new-arrival tracker (< 30 days) |
| Understand consumer sentiment | Reddit sentiment reports per brand/product |
| Surface stocking opportunities | Sentiment–gap analysis report |

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES (External)                  │
│  AGCO Registry │ Google Places │ Store Websites │ OCS       │
│  HiBuddy.ca    │ Weedmaps      │ Reddit (PRAW)              │
└────────────────────────┬────────────────────────────────────┘
                         │ Ingestion Layer (Scrapy + Playwright)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               PostgreSQL 16 + TimescaleDB                   │
│  raw_stores │ raw_products │ pricing_history │ ocs_arrivals │
│  sentiment_posts                                            │
└────────────────────────┬────────────────────────────────────┘
                         │ dbt Transformations
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Analytics Marts                          │
│  mart_store_coverage │ mart_product_matrix                  │
│  mart_price_volatility │ mart_sentiment_gap                 │
└────────────────────────┬────────────────────────────────────┘
                         │ Streamlit Dashboard
                         ▼
                  localhost:8501
```

---

## Quick Start (3 Commands)

**Prerequisites:** Docker Desktop installed and running, API keys configured (see [User Guide](docs/user-guide.md)).

```bash
# 1. Clone the repository
git clone https://github.com/montkailash/vascora.git && cd vascora

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see docs/user-guide.md § API Key Setup)

# 3. Launch all services
docker compose up -d
```

| Service | URL | Credentials |
|---|---|---|
| Airflow UI (pipeline scheduler) | http://localhost:8080 | admin / admin |
| Streamlit Dashboard | http://localhost:8501 | — |
| PostgreSQL | localhost:5432 | See .env |

---

## Implementation (Reddit Ready, Optional)

The ingestion layer is fully usable without sentiment ingestion. It includes:

- Store ingestion (`raw.agco_stores`)
- Product ingestion (`raw.store_products`)
- Pricing ingestion (`raw.product_pricing`)
- OCS catalog ingestion (`raw.ocs_catalog`)

### 1) Configure ingestion env values

Set these values in `.env`:

```dotenv
SENTIMENT_SOURCE=off
INGEST_API_TOKEN=change_me_ingest_token
API_BASE_URL=http://localhost:8000
```

### 2) Run AGCO collector (CSV -> API)

Use the template at `data/samples/agco_stores_template.csv`, then run:

```bash
PYTHONPATH=src python -m app.collectors.agco \
    --csv-path data/samples/agco_stores_template.csv
```

The collector will:

- Parse AGCO-like rows
- Geocode missing lat/lng via Google Geocoding API (if key exists)
- Compute Burlington distance and filter by `MARKET_RADIUS_KM`
- Batch POST to `POST /ingest/stores` with `X-Api-Token`

### 3) Run product/pricing/OCS collectors

```bash
# Product catalog -> /ingest/products
PYTHONPATH=src python -m app.collectors.products \
    --csv-path data/samples/store_products_template.csv

# Pricing history -> /ingest/pricing
PYTHONPATH=src python -m app.collectors.pricing \
    --csv-path data/samples/product_pricing_template.csv

# OCS catalog -> /ingest/ocs
PYTHONPATH=src python -m app.collectors.ocs \
    --csv-path data/samples/ocs_catalog_template.csv
```

### 4) Build analytics marts from raw data

```bash
PYTHONPATH=src python -m app.pipelines.refresh_marts
```

Or via API (protected by `X-Api-Token`):

```bash
curl -X POST http://localhost:8000/analytics/refresh \
    -H "X-Api-Token: $INGEST_API_TOKEN"
```

### 5) Query analytics outputs

```bash
curl "http://localhost:8000/analytics/store-coverage?limit=50"
curl "http://localhost:8000/analytics/product-matrix?limit=50"
curl "http://localhost:8000/analytics/price-volatility?limit=50"
curl "http://localhost:8000/analytics/new-arrivals?limit=50"
```

### 6) Export analytics datasets as CSV

```bash
curl -L "http://localhost:8000/analytics/export/store-coverage?limit=5000" -o store-coverage.csv
curl -L "http://localhost:8000/analytics/export/product-matrix?limit=5000" -o product-matrix.csv
curl -L "http://localhost:8000/analytics/export/price-volatility?limit=5000" -o price-volatility.csv
curl -L "http://localhost:8000/analytics/export/new-arrivals?limit=5000" -o new-arrivals.csv
```

### 7) Run full ingestion + transform in one command

```bash
PYTHONPATH=src python -m app.pipelines.run_all \
    --agco-csv data/samples/agco_stores_template.csv \
    --products-csv data/samples/store_products_template.csv \
    --pricing-csv data/samples/product_pricing_template.csv \
    --ocs-csv data/samples/ocs_catalog_template.csv
```

---

## Documentation Index

| Document | Purpose |
|---|---|
| [docs/architecture.md](docs/architecture.md) | System design, module breakdown, data flow, folder structure |
| [docs/data-sources.md](docs/data-sources.md) | All data sources, API access, rate limits, coverage notes |
| [docs/data-dictionary.md](docs/data-dictionary.md) | Full database schema with column-level definitions |
| [docs/analytics-spec.md](docs/analytics-spec.md) | Five analytics output specifications and business logic |
| [docs/tools.md](docs/tools.md) | Full tooling list with versions and justification |
| [docs/user-guide.md](docs/user-guide.md) | Step-by-step setup, operation, and troubleshooting guide |

---

## Burlington 35 km Coverage Area

The pipeline automatically filters all discovered stores to those within **35 km** of Burlington city centre (43.3255° N, 79.7990° W). This typically includes:

- Burlington (core target)
- Oakville
- Hamilton (north-east)
- Waterdown
- Dundas / Ancaster
- Milton (partial)
- Stoney Creek
- Grimsby (edge)
- Mississauga (south-west edge)

---

## Repository Structure

```
vascora/
├── README.md
├── docker-compose.yml
├── .env.example
├── airflow/
│   └── dags/
│       ├── dag_store_discovery.py
│       ├── dag_product_scrape.py
│       ├── dag_pricing_sync.py
│       ├── dag_ocs_tracker.py
│       └── dag_reddit_sentiment.py
├── scrapers/
│   ├── agco/
│   ├── google_places/
│   ├── store_menus/
│   │   ├── adapters/            # Per-POS-platform adapters (Dutchie, Jane, Cova)
│   ├── ocs/
│   ├── hibuddy/
│   └── reddit/
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   └── marts/
│   └── tests/
├── dashboard/
│   └── app.py
└── docs/
    ├── architecture.md
    ├── data-sources.md
    ├── data-dictionary.md
    ├── analytics-spec.md
    ├── tools.md
    └── user-guide.md
```

---

## Legal & Compliance Notes

- All scraping targets are **publicly accessible retail websites**. No login-walled data is collected.
- All scrapers respect `robots.txt` and enforce a minimum **3-second delay** between requests per domain.
- Reddit data is collected via the **official PRAW API** under Reddit's public data terms.
- AGCO retailer data is publicly published by the Ontario government.
- This platform does **not** store any personally identifiable customer data.

---

## Contact

**Client:** MontKailash Cannabis
**Built by:** Vascora Data Engineering
**Date:** March 2026
