import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas import (
    BatchIngestResponse,
    BatchOcsPayload,
    BatchPricingPayload,
    BatchProductPayload,
    BatchStorePayload,
)
from app.core.config import settings
from app.core.db import get_db

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _require_ingest_token(x_api_token: str | None) -> None:
    if not x_api_token or x_api_token != settings.ingest_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token.")


@router.post("/stores", response_model=BatchIngestResponse)
def ingest_stores(
    payload: BatchStorePayload,
    db: Session = Depends(get_db),
    x_api_token: str | None = Header(default=None, alias="X-Api-Token"),
):
    _require_ingest_token(x_api_token)

    now = datetime.now(UTC)
    rows = []
    for record in payload.records:
        rows.append(
            {
                "licence_number": record.licence_number,
                "store_name": record.store_name,
                "licence_holder_name": record.licence_holder_name,
                "street_address": record.street_address,
                "city": record.city,
                "province": record.province,
                "postal_code": record.postal_code,
                "phone_number": record.phone_number,
                "website_url": record.website_url,
                "latitude": record.latitude,
                "longitude": record.longitude,
                "distance_km": record.distance_km,
                "within_35km": record.within_35km,
                "hours_of_operation": json.dumps(record.hours_of_operation)
                if record.hours_of_operation
                else None,
                "is_active": record.is_active,
                "scraped_at": record.scraped_at or now,
            }
        )

    upsert_sql = text(
        """
        INSERT INTO raw.agco_stores (
            licence_number,
            store_name,
            licence_holder_name,
            street_address,
            city,
            province,
            postal_code,
            phone_number,
            website_url,
            latitude,
            longitude,
            distance_km,
            within_35km,
            hours_of_operation,
            is_active,
            scraped_at
        ) VALUES (
            :licence_number,
            :store_name,
            :licence_holder_name,
            :street_address,
            :city,
            :province,
            :postal_code,
            :phone_number,
            :website_url,
            :latitude,
            :longitude,
            :distance_km,
            :within_35km,
            CAST(:hours_of_operation AS JSONB),
            :is_active,
            :scraped_at
        )
        ON CONFLICT (licence_number)
        DO UPDATE SET
            store_name = EXCLUDED.store_name,
            licence_holder_name = EXCLUDED.licence_holder_name,
            street_address = EXCLUDED.street_address,
            city = EXCLUDED.city,
            province = EXCLUDED.province,
            postal_code = EXCLUDED.postal_code,
            phone_number = EXCLUDED.phone_number,
            website_url = EXCLUDED.website_url,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            distance_km = EXCLUDED.distance_km,
            within_35km = EXCLUDED.within_35km,
            hours_of_operation = EXCLUDED.hours_of_operation,
            is_active = EXCLUDED.is_active,
            scraped_at = EXCLUDED.scraped_at
        """
    )

    db.execute(upsert_sql, rows)
    db.commit()
    return BatchIngestResponse(status="ok", ingested=len(rows))


@router.post("/products", response_model=BatchIngestResponse)
def ingest_products(
    payload: BatchProductPayload,
    db: Session = Depends(get_db),
    x_api_token: str | None = Header(default=None, alias="X-Api-Token"),
):
    _require_ingest_token(x_api_token)

    now = datetime.now(UTC)
    rows = []
    for record in payload.records:
        rows.append(
            {
                "licence_number": record.licence_number,
                "pos_platform": record.pos_platform,
                "pos_sku": record.pos_sku,
                "product_name": record.product_name,
                "brand_name": record.brand_name,
                "category_raw": record.category_raw,
                "thc_pct_min": record.thc_pct_min,
                "thc_pct_max": record.thc_pct_max,
                "cbd_pct_min": record.cbd_pct_min,
                "cbd_pct_max": record.cbd_pct_max,
                "weight_grams": record.weight_grams,
                "unit_count": record.unit_count,
                "ocs_sku": record.ocs_sku,
                "in_stock": record.in_stock,
                "is_active": record.is_active,
                "scraped_at": record.scraped_at or now,
            }
        )

    upsert_sql = text(
        """
        INSERT INTO raw.store_products (
            licence_number,
            pos_platform,
            pos_sku,
            product_name,
            brand_name,
            category_raw,
            thc_pct_min,
            thc_pct_max,
            cbd_pct_min,
            cbd_pct_max,
            weight_grams,
            unit_count,
            ocs_sku,
            in_stock,
            is_active,
            scraped_at
        ) VALUES (
            :licence_number,
            :pos_platform,
            :pos_sku,
            :product_name,
            :brand_name,
            :category_raw,
            :thc_pct_min,
            :thc_pct_max,
            :cbd_pct_min,
            :cbd_pct_max,
            :weight_grams,
            :unit_count,
            :ocs_sku,
            :in_stock,
            :is_active,
            :scraped_at
        )
        ON CONFLICT (licence_number, pos_sku, product_name)
        DO UPDATE SET
            pos_platform = EXCLUDED.pos_platform,
            brand_name = EXCLUDED.brand_name,
            category_raw = EXCLUDED.category_raw,
            thc_pct_min = EXCLUDED.thc_pct_min,
            thc_pct_max = EXCLUDED.thc_pct_max,
            cbd_pct_min = EXCLUDED.cbd_pct_min,
            cbd_pct_max = EXCLUDED.cbd_pct_max,
            weight_grams = EXCLUDED.weight_grams,
            unit_count = EXCLUDED.unit_count,
            ocs_sku = EXCLUDED.ocs_sku,
            in_stock = EXCLUDED.in_stock,
            is_active = EXCLUDED.is_active,
            scraped_at = EXCLUDED.scraped_at
        """
    )

    db.execute(upsert_sql, rows)
    db.commit()
    return BatchIngestResponse(status="ok", ingested=len(rows))


