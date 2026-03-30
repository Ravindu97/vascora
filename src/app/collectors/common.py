import csv
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import httpx

from app.core.config import settings


def normalize_key(value: str) -> str:
    return "".join(ch for ch in value.strip().lower() if ch.isalnum())


def get_field(row: dict[str, Any], *aliases: str) -> str | None:
    if not row:
        return None

    normalized = {normalize_key(k): v for k, v in row.items()}
    for alias in aliases:
        value = normalized.get(normalize_key(alias))
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None

    text = value.strip()
    fmts = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"]
    for fmt in fmts:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip().replace("$", "").replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if text == "":
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    text = value.strip().lower()
    if text in {"1", "true", "yes", "y", "in stock", "active"}:
        return True
    if text in {"0", "false", "no", "n", "out of stock", "inactive"}:
        return False
    return default


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def download_csv(url: str) -> Path:
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()

    temp = NamedTemporaryFile(delete=False, suffix=".csv")
    temp.write(response.content)
    temp.flush()
    temp.close()
    return Path(temp.name)


def post_batches(records: list[dict[str, Any]], endpoint: str, batch_size: int) -> tuple[int, int]:
    if not records:
        return 0, 0

    ingested = 0
    failed_batches = 0

    headers = {
        "Content-Type": "application/json",
        "X-Api-Token": settings.ingest_api_token,
    }
    url = f"{settings.api_base_url.rstrip('/')}{endpoint}"

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


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
