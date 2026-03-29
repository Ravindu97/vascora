from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas import DevvitPayload, IngestResponse
from app.core.config import settings
from app.core.db import get_db

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _build_full_text(payload: DevvitPayload) -> str:
    parts = [payload.post_title]
    if payload.post_body:
        parts.append(payload.post_body)
    if payload.top_comments_text:
        parts.append(payload.top_comments_text)
    return "\n\n".join(parts)


@router.post("/reddit", response_model=IngestResponse)
def ingest_reddit(
    payload: DevvitPayload,
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None, alias="X-Webhook-Token"),
):
    if settings.sentiment_source != "devvit_webhook":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sentiment source is not configured for Devvit webhook mode.",
        )

    if not x_webhook_token or x_webhook_token != settings.devvit_webhook_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook token.")

    scraped_at = datetime.now(UTC)
    full_text = _build_full_text(payload)

    upsert_sql = text(
        """
        INSERT INTO raw.reddit_posts (
            reddit_id,
            subreddit,
            search_keyword,
            post_title,
            post_body,
            post_score,
            comment_count,
            top_comments_text,
            full_text,
            posted_at,
            scraped_at,
            vader_compound,
            sentiment_label
        ) VALUES (
            :reddit_id,
            :subreddit,
            :search_keyword,
            :post_title,
            :post_body,
            :post_score,
            :comment_count,
            :top_comments_text,
            :full_text,
            :posted_at,
            :scraped_at,
            NULL,
            NULL
        )
        ON CONFLICT (reddit_id)
        DO UPDATE SET
            subreddit = EXCLUDED.subreddit,
            search_keyword = EXCLUDED.search_keyword,
            post_title = EXCLUDED.post_title,
            post_body = EXCLUDED.post_body,
            post_score = EXCLUDED.post_score,
            comment_count = EXCLUDED.comment_count,
            top_comments_text = EXCLUDED.top_comments_text,
            full_text = EXCLUDED.full_text,
            posted_at = EXCLUDED.posted_at,
            scraped_at = EXCLUDED.scraped_at
        """
    )

    db.execute(
        upsert_sql,
        {
            "reddit_id": payload.reddit_id,
            "subreddit": payload.subreddit,
            "search_keyword": payload.search_keyword,
            "post_title": payload.post_title,
            "post_body": payload.post_body,
            "post_score": payload.post_score,
            "comment_count": payload.comment_count,
            "top_comments_text": payload.top_comments_text,
            "full_text": full_text,
            "posted_at": payload.posted_at,
            "scraped_at": scraped_at,
        },
    )
    db.commit()

    return IngestResponse(status="ok", reddit_id=payload.reddit_id)
