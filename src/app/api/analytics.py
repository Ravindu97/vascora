import csv
import io

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.pipelines.refresh_marts import refresh_marts

router = APIRouter(prefix="/analytics", tags=["analytics"])

DATASET_QUERIES = {
    "store-coverage": "SELECT * FROM marts.store_coverage ORDER BY distance_km NULLS LAST LIMIT :limit",
    "product-matrix": "SELECT * FROM marts.product_matrix ORDER BY ubiquity_score DESC NULLS LAST, store_count DESC LIMIT :limit",
    "price-volatility": "SELECT * FROM marts.price_volatility ORDER BY price_changes_last_30d DESC, last_observed_date DESC LIMIT :limit",
    "new-arrivals": "SELECT * FROM marts.new_arrivals ORDER BY opportunity_flag DESC, days_since_first_seen ASC LIMIT :limit",
}


def _require_ingest_token(x_api_token: str | None) -> None:
    if not x_api_token or x_api_token != settings.ingest_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token.")


def _fetch_dataset_rows(db: Session, dataset: str, limit: int):
    query = DATASET_QUERIES.get(dataset)
    if query is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown dataset.")
    return db.execute(text(query), {"limit": limit}).mappings().all()


def _rows_to_csv(rows) -> str:
    if not rows:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    return output.getvalue()


@router.post("/refresh")
def refresh_analytics(
    x_api_token: str | None = Header(default=None, alias="X-Api-Token"),
):
    _require_ingest_token(x_api_token)
    refresh_marts()
    return {"status": "ok", "message": "Analytics marts refreshed."}


@router.get("/store-coverage")
def get_store_coverage(
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = _fetch_dataset_rows(db, "store-coverage", limit)
    return {"count": len(rows), "rows": [dict(r) for r in rows]}


@router.get("/product-matrix")
def get_product_matrix(
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = _fetch_dataset_rows(db, "product-matrix", limit)
    return {"count": len(rows), "rows": [dict(r) for r in rows]}


@router.get("/price-volatility")
def get_price_volatility(
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = _fetch_dataset_rows(db, "price-volatility", limit)
    return {"count": len(rows), "rows": [dict(r) for r in rows]}


@router.get("/new-arrivals")
def get_new_arrivals(
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = _fetch_dataset_rows(db, "new-arrivals", limit)
    return {"count": len(rows), "rows": [dict(r) for r in rows]}


@router.get("/export/{dataset}")
def export_dataset_csv(
    dataset: str,
    limit: int = Query(default=5000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    rows = _fetch_dataset_rows(db, dataset, limit)
    csv_content = _rows_to_csv(rows)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={dataset}.csv"},
    )
