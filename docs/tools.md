# Tools and Stack

> Document: docs/tools.md
> Project: Vascora
> Last Updated: March 2026

---

## 1. Runtime Stack

| Layer | Tool | Version |
|---|---|---|
| API framework | FastAPI | 0.115.0 |
| API server | Uvicorn | 0.30.6 |
| Database | PostgreSQL | 16 |
| DB access | SQLAlchemy | 2.0.35 |
| Postgres driver | psycopg2-binary | 2.9.9 |
| Config management | pydantic-settings | 2.5.2 |
| HTTP client | httpx | 0.27.2 |
| Environment loading | python-dotenv | 1.0.1 |
| Container runtime | Docker plus Compose | v2 |

---

## 2. Why This Stack

- FastAPI provides concise API development and validation.
- PostgreSQL keeps ingestion and analytics in a single operational store.
- SQLAlchemy simplifies transaction handling for API writes.
- SQL-based marts are transparent and easy to review in interviews.
- Collector scripts keep source logic isolated and reusable.
- Docker Compose provides one-command local startup.

---

## 3. Implemented App Modules

### API modules

- app.api.ingest
- app.api.analytics
- app.api.sentiment (optional path)

### Collector modules

- app.collectors.agco
- app.collectors.products
- app.collectors.pricing
- app.collectors.ocs

### Pipeline modules

- app.pipelines.refresh_marts
- app.pipelines.run_all

---

## 4. SQL Assets

- sql/init.sql: creates raw schema and ingestion tables
- sql/marts.sql: creates marts schema and analytics views

---

## 5. API Endpoints in Use

### Ingestion

- POST /ingest/stores
- POST /ingest/products
- POST /ingest/pricing
- POST /ingest/ocs

### Analytics

- POST /analytics/refresh
- GET /analytics/store-coverage
- GET /analytics/product-matrix
- GET /analytics/price-volatility
- GET /analytics/new-arrivals
- GET /analytics/export/{dataset}

### Optional later

- POST /ingest/reddit

---

## 6. Security Controls

- Ingestion and refresh operations are token protected using X-Api-Token.
- Optional Reddit webhook path is protected using X-Webhook-Token.
- Secrets are expected in .env and excluded by .gitignore.

---

## 7. Operational Commands

Start services:

```bash
docker compose up -d --build
```

Run full pipeline:

```bash
docker compose exec ingest-api python -m app.pipelines.run_all \
  --agco-csv data/samples/agco_stores_template.csv \
  --products-csv data/samples/store_products_template.csv \
  --pricing-csv data/samples/product_pricing_template.csv \
  --ocs-csv data/samples/ocs_catalog_template.csv
```

Refresh marts only:

```bash
docker compose exec ingest-api python -m app.pipelines.refresh_marts
```
