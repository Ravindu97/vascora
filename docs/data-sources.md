# Data Sources Reference

> Document: docs/data-sources.md
> Project: Vascora
> Last Updated: March 2026

---

## 1. Current Implemented Sources

| Source | Purpose | Access | Status |
|---|---|---|---|
| AGCO store extract (CSV) | Licensed store directory baseline | CSV file input to collector | Implemented |
| Google Geocoding API | Missing lat/lng enrichment for store addresses | HTTP API call from AGCO collector | Implemented (optional but recommended) |
| Store product extract (CSV) | Store catalog ingestion | CSV file input to collector | Implemented |
| Store pricing extract (CSV) | Price timeline ingestion | CSV file input to collector | Implemented |
| OCS catalog extract (CSV) | New item and product baseline | CSV file input to collector | Implemented |

---

## 2. AGCO Store Source

### Purpose

Build the authoritative local store list for Burlington radius analysis.

### Collector

- app.collectors.agco

### Required fields (minimum)

- licence_number
- store_name
- street_address
- city

### Optional enrichments

- latitude, longitude from source file
- if absent, collector may geocode with Google API using GOOGLE_PLACES_API_KEY

### Radius filtering

Collector computes Haversine distance from Burlington center and marks:

- distance_km
- within_35km

Based on:

- BURLINGTON_LAT
- BURLINGTON_LNG
- MARKET_RADIUS_KM

---

## 3. Product Source

### Purpose

Ingest live product catalog snapshots per store.

### Collector

- app.collectors.products

### Required fields (minimum)

- licence_number
- product_name

### Typical optional fields

- pos_sku
- brand_name
- category_raw
- thc and cbd ranges
- weight_grams
- in_stock

---

## 4. Pricing Source

### Purpose

Ingest regular and sale pricing snapshots for volatility and promotion analytics.

### Collector

- app.collectors.pricing

### Required fields (minimum)

- licence_number
- product_name
- regular_price_cad

### Typical optional fields

- pos_sku
- sale_price_cad
- promo_label
- promo_start_date
- promo_end_date
- in_stock

---

## 5. OCS Catalog Source

### Purpose

Track new products and compare local availability against provincial catalog.

### Collector

- app.collectors.ocs

### Required fields (minimum)

- ocs_sku
- product_name

### Typical optional fields

- brand_name
- category_raw
- thc and cbd ranges
- weight_grams
- ocs_price_cad
- first_seen_at
- last_seen_at

---

## 6. Future Optional Source: Reddit/Devvit

Not required for current run path.

Planned integration path:

- Source mode: devvit_webhook
- Endpoint: POST /ingest/reddit
- Token: DEVVIT_WEBHOOK_TOKEN

This is additive and does not affect current non-sentiment ingestion.

---

## 7. Reliability Notes

- CSV ingest is deterministic and repeatable for interview/demo runs.
- API ingestion is idempotent where upsert keys are defined.
- Pricing table is append-oriented and should be loaded periodically to build time-series depth.
- Geocoding is best-effort; rows without geocode may be excluded by radius filtering unless source includes coordinates.
