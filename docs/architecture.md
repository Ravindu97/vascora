# System Architecture

> Document: docs/architecture.md
> Project: Vascora
> Last Updated: March 2026

---

## 1. Architecture Summary

The current implementation is an ingestion-first service with PostgreSQL-backed analytics views.

Flow:

1. CSV/source input
2. Collector scripts normalize records
3. Ingestion API writes to raw schema
4. SQL marts are refreshed from raw schema
5. Analytics API serves JSON and CSV outputs

Reddit/Devvit is optional and can be integrated later without changing core ingestion endpoints or marts.

---

## 2. Runtime Components

### 2.1 Database

- Service: PostgreSQL 16
- Container: db
- Port: 5432
- Schemas:
  - raw for ingested source-aligned data
  - marts for analytics-ready views

### 2.2 API Service

- Service: FastAPI
- Container: ingest-api
- Port: 8000
- Modules:
  - app.api.ingest for protected batch ingestion routes
  - app.api.analytics for marts refresh plus output queries and exports
  - app.api.sentiment for optional Reddit ingestion later

### 2.3 Collectors

Host or container executable Python collectors:

- app.collectors.agco
- app.collectors.products
- app.collectors.pricing
- app.collectors.ocs

All collectors post batched payloads to ingestion routes using X-Api-Token.

### 2.4 Pipelines

- app.pipelines.refresh_marts: executes SQL view definitions in sql/marts.sql
- app.pipelines.run_all: runs all collectors then refreshes marts

---

## 3. Data Flow

```text
CSV files or source extracts
        |
        v
Collector scripts (normalize, validate, enrich)
        |
        v
POST /ingest/stores|products|pricing|ocs (token protected)
        |
        v
raw.agco_stores
raw.store_products
raw.product_pricing
raw.ocs_catalog
        |
        v
python -m app.pipelines.refresh_marts
        |
        v
marts.store_coverage
marts.product_matrix
marts.price_volatility
marts.new_arrivals
        |
        v
GET /analytics/... and /analytics/export/...
```

---

## 4. Ingestion API Surface

Protected by header:

- X-Api-Token: INGEST_API_TOKEN

Routes:

- POST /ingest/stores
- POST /ingest/products
- POST /ingest/pricing
- POST /ingest/ocs

Body contract:

```json
{
  "records": [
    {"...": "..."}
  ]
}
```

Optional later:

- POST /ingest/reddit

---

## 5. Analytics API Surface

- POST /analytics/refresh (token protected)
- GET /analytics/store-coverage
- GET /analytics/product-matrix
- GET /analytics/price-volatility
- GET /analytics/new-arrivals
- GET /analytics/export/{dataset}

Supported datasets:

- store-coverage
- product-matrix
- price-volatility
- new-arrivals

---

## 6. Deployment Model

Docker Compose services currently defined:

- db
- ingest-api

Initialization:

- sql/init.sql creates raw schema and ingestion tables
- sql/marts.sql creates marts schema and analytics views

---

## 7. Extension Strategy

Reddit integration can be added later as a source extension:

1. Enable sentiment source in .env
2. Push Reddit payloads into raw.reddit_posts
3. Add optional sentiment marts or views
4. Add sentiment analytics endpoint and export

No breaking change is required in existing non-sentiment collectors or analytics endpoints.
