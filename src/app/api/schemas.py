from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DevvitPayload(BaseModel):
    reddit_id: str = Field(min_length=3, max_length=20)
    subreddit: str = Field(min_length=1, max_length=100)
    search_keyword: str = Field(min_length=1, max_length=255)
    post_title: str = Field(min_length=1)
    post_body: str | None = None
    post_score: int | None = None
    comment_count: int | None = None
    top_comments_text: str | None = None
    posted_at: datetime

    model_config = ConfigDict(extra="forbid")


class IngestResponse(BaseModel):
    status: str
    reddit_id: str