@router.post("/pricing", response_model=BatchIngestResponse)
def ingest_pricing(
    payload: BatchPricingPayload,
    db: Session = Depends(get_db),
    x_api_token: str | None = Header(default=None, alias="X-Api-Token"),
):
    _require_ingest_token(x_api_token)

    now = datetime.now(UTC)
    rows = []
    for record in payload.records:
        rows.append(
            {
                "licence_number": record.licence_number,
                "pos_sku": record.pos_sku,
                "product_name": record.product_name,
                "brand_name": record.brand_name,
                "regular_price_cad": record.regular_price_cad,
                "sale_price_cad": record.sale_price_cad,
                "promo_label": record.promo_label,
                "promo_start_date": record.promo_start_date,
                "promo_end_date": record.promo_end_date,
                "in_stock": record.in_stock,
                "scraped_at": record.scraped_at or now,
            }
        )

    insert_sql = text(
        """
        INSERT INTO raw.product_pricing (
            licence_number,
            pos_sku,
            product_name,
            brand_name,
            regular_price_cad,
            sale_price_cad,
            promo_label,
            promo_start_date,
            promo_end_date,
            in_stock,
            scraped_at
        ) VALUES (
            :licence_number,
            :pos_sku,
            :product_name,
            :brand_name,
            :regular_price_cad,
            :sale_price_cad,
            :promo_label,
            :promo_start_date,
            :promo_end_date,
            :in_stock,
            :scraped_at
        )
        """
    )

    db.execute(insert_sql, rows)
    db.commit()
    return BatchIngestResponse(status="ok", ingested=len(rows))


@router.post("/ocs", response_model=BatchIngestResponse)
def ingest_ocs_catalog(
    payload: BatchOcsPayload,
    db: Session = Depends(get_db),
    x_api_token: str | None = Header(default=None, alias="X-Api-Token"),
):
    _require_ingest_token(x_api_token)

    now = datetime.now(UTC)
    rows = []
    for record in payload.records:
        rows.append(
            {
                "ocs_sku": record.ocs_sku,
                "product_name": record.product_name,
                "brand_name": record.brand_name,
                "category_raw": record.category_raw,
                "thc_pct_min": record.thc_pct_min,
                "thc_pct_max": record.thc_pct_max,
                "cbd_pct_min": record.cbd_pct_min,
                "cbd_pct_max": record.cbd_pct_max,
                "weight_grams": record.weight_grams,
                "ocs_price_cad": record.ocs_price_cad,
                "first_seen_at": record.first_seen_at,
                "last_seen_at": record.last_seen_at,
                "scraped_at": record.scraped_at or now,
            }
        )

    upsert_sql = text(
        """
        INSERT INTO raw.ocs_catalog (
            ocs_sku,
            product_name,
            brand_name,
            category_raw,
            thc_pct_min,
            thc_pct_max,
            cbd_pct_min,
            cbd_pct_max,
            weight_grams,
            ocs_price_cad,
            first_seen_at,
            last_seen_at,
            scraped_at
        ) VALUES (
            :ocs_sku,
            :product_name,
            :brand_name,
            :category_raw,
            :thc_pct_min,
            :thc_pct_max,
            :cbd_pct_min,
            :cbd_pct_max,
            :weight_grams,
            :ocs_price_cad,
            :first_seen_at,
            :last_seen_at,
            :scraped_at
        )
        ON CONFLICT (ocs_sku)
        DO UPDATE SET
            product_name = EXCLUDED.product_name,
            brand_name = EXCLUDED.brand_name,
            category_raw = EXCLUDED.category_raw,
            thc_pct_min = EXCLUDED.thc_pct_min,
            thc_pct_max = EXCLUDED.thc_pct_max,
            cbd_pct_min = EXCLUDED.cbd_pct_min,
            cbd_pct_max = EXCLUDED.cbd_pct_max,
            weight_grams = EXCLUDED.weight_grams,
            ocs_price_cad = EXCLUDED.ocs_price_cad,
            first_seen_at = LEAST(raw.ocs_catalog.first_seen_at, EXCLUDED.first_seen_at),
            last_seen_at = GREATEST(raw.ocs_catalog.last_seen_at, EXCLUDED.last_seen_at),
            scraped_at = EXCLUDED.scraped_at
        """
    )

    db.execute(upsert_sql, rows)
    db.commit()
    return BatchIngestResponse(status="ok", ingested=len(rows))
