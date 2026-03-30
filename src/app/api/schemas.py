from datetime import date, datetime
from decimal import Decimal

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


class StorePayload(BaseModel):
    licence_number: str = Field(min_length=1, max_length=50)
    store_name: str = Field(min_length=1, max_length=255)
    licence_holder_name: str | None = Field(default=None, max_length=255)
    street_address: str = Field(min_length=1, max_length=500)
    city: str = Field(min_length=1, max_length=100)
    province: str = Field(default="ON", max_length=50)
    postal_code: str | None = Field(default=None, max_length=10)
    phone_number: str | None = Field(default=None, max_length=50)
    website_url: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    distance_km: Decimal | None = None
    within_35km: bool = False
    hours_of_operation: dict[str, str] | None = None
    is_active: bool = True
    scraped_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class OcsPayload(BaseModel):
    ocs_sku: str = Field(min_length=1, max_length=100)
    product_name: str = Field(min_length=1, max_length=500)
    brand_name: str | None = Field(default=None, max_length=255)
    category_raw: str | None = Field(default=None, max_length=100)
    thc_pct_min: Decimal | None = None
    thc_pct_max: Decimal | None = None
    cbd_pct_min: Decimal | None = None
    cbd_pct_max: Decimal | None = None
    weight_grams: Decimal | None = None
    ocs_price_cad: Decimal | None = None
    first_seen_at: date
    last_seen_at: date
    scraped_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class ProductPayload(BaseModel):
    licence_number: str = Field(min_length=1, max_length=50)
    pos_platform: str | None = Field(default=None, max_length=50)
    pos_sku: str | None = Field(default=None, max_length=255)
    product_name: str = Field(min_length=1, max_length=500)
    brand_name: str | None = Field(default=None, max_length=255)
    category_raw: str | None = Field(default=None, max_length=100)
    thc_pct_min: Decimal | None = None
    thc_pct_max: Decimal | None = None
    cbd_pct_min: Decimal | None = None
    cbd_pct_max: Decimal | None = None
    weight_grams: Decimal | None = None
    unit_count: int | None = None
    ocs_sku: str | None = Field(default=None, max_length=100)
    in_stock: bool = True
    is_active: bool = True
    scraped_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class PricingPayload(BaseModel):
    licence_number: str = Field(min_length=1, max_length=50)
    pos_sku: str | None = Field(default=None, max_length=255)
    product_name: str = Field(min_length=1, max_length=500)
    brand_name: str | None = Field(default=None, max_length=255)
    regular_price_cad: Decimal
    sale_price_cad: Decimal | None = None
    promo_label: str | None = Field(default=None, max_length=255)
    promo_start_date: date | None = None
    promo_end_date: date | None = None
    in_stock: bool = True
    scraped_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class BatchStorePayload(BaseModel):
    records: list[StorePayload] = Field(min_length=1)


class BatchOcsPayload(BaseModel):
    records: list[OcsPayload] = Field(min_length=1)


class BatchProductPayload(BaseModel):
    records: list[ProductPayload] = Field(min_length=1)


class BatchPricingPayload(BaseModel):
    records: list[PricingPayload] = Field(min_length=1)


class BatchIngestResponse(BaseModel):
    status: str
    ingested: int
