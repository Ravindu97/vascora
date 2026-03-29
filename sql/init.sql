CREATE SCHEMA IF NOT EXISTS raw;

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
