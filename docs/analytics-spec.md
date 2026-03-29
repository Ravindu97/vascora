# Analytics Specification

> **Document:** docs/analytics-spec.md
> **Project:** Vascora — MontKailash Cannabis Market Intelligence
> **Last Updated:** March 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Analytics Module 1 — Store Coverage Map](#2-analytics-module-1--store-coverage-map)
3. [Analytics Module 2 — Cross-Store Product Matrix](#3-analytics-module-2--cross-store-product-matrix)
4. [Analytics Module 3 — Price Intelligence & Volatility](#4-analytics-module-3--price-intelligence--volatility)
5. [Analytics Module 4 — OCS New Arrivals Tracker](#5-analytics-module-4--ocs-new-arrivals-tracker)
6. [Analytics Module 5 — Sentiment & Gap Analysis](#6-analytics-module-5--sentiment--gap-analysis)
7. [KPI Summary Dashboard](#7-kpi-summary-dashboard)
8. [Actionable Report Outputs](#8-actionable-report-outputs)
9. [Business Logic Reference](#9-business-logic-reference)

---

## 1. Overview

The Vascora analytics layer produces **five distinct analytical modules**, each answering a specific competitive intelligence question for MontKailash Cannabis:

| Module | Business Question | Dashboard Page |
|---|---|---|
| 1. Store Coverage Map | Who are our competitors and where are they? | Store Coverage |
| 2. Product Matrix | What products dominate the market? | Product Matrix |
| 3. Price Intelligence | How is pricing moving and who is discounting? | Price Intelligence |
| 4. New Arrivals Tracker | What new products should we be stocking? | New Arrivals |
| 5. Sentiment & Gap Analysis | What do consumers love that isn't widely available? | Sentiment & Gaps |

Each module is powered by a corresponding dbt mart model and rendered as an interactive Streamlit dashboard page.

---

## 2. Analytics Module 1 — Store Coverage Map

### Business Question
*"How many cannabis retail stores operate within 35 km of Burlington, and who are they?"*

### Data Source
`marts.mart_store_coverage`

### Key Metrics

| Metric | Definition |
|---|---|
| **Total Competitors** | COUNT of active stores within 35 km |
| **Stores Per City** | Breakdown by municipality |
| **Average Distance from Burlington** | Mean distance_km of all stores |
| **Coverage Density** | Stores per 10 km radius band |

### Visualisations

1. **Interactive Folium Map**
   - Burlington city centre marked with a distinct pin
   - 35 km radius circle overlay
   - Each competitor store plotted with a pin
   - Clicking a pin shows: store name, address, phone, hours, Google rating, product count
   - Colour-coded by distance band: 0–10 km (red), 10–25 km (orange), 25–35 km (green)

2. **Competitor Table**
   - Sortable columns: Store Name | City | Distance (km) | Phone | Hours | Products Listed | Google Rating
   - Filterable by city and distance band

3. **Bar Chart — Stores by City**

### Output Data Table: Store List

This module produces the primary deliverable store list for the exercise, including all required fields:

| Delivered Field | Source |
|---|---|
| Store name | AGCO + Google Places |
| Full address | AGCO |
| Phone number | Google Places |
| Hours of operation | Google Places |
| Licence holder (owner entity) | AGCO |
| Website URL | Google Places |
| Distance from Burlington | Calculated (Haversine) |
| Google Rating | Google Places |

> **Note on Owner Personal Details:** AGCO provides the licence holder entity name (corporation or individual). Personal contact details (email, mobile) are not publicly available and require manual outreach. This is flagged as a manual enrichment step in the User Guide.

---

## 3. Analytics Module 2 — Cross-Store Product Matrix

### Business Question
*"Which products are carried across all or most stores? What is the market's baseline product set?"*

### Data Source
`marts.mart_product_matrix`

### Key Metrics

| Metric | Definition |
|---|---|
| **Ubiquity Score** | `(store_count / total_active_stores) × 100` — percentage of market carrying the product |
| **Market Standard Products** | Products with Ubiquity Score ≥ 50% |
| **Category Distribution** | Share of each product category (flower/vape/edible etc.) across all stores |
| **Price Spread** | `max_regular_price - min_regular_price` across stores for same product |
| **Price Arbitrage Opportunities** | Products where price_spread_cad > $5 — buying/positioning signal |

### Visualisations

1. **Heatmap — Product × Store Matrix**
   - Rows: top 50 products by ubiquity score
   - Columns: each store
   - Cell colour: green = carries product, grey = does not carry
   - Tooltip shows current price at that store

2. **Bar Chart — Top 20 Most Widely Carried Products**
   - Sorted by ubiquity score descending
   - Colour-coded by category

3. **Pie Chart — Category Share Across Market**
   - Proportion of total product listings by category

4. **Price Comparison Table**
   - For top 30 products by ubiquity: regular price at each store side-by-side
   - Highlights min and max price cells

### Insight Logic

**Market Standard Products** (ubiquity ≥ 50%):
- These products represent the floor of any competitive store's offering
- MontKailash **must** carry these to not appear under-stocked
- If MontKailash is missing any, flag as **critical stocking gap**

**Price Arbitrage Signal:**
- Products with large price spreads across stores indicate consumers will price-shop
- MontKailash should price these products at or below the market median

---

## 4. Analytics Module 3 — Price Intelligence & Volatility

### Business Question
*"How often do products change in price? Who is running promotions and for how long?"*

### Data Source
`marts.mart_price_volatility` + `staging.stg_pricing` (for time-series charts)

### Key Metrics

| Metric | Definition |
|---|---|
| **Price Change Count (30d)** | Count of distinct regular price values in last 30 days per product per store |
| **Volatility Label** | `stable` / `moderate` / `volatile` (see Data Dictionary) |
| **Promotion Frequency** | % of days in the last 30 where a product had an active sale price |
| **Average Discount Depth** | `(regular_price - sale_price) / regular_price × 100` when on sale |
| **Promotion Duration** | Average days a promotion runs when one is active |
| **Market Price Index** | Average effective price across all stores for each product |

### Visualisations

1. **Price History Line Chart (per product)**
   - Time-series of effective price per day
   - Overlays from multiple stores on same chart
   - Sale periods highlighted in a different colour band

2. **Volatility Heatmap**
   - Rows: products, Columns: stores
   - Cell colour: green (stable), yellow (moderate), red (volatile)

3. **Promotion Calendar View**
   - Timeline showing which stores had active promotions on which dates
   - Useful for spotting patterns (e.g., Friday promotions, month-end discounts)

4. **Price Distribution Histogram**
   - Per category: distribution of current market prices
   - Useful for MontKailash to determine optimal price positioning

### Insight Logic

**Volatility Signal:**
- Highly volatile pricing on a product may indicate: oversupply, expiry management, or competitive pressure
- MontKailash should avoid stocking products that consistently require discounting to sell

**Promotion Timing Pattern:**
- If multiple competitors run promos the first week of the month, MontKailash can either match or counter-schedule mid-month promos to capture price-sensitive customers at a different time

---

## 5. Analytics Module 4 — OCS New Arrivals Tracker

### Business Question
*"Which new and upcoming products are appearing on OCS? Are competitors stocking them yet?"*

### Data Source
`marts.mart_new_arrivals`

### Key Metrics

| Metric | Definition |
|---|---|
| **New OCS Listings (30d)** | Products first seen on OCS within the last 30 days |
| **Local Availability Rate** | % of new OCS products already in Burlington-area stores |
| **First-Mover Opportunities** | New OCS products with `local_store_count = 0` |
| **Time to Local Shelf** | Average days from OCS listing to appearing in a local store |

### Visualisations

1. **New Arrivals Table**
   - Columns: Product Name | Brand | Category | OCS Price | Days Since OCS Listing | # Local Stores Carrying | Opportunity Flag
   - Filterable by category, days since listing, opportunity flag
   - Sorted by opportunity flag (flagged first), then days since listing ascending

2. **Timeline Scatter Plot**
   - X-axis: days since OCS listing
   - Y-axis: number of local stores carrying
   - Products with high days-since-listing but low local count = slow adoption (market gap)

3. **Category Breakdown of New Arrivals**
   - Bar chart showing which categories are growing on OCS

### Insight Logic

**First-Mover Opportunity:**
- Products with `opportunity_flag = true` (on OCS, not yet in any local store) represent a window for MontKailash to be first to shelf
- Cross-reference with the Sentiment module: if a new OCS product also has positive Reddit mentions, treat it as **Priority 1 stocking recommendation**

**Slow Adoption Products:**
- If a product has been on OCS > 14 days but `local_store_count = 0`, this is either a market rejection signal or a stocking oversight
- Check Reddit sentiment for context: negative sentiment = skip; positive = likely stocking oversight = opportunity

---

## 6. Analytics Module 5 — Sentiment & Gap Analysis

### Business Question
*"What do cannabis consumers publicly love or hate? Which positively-rated products are NOT widely available locally?"*

### Data Source
`marts.mart_sentiment_gap`

### Key Metrics

| Metric | Definition |
|---|---|
| **Opportunity Score** | `avg_sentiment_score × (1 / (local_store_count + 1))` — higher = more positive with less local availability |
| **Gap Opportunities** | Brands/products with `avg_sentiment ≥ 0.2` AND `local_store_count ≤ 2` |
| **Most Discussed Brands** | Brands with highest total Reddit post count |
| **Most Positive Brands** | Brands with highest average VADER compound score |
| **Most Negative Brands** | Brands with lowest average VADER compound score |
| **Sentiment Trend** | Change in avg sentiment score week-over-week for monitored keywords |

### Visualisations

1. **Sentiment vs. Availability Scatter Plot**
   - X-axis: `avg_sentiment_score` (−1 to +1)
   - Y-axis: `local_store_count` (inverted — lower is better opportunity = higher on chart)
   - Bubble size: `total_reddit_score` (engagement/reach)
   - Colour: green = gap opportunity, grey = already widely available
   - This chart is the primary actionable output of the platform

2. **Brand Sentiment Leaderboard**
   - Ranked table: Brand | Avg Sentiment | Total Posts | Post Reach | Local Stores | Opportunity Score
   - Sorted by Opportunity Score descending

3. **Word Cloud**
   - Generated from positive-sentiment post text for gap-opportunity products
   - Highlights what consumers are specifically praising

4. **Sentiment Timeline (weekly)**
   - Line chart per monitored brand showing sentiment score trend over time
   - Identifies brands gaining or losing consumer approval

### Insight Logic

**Gap Opportunity Definition:**
A brand or product qualifies as a Gap Opportunity when:
- `avg_sentiment_score ≥ 0.2` (net positive consumer perception)
- `local_store_count ≤ 2` (low local availability)
- `total_posts ≥ 5` (sufficient data to trust the signal)

**Interpretation:**
- These items are talked about positively online but are hard to find locally
- Stocking them gives MontKailash a differentiated competitive advantage
- Consumers already want them — no demand education required

**Negative Sentiment Alert:**
- Products with `avg_sentiment ≤ −0.2` should be flagged for de-prioritisation even if widely carried by competitors
- High negative sentiment = risk of returns, complaints, brand association damage

---

## 7. KPI Summary Dashboard

The Streamlit app homepage (before any page navigation) shows a KPI banner updated daily:

| KPI | Definition | Target (POC) |
|---|---|---|
| Total Competitors Tracked | Active stores within 35 km | — |
| Total Products Catalogued | Distinct product_keys across all stores | — |
| Products Updated Today | Records with `last_scraped_at = today` | ≥ 90% of known products |
| New OCS Arrivals (30d) | `mart_new_arrivals` row count | — |
| Gap Opportunities Identified | `mart_sentiment_gap` where `is_gap_opportunity = true` | — |
| Pipeline Last Run | Airflow `dag_dbt_transform` last success time | < 7am ET daily |
| Data Freshness | Hours since last successful scrape | < 24 hours |

---

## 8. Actionable Report Outputs

Beyond the interactive dashboard, the pipeline produces three exportable reports (CSV/PDF via Streamlit download buttons):

### Report A — Competitor Store Directory
**Audience:** MontKailash management, sales team
**Contents:** Full enriched store list — name, address, phone, hours, owner entity, distance, Google rating
**Refresh:** Daily

### Report B — Priority Stocking List
**Audience:** Buying / procurement team
**Contents:** Union of:
1. Market Standard Products not currently carried by MontKailash
2. New OCS arrivals with `opportunity_flag = true` AND positive sentiment
3. Gap Opportunity products from the sentiment module
**Ranked by:** Opportunity Score descending
**Refresh:** Weekly

### Report C — Pricing Intelligence Summary
**Audience:** Store manager, pricing team
**Contents:** Current effective price for every locally-available product, with market min/max and MontKailash's position relative to market median
**Refresh:** Daily

---

## 9. Business Logic Reference

### Opportunity Score Formula

```
opportunity_score = avg_sentiment_score × (1 / (local_store_count + 1))
```

**Why this formula:**
- A product with `avg_sentiment = 0.8` and `local_store_count = 0` scores: `0.8 × (1/1) = 0.80`
- Same product with `local_store_count = 7` scores: `0.8 × (1/8) = 0.10`
- The score naturally decays as local availability increases, prioritising genuine gaps

### Ubiquity Score Formula

```
ubiquity_score = (store_count / total_active_stores) × 100
```

Where `total_active_stores` is the current count of scraped active stores within 35 km.

### Volatility Label Thresholds

These are configurable via dbt `vars` in `dbt_project.yml`:

```yaml
vars:
  volatility_stable_max_changes: 1
  volatility_moderate_max_changes: 3
  sentiment_gap_min_score: 0.2
  sentiment_gap_max_stores: 2
  new_arrival_window_days: 30
```

### Price Change Detection

A price change is recorded when the `regular_price_cad` value in `raw.product_pricing` differs from the immediately preceding row for the same `(store_product_id)` ordered by `scraped_at`. Sale price changes are tracked separately and do not count toward the volatility index (since promos are intentional, temporary, and expected).
