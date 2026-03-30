import argparse
from datetime import UTC, date, datetime
from pathlib import Path

from app.collectors.common import (
    download_csv,
    get_field,
    load_csv,
    parse_date,
    parse_decimal,
    post_batches,
)


def _to_record(row: dict[str, str]) -> dict | None:
    ocs_sku = get_field(row, "ocs_sku", "sku")
    product_name = get_field(row, "product_name", "name", "item_name")
    first_seen = parse_date(get_field(row, "first_seen_at", "first_seen"))
    last_seen = parse_date(get_field(row, "last_seen_at", "last_seen"))

    if not ocs_sku or not product_name:
        return None

    today = datetime.now(UTC).date()

    return {
        "ocs_sku": ocs_sku,
        "product_name": product_name,
        "brand_name": get_field(row, "brand_name", "brand"),
        "category_raw": get_field(row, "category_raw", "category"),
        "thc_pct_min": parse_decimal(get_field(row, "thc_pct_min", "thc_min")),
        "thc_pct_max": parse_decimal(get_field(row, "thc_pct_max", "thc_max")),
        "cbd_pct_min": parse_decimal(get_field(row, "cbd_pct_min", "cbd_min")),
        "cbd_pct_max": parse_decimal(get_field(row, "cbd_pct_max", "cbd_max")),
        "weight_grams": parse_decimal(get_field(row, "weight_grams", "weight_g", "weight")),
        "ocs_price_cad": parse_decimal(get_field(row, "ocs_price_cad", "price")),
        "first_seen_at": first_seen or today,
        "last_seen_at": last_seen or today,
        "scraped_at": datetime.now(UTC).isoformat(),
    }


def run(csv_path: str | None, csv_url: str | None, batch_size: int) -> int:
    if not csv_path and not csv_url:
        raise ValueError("Provide --csv-path or --csv-url.")

    temp_file: Path | None = None
    path: Path

    if csv_url:
        temp_file = download_csv(csv_url)
        path = temp_file
    else:
        path = Path(csv_path or "")

    rows = load_csv(path)

    records = []
    skipped = 0
    for row in rows:
        rec = _to_record(row)
        if rec is None:
            skipped += 1
            continue
        records.append(rec)

    ingested, failed = post_batches(records, endpoint="/ingest/ocs", batch_size=batch_size)

    if temp_file and temp_file.exists():
        temp_file.unlink(missing_ok=True)

    print(f"Rows read: {len(rows)}")
    print(f"Rows transformed: {len(records)}")
    print(f"Rows ingested: {ingested}")
    print(f"Invalid rows skipped: {skipped}")
    print(f"Failed batches: {failed}")

    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="OCS catalog ingestion.")
    parser.add_argument("--csv-path", type=str, default=None)
    parser.add_argument("--csv-url", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    raise SystemExit(run(csv_path=args.csv_path, csv_url=args.csv_url, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
