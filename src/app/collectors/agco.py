import argparse
import csv
import math
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import httpx

from app.core.config import settings


def _normalize_key(value: str) -> str:
    return "".join(ch for ch in value.strip().lower() if ch.isalnum())


def _get_field(row: dict[str, Any], *aliases: str) -> str | None:
    if not row:
        return None

    normalized = {_normalize_key(k): v for k, v in row.items()}
    for alias in aliases:
        value = normalized.get(_normalize_key(alias))
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def _geocode_address(address: str, city: str, province: str, postal_code: str | None) -> tuple[float, float] | None:
    if not settings.google_places_api_key:
        return None

    q = f"{address}, {city}, {province}, Canada"
    if postal_code:
        q = f"{q} {postal_code}"

    params = {
        "address": q,
        "key": settings.google_places_api_key,
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.get("https://maps.googleapis.com/maps/api/geocode/json", params=params)
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("status") != "OK":
        return None

    results = payload.get("results", [])
    if not results:
        return None

    location = results[0].get("geometry", {}).get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")
    if lat is None or lng is None:
        return None

    return float(lat), float(lng)


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _download_csv(url: str) -> Path:
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()

    temp = NamedTemporaryFile(delete=False, suffix=".csv")
    temp.write(response.content)
    temp.flush()
    temp.close()
    return Path(temp.name)


def _to_store_record(row: dict[str, str]) -> dict[str, Any] | None:
    licence_number = _get_field(row, "licence_number", "licence number", "license number", "licence#")
    store_name = _get_field(row, "store_name", "store name", "trading name", "operating name")
    street_address = _get_field(row, "street_address", "address", "street", "location")
    city = _get_field(row, "city", "municipality", "town")

    if not licence_number or not store_name or not street_address or not city:
        return None

    province = _get_field(row, "province") or "ON"
    postal_code = _get_field(row, "postal_code", "postal code", "postcode")
    licence_holder_name = _get_field(row, "licence_holder_name", "licence holder", "license holder")
    phone_number = _get_field(row, "phone_number", "phone", "telephone")
    website_url = _get_field(row, "website_url", "website", "url")

    lat_raw = _get_field(row, "latitude", "lat")
    lng_raw = _get_field(row, "longitude", "lng", "lon")

    lat: float | None = None
    lng: float | None = None

    if lat_raw and lng_raw:
        try:
            lat = float(lat_raw)
            lng = float(lng_raw)
        except ValueError:
            lat, lng = None, None

    if lat is None or lng is None:
        geocoded = _geocode_address(street_address, city, province, postal_code)
        if geocoded:
            lat, lng = geocoded

    distance_km: float | None = None
    within_35km = False
    if lat is not None and lng is not None:
        distance_km = _haversine_km(settings.burlington_lat, settings.burlington_lng, lat, lng)
        within_35km = distance_km <= settings.market_radius_km

    now = datetime.now(UTC).isoformat()

    return {
        "licence_number": licence_number,
        "store_name": store_name,
        "licence_holder_name": licence_holder_name,
        "street_address": street_address,
        "city": city,
        "province": province,
        "postal_code": postal_code,
        "phone_number": phone_number,
        "website_url": website_url,
        "latitude": lat,
        "longitude": lng,
        "distance_km": distance_km,
        "within_35km": within_35km,
        "hours_of_operation": None,
        "is_active": True,
        "scraped_at": now,
    }


def _post_batches(records: list[dict[str, Any]], batch_size: int) -> tuple[int, int]:
    if not records:
        return 0, 0

    ingested = 0
    failed_batches = 0

    headers = {
        "Content-Type": "application/json",
        "X-Api-Token": settings.ingest_api_token,
    }
    url = f"{settings.api_base_url.rstrip('/')}/ingest/stores"

    with httpx.Client(timeout=60.0) as client:
        for i in range(0, len(records), batch_size):
            chunk = records[i : i + batch_size]
            response = client.post(url, headers=headers, json={"records": chunk})
            if response.status_code >= 300:
                failed_batches += 1
                continue
            payload = response.json()
            ingested += int(payload.get("ingested", 0))

    return ingested, failed_batches


def run(csv_path: str | None, csv_url: str | None, keep_outside_radius: bool, batch_size: int) -> int:
    if not csv_path and not csv_url:
        raise ValueError("Provide --csv-path or --csv-url.")

    temp_file: Path | None = None
    path: Path

    if csv_url:
        temp_file = _download_csv(csv_url)
        path = temp_file
    else:
        path = Path(csv_path or "")

    rows = _load_csv(path)

    transformed: list[dict[str, Any]] = []
    skipped_invalid = 0
    skipped_outside = 0

    for row in rows:
        record = _to_store_record(row)
        if record is None:
            skipped_invalid += 1
            continue

        if not keep_outside_radius and not record["within_35km"]:
            skipped_outside += 1
            continue

        transformed.append(record)

    ingested, failed_batches = _post_batches(transformed, batch_size=batch_size)

    if temp_file and temp_file.exists():
        temp_file.unlink(missing_ok=True)

    print(f"Rows read: {len(rows)}")
    print(f"Rows transformed: {len(transformed)}")
    print(f"Rows ingested: {ingested}")
    print(f"Invalid rows skipped: {skipped_invalid}")
    print(f"Outside radius skipped: {skipped_outside}")
    print(f"Failed batches: {failed_batches}")

    return 0 if failed_batches == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="AGCO store ingestion.")
    parser.add_argument("--csv-path", type=str, default=None, help="Path to local AGCO CSV file.")
    parser.add_argument("--csv-url", type=str, default=None, help="URL of AGCO CSV file.")
    parser.add_argument(
        "--keep-outside-radius",
        action="store_true",
        help="Ingest all stores even if outside Burlington radius.",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    exit_code = run(
        csv_path=args.csv_path,
        csv_url=args.csv_url,
        keep_outside_radius=args.keep_outside_radius,
        batch_size=args.batch_size,
    )
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
