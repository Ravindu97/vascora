from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RedditPost(Base):
    __tablename__ = "reddit_posts"
    __table_args__ = {"schema": "raw"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reddit_id: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, unique=True)
    subreddit: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    search_keyword: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    post_title: Mapped[str] = mapped_column(Text, nullable=False)
    post_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_comments_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vader_compound: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(VARCHAR(10), nullable=True)
