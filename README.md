# Vascora

Practical data ingestion and analytics API for cannabis market intelligence in Burlington, ON (35 km radius), built so Reddit integration can be added later without changing core workflows.

## What Runs in This Repo

- PostgreSQL database (raw + marts schemas)
- FastAPI service for ingestion and analytics
- Collector scripts for:
    - AGCO stores
    - Store products
    - Product pricing
    - OCS catalog
- SQL marts refresh pipeline
- CSV export endpoints for analytics outputs

## Prerequisites

- Docker Desktop
- Docker Compose v2
- Git
- Optional for collectors (if running on host instead of container): Python 3.11 + pip

## 1) Configure Environment

Copy template and edit values:

```bash
cp .env.example .env
```

Minimum required values in `.env`:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=vascora
POSTGRES_PASSWORD=change_me_to_a_strong_password
POSTGRES_DB=vascora

API_BASE_URL=http://localhost:8000
INGEST_API_TOKEN=change_me_ingest_token

BURLINGTON_LAT=43.3255
BURLINGTON_LNG=-79.7990
MARKET_RADIUS_KM=35

# Keep sentiment off for now (Reddit can be enabled later)
SENTIMENT_SOURCE=off
DEVVIT_WEBHOOK_TOKEN=replace_with_shared_secret

# Needed only if AGCO rows are missing lat/lng and geocoding is required
GOOGLE_PLACES_API_KEY=AIza...your_key_here...
```

## 2) Start Services

```bash
docker compose up -d --build
```

Services:

- API: http://localhost:8000
- DB: localhost:5432

Health check:

```bash
curl http://localhost:8000/healthz
```

Expected:

```json
{"status":"ok"}
```

## 3) Initialize Database Schema

For first run on a clean DB volume, schema is auto-created from [sql/init.sql](sql/init.sql).

If you already have an old DB volume and need to re-apply schema changes:

```bash
docker compose exec db psql -U vascora -d vascora -f /docker-entrypoint-initdb.d/init.sql
```

## 4) Ingest Data (Option A: One Command)

Use sample files to validate the full pipeline quickly:

```bash
docker compose exec ingest-api python -m app.pipelines.run_all \
    --agco-csv data/samples/agco_stores_template.csv \
    --products-csv data/samples/store_products_template.csv \
    --pricing-csv data/samples/product_pricing_template.csv \
    --ocs-csv data/samples/ocs_catalog_template.csv
```

What this does:

1. Ingest stores -> `raw.agco_stores`
2. Ingest products -> `raw.store_products`
3. Ingest pricing -> `raw.product_pricing`
4. Ingest OCS catalog -> `raw.ocs_catalog`
5. Refresh marts from raw data

## 5) Ingest Data (Option B: Step by Step)

### Stores

```bash
docker compose exec ingest-api python -m app.collectors.agco \
    --csv-path data/samples/agco_stores_template.csv
```

### Products

```bash
docker compose exec ingest-api python -m app.collectors.products \
    --csv-path data/samples/store_products_template.csv
```

### Pricing

```bash
docker compose exec ingest-api python -m app.collectors.pricing \
    --csv-path data/samples/product_pricing_template.csv
```

### OCS Catalog

```bash
docker compose exec ingest-api python -m app.collectors.ocs \
    --csv-path data/samples/ocs_catalog_template.csv
```

### Refresh Marts

```bash
docker compose exec ingest-api python -m app.pipelines.refresh_marts
```

## 6) Query Analytics APIs

JSON endpoints:

```bash
curl "http://localhost:8000/analytics/store-coverage?limit=50"
curl "http://localhost:8000/analytics/product-matrix?limit=50"
curl "http://localhost:8000/analytics/price-volatility?limit=50"
curl "http://localhost:8000/analytics/new-arrivals?limit=50"
```

Force marts refresh via API (protected):

```bash
curl -X POST http://localhost:8000/analytics/refresh \
    -H "X-Api-Token: $INGEST_API_TOKEN"
