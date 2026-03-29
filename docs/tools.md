# Tools & Technology Stack

> **Document:** docs/tools.md
> **Project:** Vascora — MontKailash Cannabis Market Intelligence
> **Last Updated:** March 2026

---

## Table of Contents

1. [Stack Summary](#1-stack-summary)
2. [Core Language](#2-core-language)
3. [Data Extraction Layer](#3-data-extraction-layer)
4. [Data Storage Layer](#4-data-storage-layer)
5. [Data Transformation Layer](#5-data-transformation-layer)
6. [Pipeline Orchestration](#6-pipeline-orchestration)
7. [Natural Language Processing](#7-natural-language-processing)
8. [Analytics & Visualisation Layer](#8-analytics--visualisation-layer)
9. [Infrastructure & DevOps](#9-infrastructure--devops)
10. [Configuration & Utilities](#10-configuration--utilities)
11. [Development Tools](#11-development-tools)
12. [Tool Decision Log](#12-tool-decision-log)
13. [Dependency Installation](#13-dependency-installation)

---

## 1. Stack Summary

```
Language:       Python 3.11
Scraping:       Scrapy 2.11 + Playwright 1.44
Database:       PostgreSQL 16 + TimescaleDB 2.x
ORM:            SQLAlchemy 2.0 + Alembic 1.13
Transform:      dbt-core 1.8 + dbt-postgres 1.8
Orchestration:  Apache Airflow 2.9
NLP/Sentiment:  NLTK 3.8 (VADER) + Devvit Relay (optional PRAW 7.7)
Dashboard:      Streamlit 1.35 + Plotly 5.22 + Folium 0.17
Geo:            GeoPy 2.4
Containers:     Docker + Docker Compose v2
```

---

## 2. Core Language

### Python 3.11

| Attribute | Detail |
|---|---|
| Version | 3.11.x (latest 3.11 patch) |
| Why 3.11 specifically | Performance improvements (~10–15% faster than 3.10), exception notes, stable ecosystem support across all chosen libraries |
| Why not 3.12 | Several key dependencies (notably Airflow 2.9) have better-tested support against 3.11 |
| Runtime in Docker | `python:3.11-slim` base image for scraper/dbt/dashboard containers |

---

## 3. Data Extraction Layer

### Scrapy 2.11

| Attribute | Detail |
|---|---|
| Purpose | Primary web crawling framework for all static HTML scraping (AGCO, OCS, HiBuddy) |
| Why Scrapy | Battle-tested, async by default via Twisted, built-in middleware for rate limiting (`AUTOTHROTTLE`), item pipelines for clean data loading, broad industry adoption |
| Key features used | `AutoThrottle` (automatic rate control), `Item Pipelines` (write to PostgreSQL), `Spider middleware` (retry logic), `Exporters` (debug CSV export) |
| Documentation | https://docs.scrapy.org |

### Playwright for Python 1.44

| Attribute | Detail |
|---|---|
| Purpose | Headless browser automation for JavaScript-rendered store menus (Dutchie, Jane embed) |
| Why Playwright | Better than Selenium for modern JS SPAs; supports async; chromium headless; stealth mode available; maintained by Microsoft |
| Usage pattern | Integrated with Scrapy spiders via `scrapy-playwright` middleware for transparent async browser rendering |
| Key dependency | `scrapy-playwright` 0.0.34 bridges Scrapy and Playwright |
| Documentation | https://playwright.dev/python |

### Devvit Relay (Recommended Sentiment Ingestion)

| Attribute | Detail |
|---|---|
| Purpose | Receives subreddit content from a Devvit app and forwards into the Vascora ingestion endpoint |
| Why Devvit Relay | Avoids local Reddit API credential setup for the data pipeline; centralises Reddit auth in one managed app; easier for teams |
| Integration pattern | Devvit app sends signed JSON payloads to Vascora webhook (`/ingest/reddit`) |
| Auth model | Shared webhook token (`DEVVIT_WEBHOOK_TOKEN`) |
| Trade-off | Requires a deployed Devvit app and webhook hosting |

### PRAW (Python Reddit API Wrapper) 7.7 (Optional Fallback)

| Attribute | Detail |
|---|---|
| Purpose | Optional direct pull mode for Reddit posts/comments using the official API |
| Why PRAW | Useful when you prefer in-pipeline pull mode instead of webhook push mode |
| Rate limits | 60 requests/minute on free Reddit API tier |
| Documentation | https://praw.readthedocs.io |

### httpx 0.27

| Attribute | Detail |
|---|---|
| Purpose | Async HTTP client for direct REST API calls (Google Places API, fallback geocoding) |
| Why httpx | Supports both sync and async modes; HTTP/2 support; better than `requests` for async pipelines |
| Usage | Google Places API calls in `scrapers/google_places/places_enricher.py` |

### BeautifulSoup4 4.12

| Attribute | Detail |
|---|---|
| Purpose | HTML parsing for simpler scrapers (AGCO registry) |
| Why | Lightweight, reliable, works with Python's built-in `html.parser` |

---

## 4. Data Storage Layer

### PostgreSQL 16

| Attribute | Detail |
|---|---|
| Purpose | Primary relational database for all raw, staging, and mart data |
| Why PostgreSQL | JSONB support for hours of operation; `INSERT ... ON CONFLICT` upsert pattern; full SQL analytics; TimescaleDB extension availability; industry standard for data engineering |
| Docker image | `timescale/timescaledb:latest-pg16` |
| Connection | SQLAlchemy connection string: `postgresql+psycopg2://user:pass@localhost:5432/vascora` |

### TimescaleDB 2.x (PostgreSQL Extension)

| Attribute | Detail |
|---|---|
| Purpose | Time-series optimisation for the `raw.product_pricing` table |
| Why TimescaleDB | Converts the pricing table to a hypertable with automatic time-based partitioning; makes queries like "price history for the last 90 days" orders of magnitude faster; no separate infrastructure needed (runs as a Postgres extension) |
| Key feature used | `create_hypertable()` on `raw.product_pricing(scraped_at)` with 1-month chunk interval |
| Documentation | https://docs.timescale.com |

### SQLAlchemy 2.0

| Attribute | Detail |
|---|---|
| Purpose | Python ORM and SQL toolkit for database interactions in scrapers and dbt seed loading |
| Why 2.0 | Modern async engine support; improved type annotation; significant performance improvements over 1.x |
| Usage | All scraper database writes; Alembic migration base |

### Alembic 1.13

| Attribute | Detail |
|---|---|
| Purpose | Database schema migration management |
| Why | Works natively with SQLAlchemy 2.0; generates versioned migration scripts; supports rollback |
| Usage | All DDL changes (CREATE TABLE, ALTER TABLE) are managed as Alembic migrations |

### psycopg2-binary 2.9

| Attribute | Detail |
|---|---|
| Purpose | PostgreSQL driver for SQLAlchemy |
| Why binary | Eliminates native library compilation requirement in Docker |

---

## 5. Data Transformation Layer

### dbt-core 1.8

| Attribute | Detail |
|---|---|
| Purpose | SQL-based transformation of raw data into staging and mart models |
| Why dbt | Industry-standard for ELT transformations; SQL-first (no Python required for transforms); built-in testing (`not_null`, `unique`, `accepted_values`); auto-generated lineage documentation; modular model structure |
| Key features used | `staging` → `intermediate` → `marts` model layers; `ref()` for dependency tracking; `source()` for raw schema references; `dbt test` for data quality |
| Documentation | https://docs.getdbt.com |

### dbt-postgres 1.8

| Attribute | Detail |
|---|---|
| Purpose | dbt adapter for PostgreSQL |
| Note | Must match dbt-core minor version (both 1.8.x) |

---

## 6. Pipeline Orchestration

### Apache Airflow 2.9

| Attribute | Detail |
|---|---|
| Purpose | Schedules and orchestrates all pipeline DAGs on a daily cadence |
| Why Airflow | Most widely recognised orchestration tool in the data engineering industry; rich UI for monitoring DAG runs and task logs; robust retry logic; easy dependency chaining between DAGs; large community |
| Deployment | `apache/airflow:2.9` Docker image with custom requirements |
| Key DAGs | 6 DAGs covering store discovery, product scrape, pricing sync, OCS tracking, dbt transformation, and Reddit sentiment (see [architecture.md](architecture.md)) |
| Data storage | Airflow metadata DB runs on the same PostgreSQL instance in a separate `airflow` schema |
| Documentation | https://airflow.apache.org/docs |

---

## 7. Natural Language Processing

### NLTK 3.8 — VADER Sentiment Analyser

| Attribute | Detail |
|---|---|
| Purpose | Assigns a compound sentiment score (−1.0 to +1.0) to Reddit posts |
| Algorithm | VADER (Valence Aware Dictionary and sEntiment Reasoner) — a lexicon and rule-based model designed specifically for social media text |
| Why VADER | Pre-trained on social media language; handles slang, emoji, and intensifiers; no GPU required; no API cost; runs entirely locally; fast (~100k posts/minute) |
| Why not OpenAI GPT | API cost, external dependency, and latency would make weekly batch processing expensive and fragile for a POC |
| Output | `vader_compound` score: ≥ 0.05 = positive, ≤ −0.05 = negative, between = neutral |
| Documentation | https://www.nltk.org/api/nltk.sentiment.vader.html |

### PRAW 7.7 (also listed under Extraction)

Used here in the NLP context — PRAW collects the text, and VADER processes it in the same collection step.

---

## 8. Analytics & Visualisation Layer

### Streamlit 1.35

| Attribute | Detail |
|---|---|
| Purpose | Interactive web dashboard serving all five analytics pages |
| Why Streamlit | Pure Python — no frontend (JavaScript/React) expertise required; rapid iteration; native support for Plotly, Folium, and pandas DataFrames; built-in export/download widgets |
| Deployment | Custom Docker image, exposed on port 8501 |
| Structure | Multi-page app with `pages/` directory |
| Documentation | https://docs.streamlit.io |

### Plotly 5.22

| Attribute | Detail |
|---|---|
| Purpose | All interactive charts (line charts, heatmaps, scatter plots, bar charts, histograms) |
| Why Plotly | Native Streamlit integration via `st.plotly_chart()`; highly interactive (tooltips, zoom, filter); professional visual output |
| Documentation | https://plotly.com/python |

### Folium 0.17

| Attribute | Detail |
|---|---|
| Purpose | Interactive map rendering for the Store Coverage Map page |
| Why Folium | Generates Leaflet.js maps from Python; supports custom markers, circle overlays, popups, and tooltips; renders inline in Streamlit via `folium_static()` |
| Key features used | `folium.Map`, `folium.Marker`, `folium.Circle` (35 km radius), `folium.Popup` (store detail cards) |
| Documentation | https://python-visualization.github.io/folium |

### pandas 2.1

| Attribute | Detail |
|---|---|
| Purpose | Data manipulation in scraper pipelines and dashboard data loading |
| Why 2.1 | Arrow-backed dataframes for memory efficiency; improved nullable dtypes |

### numpy 1.26

| Attribute | Detail |
|---|---|
| Purpose | Numerical operations (Haversine distance calculation, statistical aggregations) |

---

## 9. Infrastructure & DevOps

### Docker Engine + Docker Compose v2

| Attribute | Detail |
|---|---|
| Purpose | Containerises all services for reproducible, platform-independent deployment |
| Why Docker Compose | Single-command startup of the entire 6-service stack; network isolation between services; volume mounting for data persistence; standard for local data engineering POC development |
| Services containerised | PostgreSQL+TimescaleDB, Airflow Webserver, Airflow Scheduler, Airflow Worker, Streamlit Dashboard, dbt Runner |

---

## 10. Configuration & Utilities

### python-dotenv 1.0

| Attribute | Detail |
|---|---|
| Purpose | Loads `.env` file into environment variables at runtime |
| Usage | All scrapers and the dashboard read API keys and DB credentials from environment variables; never hardcoded |

### GeoPy 2.4

| Attribute | Detail |
|---|---|
| Purpose | Geocoding (address → lat/lng) and Haversine distance calculation |
| Geocoder used | Nominatim (OpenStreetMap) — free, no API key required |
| Fallback geocoder | Google Geocoding API (same key as Places API) |
| Key function | `geopy.distance.geodesic()` for distance calculations |

### structlog 24.x

| Attribute | Detail |
|---|---|
| Purpose | Structured JSON logging across all scrapers and Airflow tasks |
| Why structured logging | JSON logs are parseable by Airflow's log viewer and easily shipped to a log aggregator in production |

### tenacity 8.x

| Attribute | Detail |
|---|---|
| Purpose | Retry logic with exponential backoff for HTTP requests and API calls |
| Usage | Wraps all external API calls (Google Places, PRAW) and scraper requests |

---

## 11. Development Tools

| Tool | Version | Purpose |
|---|---|---|
| `black` | 24.x | Python code formatter — enforces consistent style |
| `ruff` | 0.4.x | Fast Python linter — catches errors and style issues |
| `pytest` | 8.x | Unit testing for scraper adapters and transformation logic |
| `pytest-mock` | 3.x | Mocking HTTP responses in scraper tests |
| `pre-commit` | 3.x | Git hook runner for black + ruff before commits |
| Git | — | Version control |
| VS Code | — | Recommended IDE; `.vscode/` workspace settings included |

---

## 12. Tool Decision Log

Decisions made during technology selection:

| Decision | Choice Made | Alternatives Considered | Reason |
|---|---|---|---|
| Time-series database | TimescaleDB (PostgreSQL extension) | InfluxDB, QuestDB | Keeps the stack a single database; no additional service; full SQL support; sufficient for POC scale |
| Pipeline orchestration | Apache Airflow 2.9 | Prefect 2.x, Dagster | Airflow is most widely recognised in data engineering interviews; UI is well-known; documentation is mature |
| Sentiment analysis | VADER (NLTK) | OpenAI GPT-4o API, HuggingFace transformers | Zero cost; no external API dependency; fast batch processing; adequate accuracy for cannabis social media text |
| Dashboard | Streamlit | Metabase, Grafana, Plotly Dash | Pure Python; fastest iteration; native Plotly + Folium support; no frontend expertise required for POC |
| Web scraping | Scrapy + Playwright | Selenium, Puppeteer, requests-html | Scrapy is production-grade with built-in rate limiting; Playwright handles modern JS better than Selenium; both have strong Python support |
| HTTP client | httpx | requests, aiohttp | httpx supports both sync + async; HTTP/2; modern API similar to requests |
| Transformation | dbt-core | pandas scripts, SQLMesh | dbt is the industry standard; reusable, tested, documented SQL models; lineage is a major advantage for interview demonstration |
| ORM | SQLAlchemy 2.0 | peewee, tortoise-orm | SQLAlchemy is the Python standard; Alembic migration support; async engine for future use |

---

## 13. Dependency Installation

### Full requirements list (Python packages)

```
# requirements.txt — shared base
python-dotenv==1.0.0
structlog==24.1.0
tenacity==8.3.0
sqlalchemy==2.0.30
alembic==1.13.1
psycopg2-binary==2.9.9
pandas==2.1.4
numpy==1.26.4
geopy==2.4.1
httpx==0.27.0
beautifulsoup4==4.12.3

# requirements-scrapers.txt
scrapy==2.11.2
scrapy-playwright==0.0.34
playwright==1.44.0
praw==7.7.1
nltk==3.8.1

# requirements-dbt.txt
dbt-core==1.8.4
dbt-postgres==1.8.4

# requirements-dashboard.txt
streamlit==1.35.0
plotly==5.22.0
folium==0.17.0
streamlit-folium==0.20.0

# requirements-dev.txt
pytest==8.2.2
pytest-mock==3.14.0
black==24.4.2
ruff==0.4.7
pre-commit==3.7.1
```

### One-time Playwright setup

After installing `playwright`, download the Chromium browser binary:

```bash
playwright install chromium
```

This is handled automatically in the Docker build (`Dockerfile.scrapers`).

### NLTK corpus download

VADER requires its lexicon to be downloaded once:

```python
import nltk
nltk.download('vader_lexicon')
```

This is handled in the scraper container's `entrypoint.sh`.
