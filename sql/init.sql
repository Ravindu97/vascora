CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.agco_stores (
    id SERIAL PRIMARY KEY,
    licence_number VARCHAR(50) NOT NULL UNIQUE,
    store_name VARCHAR(255) NOT NULL,
    licence_holder_name VARCHAR(255) NULL,
    street_address VARCHAR(500) NOT NULL,
    city VARCHAR(100) NOT NULL,
    province VARCHAR(50) NOT NULL DEFAULT 'ON',
    postal_code VARCHAR(10) NULL,
    phone_number VARCHAR(50) NULL,
    website_url TEXT NULL,
    latitude NUMERIC(10, 7) NULL,
    longitude NUMERIC(10, 7) NULL,
    distance_km NUMERIC(8, 3) NULL,
    within_35km BOOLEAN NOT NULL DEFAULT false,
    hours_of_operation JSONB NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    scraped_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agco_stores_city ON raw.agco_stores (city);
CREATE INDEX IF NOT EXISTS idx_agco_stores_within_35km ON raw.agco_stores (within_35km);

CREATE TABLE IF NOT EXISTS raw.ocs_catalog (
    id SERIAL PRIMARY KEY,
    ocs_sku VARCHAR(100) NOT NULL UNIQUE,
    product_name VARCHAR(500) NOT NULL,
    brand_name VARCHAR(255) NULL,
    category_raw VARCHAR(100) NULL,
    thc_pct_min NUMERIC(5, 2) NULL,
    thc_pct_max NUMERIC(5, 2) NULL,
    cbd_pct_min NUMERIC(5, 2) NULL,
    cbd_pct_max NUMERIC(5, 2) NULL,
    weight_grams NUMERIC(8, 3) NULL,
    ocs_price_cad NUMERIC(8, 2) NULL,
    first_seen_at DATE NOT NULL,
    last_seen_at DATE NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ocs_catalog_brand ON raw.ocs_catalog (brand_name);
CREATE INDEX IF NOT EXISTS idx_ocs_catalog_last_seen_at ON raw.ocs_catalog (last_seen_at DESC);

CREATE TABLE IF NOT EXISTS raw.store_products (
    id BIGSERIAL PRIMARY KEY,
    licence_number VARCHAR(50) NOT NULL,
    pos_platform VARCHAR(50) NULL,
    pos_sku VARCHAR(255) NULL,
    product_name VARCHAR(500) NOT NULL,
    brand_name VARCHAR(255) NULL,
    category_raw VARCHAR(100) NULL,
    thc_pct_min NUMERIC(5, 2) NULL,
    thc_pct_max NUMERIC(5, 2) NULL,
    cbd_pct_min NUMERIC(5, 2) NULL,
    cbd_pct_max NUMERIC(5, 2) NULL,
    weight_grams NUMERIC(8, 3) NULL,
    unit_count INTEGER NULL,
    ocs_sku VARCHAR(100) NULL,
    in_stock BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    scraped_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_store_products_identity UNIQUE (licence_number, pos_sku, product_name)
);

CREATE INDEX IF NOT EXISTS idx_store_products_licence_number ON raw.store_products (licence_number);
CREATE INDEX IF NOT EXISTS idx_store_products_brand_name ON raw.store_products (brand_name);

CREATE TABLE IF NOT EXISTS raw.product_pricing (
    id BIGSERIAL PRIMARY KEY,
    licence_number VARCHAR(50) NOT NULL,
    pos_sku VARCHAR(255) NULL,
    product_name VARCHAR(500) NOT NULL,
    brand_name VARCHAR(255) NULL,
    regular_price_cad NUMERIC(8, 2) NOT NULL,
    sale_price_cad NUMERIC(8, 2) NULL,
    promo_label VARCHAR(255) NULL,
    promo_start_date DATE NULL,
    promo_end_date DATE NULL,
    in_stock BOOLEAN NOT NULL DEFAULT true,
    scraped_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_pricing_licence_sku_scraped_at
    ON raw.product_pricing (licence_number, pos_sku, scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_product_pricing_product_name ON raw.product_pricing (product_name);

CREATE TABLE IF NOT EXISTS raw.reddit_posts (
    id SERIAL PRIMARY KEY,
    reddit_id VARCHAR(20) NOT NULL UNIQUE,
    subreddit VARCHAR(100) NOT NULL,
    search_keyword VARCHAR(255) NOT NULL,
    post_title TEXT NOT NULL,
    post_body TEXT NULL,
    post_score INTEGER NULL,
    comment_count INTEGER NULL,
    top_comments_text TEXT NULL,
    full_text TEXT NOT NULL,
    vader_compound NUMERIC(5, 4) NULL,
    sentiment_label VARCHAR(10) NULL,
    posted_at TIMESTAMPTZ NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reddit_posts_subreddit ON raw.reddit_posts (subreddit);
CREATE INDEX IF NOT EXISTS idx_reddit_posts_keyword ON raw.reddit_posts (search_keyword);
CREATE INDEX IF NOT EXISTS idx_reddit_posts_scraped_at ON raw.reddit_posts (scraped_at DESC);