```

## 7) Export CSV Outputs

```bash
curl -L "http://localhost:8000/analytics/export/store-coverage?limit=5000" -o store-coverage.csv
curl -L "http://localhost:8000/analytics/export/product-matrix?limit=5000" -o product-matrix.csv
curl -L "http://localhost:8000/analytics/export/price-volatility?limit=5000" -o price-volatility.csv
curl -L "http://localhost:8000/analytics/export/new-arrivals?limit=5000" -o new-arrivals.csv
```

## 8) Load Real Data Files

Replace sample paths with your real files:

```bash
docker compose exec ingest-api python -m app.collectors.agco --csv-path /app/data/agco.csv
docker compose exec ingest-api python -m app.collectors.products --csv-path /app/data/products.csv
docker compose exec ingest-api python -m app.collectors.pricing --csv-path /app/data/pricing.csv
docker compose exec ingest-api python -m app.collectors.ocs --csv-path /app/data/ocs.csv
docker compose exec ingest-api python -m app.pipelines.refresh_marts
```

If you need these files available in container path `/app/data`, place them under workspace `data/` on host.

## 9) API Contract (Ingestion)

Protected ingestion endpoints use header:

- `X-Api-Token: <INGEST_API_TOKEN>`

Endpoints:

- `POST /ingest/stores`
- `POST /ingest/products`
- `POST /ingest/pricing`
- `POST /ingest/ocs`

Each endpoint accepts JSON:

```json
{
    "records": [
        {"...": "..."}
    ]
}
```

## 10) Reddit Integration Later (Optional)

Current setup is ready for future integration. To add later:

1. Set `SENTIMENT_SOURCE=devvit_webhook`
2. Configure `DEVVIT_WEBHOOK_TOKEN`
3. Start sending payloads to `POST /ingest/reddit`

No changes are required to existing collectors, marts, or exports.

## 11) Troubleshooting

### API not reachable

```bash
docker compose ps
docker compose logs ingest-api
```

### Database schema missing after restart

If using an existing DB volume, re-run schema manually (Step 3).

### 401 on ingestion routes

Ensure header token matches `INGEST_API_TOKEN` exactly.

### Empty analytics results

1. Confirm raw tables have data.
2. Run marts refresh command.

### FileNotFoundError for sample CSV or marts SQL

If you see errors like `data/samples/...` or `sql/marts.sql` not found from `ingest-api`, ensure these mounts exist in [docker-compose.yml](docker-compose.yml):

- `./data:/app/data:ro`
- `./sql:/app/sql:ro`

Then rebuild and restart:

```bash
docker compose up -d --build
```

### Port conflicts

If `5432` or `8000` is occupied, change host port mapping in [docker-compose.yml](docker-compose.yml).

## Project References

- [docs/user-guide.md](docs/user-guide.md)
- [docs/data-dictionary.md](docs/data-dictionary.md)
- [docs/analytics-spec.md](docs/analytics-spec.md)

## 12) Interview Handover Checklist

Use this checklist before submitting your exercise.

### A. Technical completion

- Services start successfully (`docker compose up -d --build`)
- Ingestion runs without failures (one-command or step-by-step)
- Marts refresh completes
- Analytics endpoints return non-empty results
- CSV export files are generated

### B. Required business outputs

- Competitor store list (name, address, phone, hours if available, licence holder)
- Product catalog per store
- Regular and sale pricing snapshots
- New OCS arrivals and local availability gaps

### C. Files to include in submission

- `store-coverage.csv`
- `product-matrix.csv`
- `price-volatility.csv`
- `new-arrivals.csv`
- This README and docs folder

### D. Scope declaration (recommended)

If sentiment is deferred, state clearly:

1. Current delivery includes ingestion, pricing intelligence, and OCS opportunity tracking.
2. Reddit/Devvit ingestion is designed and endpoint-ready (`POST /ingest/reddit`) but intentionally deferred.

## 13) Recommended Execution Sequence

For repeatable runs, execute in this exact order:

1. Start services
2. Ingest stores
3. Ingest products
4. Ingest pricing
5. Ingest OCS catalog
6. Refresh marts
7. Query analytics endpoints
8. Export CSV outputs
