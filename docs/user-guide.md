# User Guide

> **Document:** docs/user-guide.md
> **Project:** Vascora — MontKailash Cannabis Market Intelligence
> **Last Updated:** March 2026
> **Audience:** Data engineers setting up the system; business users reading the dashboard

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Obtaining API Keys](#2-obtaining-api-keys)
3. [Environment Configuration](#3-environment-configuration)
4. [First-Time Setup](#4-first-time-setup)
5. [Running the Pipeline](#5-running-the-pipeline)
6. [Triggering DAGs Manually](#6-triggering-dags-manually)
7. [Using the Dashboard](#7-using-the-dashboard)
8. [Reading the Analytics Outputs](#8-reading-the-analytics-outputs)
9. [Export & Reporting](#9-export--reporting)
10. [Burlington 35 km Coverage Map](#10-burlington-35-km-coverage-map)
11. [Extending the Pipeline](#11-extending-the-pipeline)
12. [Troubleshooting](#12-troubleshooting)
13. [FAQ](#13-faq)

---

## 1. Prerequisites

Before setting up Vascora, ensure the following are installed on your machine:

| Requirement | Version | Check Command | Install Link |
|---|---|---|---|
| Docker Desktop | Latest | `docker --version` | https://www.docker.com/products/docker-desktop |
| Docker Compose | v2+ | `docker compose version` | Bundled with Docker Desktop |
| Git | Any | `git --version` | https://git-scm.com |
| Text editor | Any | — | VS Code recommended |

**Platform:** macOS or Linux recommended for this POC. Windows requires WSL2.

**Hardware minimums:**
- RAM: 8 GB (16 GB recommended — Playwright is memory-intensive)
- Disk: 10 GB free space
- CPU: 4 cores recommended (Airflow + DB + Scrapers run concurrently)

**No Python installation required on your host machine** — all Python code runs inside Docker containers.

---

## 2. Obtaining API Keys

The pipeline requires two sets of external API credentials. Both have free tiers sufficient for the POC.

---

### 2.1 Google Places API Key

Used to enrich stores with phone numbers, website URLs, and hours of operation.

**Step-by-step:**

1. Go to https://console.cloud.google.com
2. Create a new project (e.g., `vascora-poc`)
3. Navigate to **APIs & Services → Library**
4. Search for and enable:
   - **Places API (New)**
   - **Geocoding API** (for address geocoding fallback)
5. Navigate to **APIs & Services → Credentials**
6. Click **Create Credentials → API Key**
7. Copy the generated key
8. (Recommended) Click **Restrict Key**:
   - Under API restrictions, select: Places API, Geocoding API
   - Under Application restrictions, select "IP addresses" and add your server's IP

**Estimated cost for this POC:** < $5/month for Burlington-area store count (~50–80 stores, 2 requests/store/day)

**Note:** Google provides a $200/month free credit. This POC will stay well within that limit.

---

### 2.2 Sentiment Data Mode (Recommended: Devvit Relay)

If you are blocked on Reddit API key setup, use **Devvit Relay mode**.

In this mode, sentiment data is collected by a small Devvit app and pushed to Vascora through a webhook. Your local pipeline does not require `REDDIT_CLIENT_ID` or `REDDIT_CLIENT_SECRET`.

**When to use this mode:**
- You cannot create Reddit API credentials quickly
- You want to keep Reddit auth outside local infrastructure

**High-level setup:**
1. Deploy a Devvit app that reads target subreddits and emits JSON payloads
2. Configure the app to call your ingestion endpoint (for example, `POST /ingest/reddit`)
3. Set `SENTIMENT_SOURCE=devvit_webhook` in `.env`
4. Set a shared secret token in both Devvit and Vascora (`DEVVIT_WEBHOOK_TOKEN`)

**Payload fields expected by Vascora:**
- `reddit_id`
- `subreddit`
- `search_keyword`
- `post_title`
- `post_body`
- `post_score`
- `comment_count`
- `top_comments_text`
- `posted_at`

Vascora will compute VADER sentiment from the incoming text exactly as it does in API mode.

---

### 2.3 Optional Fallback: Reddit API Credentials (PRAW)

Use this only if you prefer direct API pulls from the pipeline.

**Step-by-step:**

1. Log in to Reddit at https://www.reddit.com
2. Navigate to https://www.reddit.com/prefs/apps
3. Scroll to **"Developed Applications"** and click **"Create Another App"**
4. Fill in:
   - **Name:** `vascora-sentiment-collector`
   - **App type:** Select **"script"**
   - **Description:** `Cannabis market intelligence data collection`
   - **Redirect URI:** `http://localhost:8080` (required field, not actually used for script type)
5. Click **Create App**
6. Note the values:
   - **Client ID:** shown under the app name (14-character string)
   - **Client Secret:** shown as "secret"
   - **User Agent:** create a descriptive string, e.g.: `vascora:v1.0 (by /u/YOUR_REDDIT_USERNAME)`

**Rate limit:** 60 requests/minute. The weekly sentiment DAG uses far fewer than this.

---

## 3. Environment Configuration

The entire pipeline is configured via a single `.env` file at the project root.

**Step 1: Copy the template**
```bash
cp .env.example .env
```

**Step 2: Open `.env` in your editor and fill in all values**

```dotenv
# ─── Database ─────────────────────────────────────────────
POSTGRES_USER=vascora
POSTGRES_PASSWORD=change_me_to_a_strong_password
POSTGRES_DB=vascora
POSTGRES_PORT=5432

# ─── Google Places API ────────────────────────────────────
GOOGLE_PLACES_API_KEY=AIza...your_key_here...

# ─── Sentiment Source ─────────────────────────────────────
# Choose one: devvit_webhook | praw_api | off
SENTIMENT_SOURCE=devvit_webhook

# Devvit relay mode (recommended if API keys are a blocker)
DEVVIT_WEBHOOK_TOKEN=replace_with_shared_secret

# Optional fallback: direct Reddit API mode (PRAW)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=

# ─── Airflow ──────────────────────────────────────────────
AIRFLOW_ADMIN_USERNAME=admin
AIRFLOW_ADMIN_PASSWORD=admin
AIRFLOW__CORE__FERNET_KEY=generate_this_with_command_below

# ─── Target Market ────────────────────────────────────────
BURLINGTON_LAT=43.3255
BURLINGTON_LNG=-79.7990
MARKET_RADIUS_KM=35

# ─── Pipeline Settings ────────────────────────────────────
SCRAPER_DELAY_SECONDS=3
NEW_ARRIVAL_WINDOW_DAYS=30
SENTIMENT_GAP_MIN_SCORE=0.2
SENTIMENT_GAP_MAX_STORES=2
```

**Step 3: Generate a Fernet key for Airflow**

Airflow uses a Fernet key to encrypt sensitive variables stored in its metadata DB. Generate one with:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the output as the value of `AIRFLOW__CORE__FERNET_KEY` in your `.env`.

> **Security:** Never commit `.env` to version control. The `.gitignore` is pre-configured to exclude it.

---

## 4. First-Time Setup

Run these steps once to initialise the database and Airflow.

**Step 1: Build Docker images**
```bash
docker compose build
```
This pulls base images and installs all Python dependencies. Takes 5–10 minutes on first run.

**Step 2: Start all services**
```bash
docker compose up -d
```

Services that start:
- `db` — PostgreSQL 16 + TimescaleDB
- `airflow-webserver` — Airflow UI
- `airflow-scheduler` — DAG scheduler
- `airflow-worker` — Task executor
- `dashboard` — Streamlit app

**Step 3: Run database migrations**
```bash
docker compose exec db psql -U vascora -d vascora -f /docker-entrypoint-initdb.d/init.sql
```
Or, using Alembic:
```bash
docker compose run --rm scrapers alembic upgrade head
```

**Step 4: Initialise dbt**
```bash
docker compose run --rm dbt dbt deps
docker compose run --rm dbt dbt debug
```
`dbt debug` should report all green — it confirms the database connection is working.

**Step 5: Verify services are running**

Open the following in your browser:

| Service | URL | Expected |
|---|---|---|
| Airflow UI | http://localhost:8080 | Login page (use admin/admin or your configured credentials) |
| Streamlit Dashboard | http://localhost:8501 | "No data yet" placeholder pages |

---

## 5. Running the Pipeline

### Automatic Schedule

Once Airflow is running, DAGs will execute automatically on their scheduled times (see schedule in [architecture.md](architecture.md)). The full pipeline completes by **07:00 ET daily**.

You do not need to do anything — the pipeline is self-sustaining once started.

### First Run — Trigger Manually

On first setup, no historical data exists. Trigger all DAGs manually to populate the database before the first scheduled run:

See [§ 6 — Triggering DAGs Manually](#6-triggering-dags-manually) below.

**Recommended first-run order:**
1. `dag_store_discovery` (must complete first — discovers store list)
2. `dag_product_scrape` (requires store list from step 1)
3. `dag_pricing_sync` (requires products from step 2)
4. `dag_ocs_tracker` (independent — can run any time)
5. `dag_dbt_transform` (requires steps 1–4 to be complete)
6. `dag_sentiment_ingest` (independent — can run any time, only if `SENTIMENT_SOURCE` is not `off`)

First full run takes approximately **2–3 hours** depending on the number of stores and their website response times.

---

## 6. Triggering DAGs Manually

1. Open Airflow UI at http://localhost:8080
2. Log in with your credentials
3. On the **DAGs** page, find the DAG you want to run
4. Click the **▶ (Play)** button on the right side of the DAG row
5. Click **Trigger DAG** in the confirmation modal
6. The DAG run will appear in the **Runs** column

**Monitoring a running DAG:**
1. Click the DAG name to open its detail view
2. Click on the most recent run to see the graph view
3. Each task box shows status: queued (grey) → running (yellow) → success (green) → failed (red)
4. Click any task box → **Logs** to see real-time task output

**If a task fails:**
- Red task box = failed
- Click the task → **Logs** to see the error message
- Common failures: scraper timeout, store website changed layout, API key issue
- After fixing the root cause, click the failed task → **Clear** → **Confirm** to re-run just that task

---

## 7. Using the Dashboard

The Streamlit dashboard is available at **http://localhost:8501** after pipes have data.

### Navigation

The sidebar on the left lists all five pages:
- **Store Coverage** — Map and table of all competitors
- **Product Matrix** — Cross-store product heatmap and pricing
- **Price Intelligence** — Historic pricing and volatility
- **New Arrivals** — OCS new products + local availability
- **Sentiment & Gaps** — Reddit sentiment + stocking opportunities

### Page Controls

Each page has sidebar filter controls:

| Page | Available Filters |
|---|---|
| Store Coverage | City, Distance Band (0–10km, 10–25km, 25–35km), Min Google Rating |
| Product Matrix | Category, Min Ubiquity Score, Brand |
| Price Intelligence | Store, Category, Date Range, Volatility Label |
| New Arrivals | Category, Days Since OCS Listing, Opportunity Flag only |
| Sentiment & Gaps | Keyword Type (brand/product), Min Post Count, Opportunity Flag only |

### Date Selector

At the top of each page, a **"Data as of:"** selector defaults to today. You can view historical snapshots by selecting a past date — the dashboard will show what the data looked like on that day.

---

## 8. Reading the Analytics Outputs

### Store Coverage Page

**What to look for:**
- Total number of active competitors in the 35 km radius — this is the competitive landscape size
- Clustering of stores in specific cities — identifies high-competition zones
- Stores with **low Google ratings** (< 3.5) — represents unmet consumer demand in that area
- Stores marked with **missing hours or phone** — scraper data gaps requiring manual verification

**Owner Details note:**
The "Licence Holder" column shows the legal entity registered with AGCO (corporation name or individual name). This is the maximum detail publicly available. To obtain personal contact information (email, mobile), manually search LinkedIn or the AGCO website for the licence holder entity.

---

### Product Matrix Page

**What to look for:**
- Products with **Ubiquity Score > 75%** — these are de facto market standards; MontKailash must carry them
- Products where **MontKailash is missing coverage** — gaps highlighted if MontKailash store data has been entered
- Large **price spread** (> $5 for same product) — pricing arbitrage opportunity; undercut the high-price stores
- **Dominant categories** in the category pie chart — if vapes are 40% of listings, vapes drive volume

---

### Price Intelligence Page

**What to look for:**
- **Volatile products** — products changing price 4+ times in 30 days are likely selling slowly and being discounted to move inventory
- **Promotion frequency per store** — identify which competitors are most aggressive with discounts (potential volume leaders)
- Products where MontKailash's price is **above market median** — immediate pricing adjustment opportunity
- Products where **multiple stores are running simultaneous promos** — coordinated market pressure; MontKailash should match or offer a better promotion

---

### New Arrivals Page

**What to look for:**
- Products with `opportunity_flag = true` (yellow star icon) — OCS-listed but not yet in any local store
- Sort by "Days Since OCS Listing" ascending — the newest products most likely to be stocking opportunities
- Cross-reference: click a new arrival product and check its sentiment score (link to Sentiment page)

**Stocking decision flow:**
```
Is it on OCS?
└── YES → Is sentiment positive (> 0.2)?
    ├── YES → Is it in < 3 local stores?
    │   ├── YES → ✅ HIGH PRIORITY — stock immediately
    │   └── NO  → ℹ️ MEDIUM — stock if category fits portfolio
    └── NO  → Is it in 0 local stores?
        ├── YES → 🔍 INVESTIGATE — check reviews, recency
        └── NO  → ⏳ MONITOR — wait for sentiment data
```

---

### Sentiment & Gaps Page

**What to look for:**
- Top-right quadrant of the scatter plot — **high positive sentiment + low local availability** = the best stocking opportunities
- Brands with `is_gap_opportunity = true` first in the leaderboard table
- The word cloud — specific product attributes consumers praise (e.g., "smooth", "potent", "great price", "consistent")
- Brands trending **upward** in the sentiment timeline — gaining consumer momentum
- Brands trending **downward** — consider reducing or deprioritising these lines

---

## 9. Export & Reporting

Each dashboard page has a **"⬇ Download CSV"** button in the top-right corner. This exports the current filtered view as a CSV file.

Available downloads:

| Page | Export Contents |
|---|---|
| Store Coverage | Full competitor store list (all enriched fields) |
| Product Matrix | Product × store ubiquity table |
| Price Intelligence | Current pricing for all products, all stores |
| New Arrivals | OCS new arrivals with local availability status |
| Sentiment & Gaps | Full sentiment + gap opportunity table |

**Pre-built Reports** (under the sidebar **"Reports"** link):

| Report | Description | Audience |
|---|---|---|
| **Competitor Store Directory** | All stores, enriched, sorted by distance | Management |
| **Priority Stocking List** | Ranked buy recommendations for MontKailash | Buying team |
| **Pricing Intelligence Summary** | MontKailash vs. market pricing | Store manager |

Reports regenerate daily at 07:00 ET and are available as both CSV and PDF.

---

## 10. Burlington 35 km Coverage Map

The pipeline's 35 km radius from Burlington city centre (43.3255° N, 79.7990° W) captures stores in:

| City / Area | Approx. Distance from Burlington | Direction |
|---|---|---|
| Burlington (core) | 0–5 km | Centre |
| Waterdown | ~15 km | North |
| Hamilton (downtown) | ~18 km | East |
| Ancaster | ~20 km | East |
| Dundas | ~22 km | East |
| Stoney Creek | ~24 km | East |
| Oakville | ~20 km | West |
| Milton | ~27 km | North-West |
| Grimsby | ~34 km | East |
| Mississauga (south) | ~32 km | West |

Cities that fall **outside** the radius (not included):
- Toronto proper (~50 km)
- Brampton (~40 km)
- Guelph (~40 km)
- Niagara Falls (~90 km)

---

## 11. Extending the Pipeline

### Adding a New Store Manually

If a store is known to exist but isn't being picked up by the AGCO scraper (e.g., newly licensed, data lag):

1. Navigate to Airflow UI → Admin → Variables
2. Add a variable: key = `manual_stores`, value = JSON array of `{licence_number, store_name, street_address, city, postal_code}`
3. The `dag_store_discovery` DAG checks this variable and merges manually added stores with AGCO data

### Adding a New Scraper Adapter

When a store uses a POS platform not yet supported:

1. Create a new adapter file at `scrapers/store_menus/adapters/new_platform_adapter.py`
2. The adapter must implement the `BaseMenuAdapter` interface:
   ```python
   class NewPlatformAdapter(BaseMenuAdapter):
       def extract_products(self, store_url: str) -> list[dict]: ...
   ```
3. Register the adapter in `scrapers/store_menus/adapter_registry.py` with its detection pattern
4. Write a unit test in `tests/test_adapters/test_new_platform.py`

### Adding New Sentiment Sources / Subreddits

If using **Devvit Relay mode**:
1. Update subreddit targets in your Devvit app configuration
2. Confirm the webhook payload still matches Vascora's expected schema
3. Trigger `dag_sentiment_ingest`

If using **PRAW API mode**:
1. Open `scrapers/reddit/reddit_collector.py`
2. Add the subreddit name to the `SUBREDDITS` list
3. Trigger `dag_sentiment_ingest`

### Adding New dbt Analytics Models

1. Create a new SQL file in `dbt/models/marts/`
2. Add a `ref()` dependency on the appropriate staging or intermediate model
3. Run `docker compose run --rm dbt dbt run --select new_model_name`
4. Add a dbt test in `dbt/tests/`
5. Add the new mart table to the Streamlit dashboard as a new page or additional metric

### Changing the Target Market Radius

Update `MARKET_RADIUS_KM` in `.env`:
```dotenv
MARKET_RADIUS_KM=50  # increase to 50 km
```
Then re-run `dag_store_discovery` to re-geocode and re-filter the store list.

---

## 12. Troubleshooting

### Issue: `docker compose up` fails with "port already in use"

**Cause:** Another service is using port 5432 (PostgreSQL) or 8080 (Airflow).
**Fix:** Stop the conflicting service, or change the port in `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"  # Use 5433 on host instead
```
Then update the connection string in `.env` to match.

---

### Issue: Airflow DAG shows "Import Error"

**Cause:** Python syntax error or missing import in a DAG file.
**Fix:**
1. Airflow UI → DAGs → click the red error icon next to the DAG name
2. Read the import error message
3. Fix the Python error in `airflow/dags/dag_xxx.py`
4. Airflow auto-reloads DAGs every 30 seconds — no restart needed

---

### Issue: A scraper returns zero products

**Cause:** The store website changed its layout, or the POS platform updated.
**Symptoms:** Airflow task succeeds (no error) but no new rows in `raw.store_products`.
**Fix:**
1. Manually visit the store's website and inspect the product menu
2. Check if the POS embed platform has changed (Dutchie → Jane, etc.)
3. Update the relevant adapter CSS selectors or detection logic
4. Re-run the `dag_product_scrape` DAG

---

### Issue: Google Places API returns "REQUEST_DENIED"

**Cause:** API key not activated, or the Places API not enabled in the GCP project.
**Fix:**
1. Go to https://console.cloud.google.com → APIs & Services → Library
2. Confirm "Places API (New)" shows as **Enabled**
3. Check API key restrictions — ensure the key allows Places API calls
4. Confirm `GOOGLE_PLACES_API_KEY` in `.env` matches the GCP Console key exactly

---

### Issue: Sentiment ingestion has no new records

**Cause:** `SENTIMENT_SOURCE` mode mismatch or upstream source not sending data.
**Fix:**
1. Confirm `.env` has the intended source mode (`devvit_webhook`, `praw_api`, or `off`)
2. If using Devvit, validate webhook endpoint reachability and token match (`DEVVIT_WEBHOOK_TOKEN`)
3. If using PRAW, verify `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and `REDDIT_USER_AGENT`
4. Re-run `dag_sentiment_ingest`

---

### Issue: dbt run fails with "Database Error: relation does not exist"

**Cause:** The raw schema tables haven't been created yet, or a migration is missing.
**Fix:**
```bash
docker compose run --rm scrapers alembic upgrade head
docker compose run --rm dbt dbt debug
docker compose run --rm dbt dbt run
```

---

### Issue: Dashboard shows "No data" on all pages

**Cause:** dbt models haven't been run yet, so `marts.*` tables are empty.
**Fix:**
1. Confirm at least `dag_store_discovery` and `dag_product_scrape` have completed successfully
2. Manually trigger `dag_dbt_transform` in Airflow
3. Refresh the dashboard (Streamlit caches for 5 minutes by default — press **R** to hard refresh)

---

### Issue: Store website blocked by bot protection (HTTP 403 or CAPTCHA)

**Cause:** Some cannabis store websites (particularly Dutchie-powered) use Cloudflare bot protection.
**Fix (short term):** Increase scraper delay for that domain — add a `CUSTOM_DELAYS` entry in the scraper config:
```python
CUSTOM_DELAYS = {
    "example-store.com": 10  # 10-second delay
}
```
**Fix (longer term):** Use a residential proxy rotation service. This is out of scope for the POC but can be integrated via Scrapy's `HttpProxyMiddleware`.

---

## 13. FAQ

**Q: How often does the data refresh?**
A: Store and product data refreshes daily. Pricing refreshes daily. Sentiment refreshes weekly by default (or near-real-time if using Devvit webhook pushes). The full daily pipeline completes by 07:00 ET each morning.

**Q: Can I use this for a market other than Burlington?**
A: Yes. Change `BURLINGTON_LAT`, `BURLINGTON_LNG`, and `MARKET_RADIUS_KM` in `.env`, then re-run `dag_store_discovery`. All downstream data will update for the new market.

**Q: How accurate is the sentiment analysis?**
A: The VADER model is designed for social media text and performs well for general positive/negative classification. It is not fine-tuned on cannabis-specific vocabulary. For the POC, this is sufficient for identifying directional signals. Production-grade use would benefit from fine-tuning or GPT-4o summarisation.

**Q: Why are some stores missing phone numbers or hours?**
A: Google Places doesn't have complete data for every business. If a store hasn't been claimed on Google Business Profile, phone and hours may be absent. In those cases, the fields will show "Not available" with a flag for manual verification.

**Q: Does the platform collect any customer personal data?**
A: No. All data collected is publicly available retail information (store details, product menus, prices) or aggregated public commentary (Reddit). No customer PII is processed or stored.

**Q: How do I stop all services?**
```bash
docker compose down
```
To stop and also remove all data volumes (full reset):
```bash
docker compose down -v
```
> ⚠️ The `-v` flag deletes all database data. Only use this if you want a complete fresh start.

**Q: How do I update the pipeline code without losing data?**
```bash
git pull origin main
docker compose build
docker compose up -d
```
Database data persists in the Docker volume across rebuilds.
