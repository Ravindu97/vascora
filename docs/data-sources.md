# Data Sources Reference

> **Document:** docs/data-sources.md
> **Project:** Vascora — MontKailash Cannabis Market Intelligence
> **Last Updated:** March 2026

---

## Table of Contents

1. [Source Overview](#1-source-overview)
2. [AGCO Retailer Registry](#2-agco-retailer-registry)
3. [Google Places API](#3-google-places-api)
4. [Cannabis Store Websites](#4-cannabis-store-websites)
5. [Ontario Cannabis Store (OCS)](#5-ontario-cannabis-store-ocs)
6. [HiBuddy.ca](#6-hibuddyca)
7. [Weedmaps](#7-weedmaps)
8. [Reddit](#8-reddit)
9. [GeoPy / Nominatim (Geocoding)](#9-geopy--nominatim-geocoding)
10. [Source Reliability & Fallback Strategy](#10-source-reliability--fallback-strategy)

---

## 1. Source Overview

| # | Source | Primary Purpose | Access Type | Cost | Update Frequency |
|---|---|---|---|---|---|
| 1 | AGCO Retailer Registry | Authoritative licensed store list | Public web / CSV | Free | As-needed (AGCO updates monthly) |
| 2 | Google Places API | Store hours, phone, ratings, website URL | REST API | Paid (~$0.017/request) | Daily |
| 3 | Store Websites | Live product menus + pricing | Web scraping | Free | Daily |
| 4 | Ontario Cannabis Store (OCS) | Full Ontario product catalog, new arrivals | Web scraping | Free | Daily |
| 5 | HiBuddy.ca | Comparative pricing platform | Web scraping | Free | Daily |
| 6 | Weedmaps | Supplemental menus + reviews | Web scraping | Free | Daily |
| 7 | Reddit | Public product/brand sentiment | Devvit Webhook (preferred) / PRAW API (fallback) | Free | Weekly or near-real-time |
| 8 | GeoPy / Nominatim | Address geocoding + distance filter | OSM API | Free | On-demand |

---

## 2. AGCO Retailer Registry

**What it provides:** The only government-authoritative list of all cannabis retail licences issued in Ontario. This is the ground-truth source for store existence validation.

**URL:** https://www.agco.ca/cannabis/cannabis-retail-store-licences

**Access method:**
- The AGCO publishes a publicly downloadable dataset or a searchable web directory
- Primary method: download the published CSV/Excel file if available; fallback to HTML scraping
- Scraper: `scrapers/agco/agco_spider.py`

**Fields available from AGCO:**
| Field | Notes |
|---|---|
| Licence Number | Unique identifier per store |
| Store Name / Trading Name | Legal operating name |
| Street Address | Full civic address |
| City / Municipality | |
| Postal Code | |
| Licence Holder Name | Entity (corporation or individual) registered as licence holder |
| Licence Status | Active / Suspended / Revoked |
| Licence Issue Date | |

**Important limitations:**
- AGCO does **not** provide: phone number, website URL, hours of operation, or individual owner contact details
- Owner contact enrichment requires manual outreach or LinkedIn research — **flag as manual step**
- The CSV is updated monthly by AGCO; daily scraping may not reflect same-day changes

**Filtering applied:**
- Licence type: `Cannabis Retail Store`
- Status: `Active` only
- Geocoded address within 35 km of Burlington (43.3255° N, 79.7990° W)

---

## 3. Google Places API

**What it provides:** Operational enrichment for each store discovered via AGCO — phone number, website, hours, Google rating, and maps URL.

**API:** Google Maps Places API (New) — Place Search + Place Details endpoints

**Requests per store:**
1. `Text Search` — finds the Place ID by store name + address (~1 request)
2. `Place Details` — retrieves phone, website, opening_hours, rating (~1 request)

**Estimated cost for POC:**
- ~50–80 stores × 2 requests = ~100–160 requests/day
- At $0.017/request = approximately **$1.70–$2.72/day** — well within free tier on initial quota

**Fields collected:**
| Field | API Key |
|---|---|
| Phone number | `formatted_phone_number` |
| Website URL | `website` |
| Hours of operation | `opening_hours.weekday_text` |
| Google Rating | `rating` |
| Review count | `user_ratings_total` |
| Maps URL | `url` |

**Configuration:** `GOOGLE_PLACES_API_KEY` in `.env`

**Rate limits:** 1,000 requests/minute (standard tier)

---

## 4. Cannabis Store Websites

**What it provides:** Live product menus including product names, brands, categories, THC/CBD content, weights, regular prices, sale prices, and promotional labels.

**Access method:** Web scraping via Scrapy + Playwright (required for JS-rendered menus)

**POS Platform Detection:**
Most cannabis stores in Ontario embed their product menus through a third-party POS platform. The scraper detects cues in the store's page HTML:

| POS Platform | Detection Signal | Estimated Market Share in Ontario |
|---|---|---|
| Dutchie | `<iframe src="*dutchie.com*">` or `dutchie` in JS bundles | ~45% |
| Jane Technologies | `<iframe src="*iheartjane.com*">` | ~25% |
| Cova POS | `cova` in meta tags or direct HTML menu | ~20% |
| Custom / Other | None of the above | ~10% |

**Adapter pattern:**
Each POS platform has a dedicated adapter in `scrapers/store_menus/adapters/`:

```
dutchie_adapter.py    — Playwright headless browser, extracts JSON payload from Dutchie embed
jane_adapter.py       — Jane embed API endpoint, returns product JSON directly
cova_adapter.py       — Scrapy CSS selectors on Cova-generated HTML
```

**Rate limiting:** Minimum 3-second delay between requests per domain. Scrapy `AUTOTHROTTLE` enabled.

**Fields scraped per product:**
| Field | Notes |
|---|---|
| Product name | As listed on menu |
| Brand name | |
| Category | Normalised to: flower / pre-roll / vape / edible / concentrate / tincture / topical |
| THC % (min/max) | Some stores list a range |
| CBD % (min/max) | |
| Weight (g or count) | |
| SKU / Product ID | POS-platform internal ID |
| Regular price (CAD) | |
| Sale price (CAD) | Null if no active promotion |
| Promo label | Text of promotion (e.g., "Weekend Deal") |
| Promo start/end date | Where visible on the page |
| In-stock status | Boolean |

---

## 5. Ontario Cannabis Store (OCS)

**What it provides:** The complete Ontario cannabis product catalog — including products that may not yet have local retail distribution. This is the authoritative source for tracking new product arrivals to the Ontario market.

**URL:** https://ocs.ca/collections/all-products

**Access method:** Scrapy spider with pagination support. OCS uses server-side rendered product pages with URL-based pagination.

**Fields collected:**
| Field | Notes |
|---|---|
| OCS SKU | Unique product identifier |
| Product name | |
| Brand name | |
| Category | |
| THC % / CBD % | |
| Listed date | Inferred from OCS "New" badge or sitemap `lastmod` |
| Available in Ontario | Boolean — some products are province-limited |
| OCS price | MSRP baseline |

**Key use case:** The `mart_new_arrivals` dbt model cross-references OCS products listed in the last 30 days against local store menus. Products appearing on OCS but not yet in local stores = **market entry opportunities** for MontKailash.

**Rate limiting:** 5-second delay between OCS requests. OCS has CDN-level rate limiting.

---

## 6. HiBuddy.ca

**What it provides:** A cannabis price-comparison platform that aggregates product menus from Ontario stores. Useful as a cross-validation source against directly scraped store data.

**URL:** https://hibuddy.ca

**Access method:** Scrapy + Playwright (JS-rendered product listings)

**Use in pipeline:**
- Secondary validation of product prices collected from store websites
- Identifies discrepancies that may indicate our store scraper missed a price update
- Provides a "market average price" reference per product SKU

**Fields collected:**
| Field | Notes |
|---|---|
| Store name | |
| Product name | |
| Brand | |
| HiBuddy listed price | |
| Last updated timestamp | |

**Important note:** HiBuddy data may lag store website data by 24–48 hours. It is a **validation source**, not the primary price source.

---

## 7. Weedmaps

**What it provides:** Supplemental store listings, product menus, and customer reviews for Ontario cannabis retailers.

**URL:** https://weedmaps.com/dispensaries/canada/ontario

**Access method:** Scrapy + Playwright. Weedmaps uses client-side rendering.

**Use in pipeline:**
- Supplemental product and pricing data for stores whose own website menus are difficult to scrape
- Customer review text (supplemental to Reddit sentiment)

**Fields collected:**
| Field | Notes |
|---|---|
| Store listing URL | |
| Product name + brand | |
| Weedmaps price | |
| Customer review text | For sentiment supplementation |
| Review star rating | |

**Important note:** Weedmaps ToS should be reviewed before production deployment. This source is classified as **supplemental/optional** in the POC.

---

## 8. Reddit

**What it provides:** Unfiltered public consumer commentary about specific cannabis products, brands, and stores - the closest available proxy for real consumer sentiment.

Vascora supports two ingestion modes.

### Mode A (Preferred): Devvit Webhook Relay

**Access:** A Devvit app collects posts/comments from target subreddits and pushes payloads to Vascora via webhook.

**Credentials required in Vascora:**
- `SENTIMENT_SOURCE=devvit_webhook`
- `DEVVIT_WEBHOOK_TOKEN`

**Benefits:**
- No local Reddit API key setup in the data pipeline
- Cleaner auth separation between ingestion app and analytics stack
- Can run near-real-time push instead of only scheduled pull

### Mode B (Fallback): PRAW API Pull

**Access:** Official **PRAW (Python Reddit API Wrapper)** library using Reddit's public data API.

**API credentials required:**
- Reddit application (Script type) created at https://www.reddit.com/prefs/apps
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` in `.env`

**Rate limits:** 60 requests/minute on free tier. More than sufficient for weekly batch processing.

**Subreddits monitored:**

| Subreddit | Rationale |
|---|---|
| r/TheOCS | Ontario-specific OCS product discussions |
| r/canadients | Largest Canadian cannabis community |
| r/OnCannabis | Ontario cannabis focused |
| r/weed | General; filtered to Canadian context via flair/keywords |

**Search query strategy:**
- Search by brand name (e.g., "Redecan", "FIGR", "Pure Sunfarms")
- Search by product category keywords (e.g., "THC vape Ontario", "edibles OCS")
- Search by specific product names when available

**Fields collected:**
| Field | Notes |
|---|---|
| Post ID | Reddit unique identifier |
| Subreddit | |
| Search keyword used | For attribution |
| Post title | |
| Post body text | |
| Post score (upvotes) | Relevance signal |
| Comment count | Engagement signal |
| Top 5 comments text | Collected via separate API call |
| Post creation timestamp | |
| VADER compound score | Added at collection time (−1 to +1) |
| Sentiment label | Positive / Neutral / Negative |

---

## 9. GeoPy / Nominatim (Geocoding)

**What it provides:** Converts store street addresses to latitude/longitude coordinates, enabling distance calculations from the Burlington centroid.

**Library:** `geopy` 2.4 with `Nominatim` geocoder (OpenStreetMap)

**Burlington centroid:** 43.3255° N, 79.7990° W

**Distance formula:** Haversine (great-circle distance)

**Fallback:** If Nominatim fails to geocode an address (unusual formatting), the scraper falls back to Google Geocoding API using the same `GOOGLE_PLACES_API_KEY`.

**Rate limits:** Nominatim enforces 1 request/second. The store discovery DAG runs this step only once per new store (results cached in `raw.agco_stores`).

---

## 10. Source Reliability & Fallback Strategy

| Source | Reliability Risk | Fallback |
|---|---|---|
| AGCO Registry | Low — government source, stable | Cache last known good CSV in S3/local |
| Google Places API | Low — commercial SLA | Log failures, retry with exponential backoff |
| Store Websites | **High** — sites change layout, add bot protection | Per-store error alerting; manual review queue |
| OCS | Medium — occasional layout changes | Versioned CSS selectors; alerting on zero-result scrapes |
| HiBuddy | Medium — JS-heavy, may add bot protection | Mark as optional; degrade gracefully |
| Weedmaps | Medium | Mark as optional; degrade gracefully |
| Reddit (Devvit / PRAW) | Low to Medium - depends on webhook availability or API credentials | Retry webhook delivery; fallback to PRAW mode |
| Nominatim | Low | Google Geocoding API fallback |

**General scraper failure policy:**
- On HTTP 4xx/5xx: log error, mark store as `scrape_failed`, skip to next store
- On zero-product result (likely scraper breakage): alert via Airflow email notification, do **not** delete previous day's data
- All failures visible in Airflow DAG run logs and the Streamlit monitoring page
