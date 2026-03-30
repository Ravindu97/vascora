import argparse
from pathlib import Path

from app.collectors.common import (
    download_csv,
    get_field,
    load_csv,
    parse_bool,
    parse_decimal,
    parse_int,
    post_batches,
    utc_now_iso,
)


def _to_record(row: dict[str, str]) -> dict | None:
    licence_number = get_field(row, "licence_number", "license_number", "store_licence_number")
    product_name = get_field(row, "product_name", "name", "item_name")

    if not licence_number or not product_name:
        return None

    return {
        "licence_number": licence_number,
        "pos_platform": get_field(row, "pos_platform", "platform"),
        "pos_sku": get_field(row, "pos_sku", "sku", "product_id"),
        "product_name": product_name,
        "brand_name": get_field(row, "brand_name", "brand"),
        "category_raw": get_field(row, "category_raw", "category"),
        "thc_pct_min": parse_decimal(get_field(row, "thc_pct_min", "thc_min")),
        "thc_pct_max": parse_decimal(get_field(row, "thc_pct_max", "thc_max")),
        "cbd_pct_min": parse_decimal(get_field(row, "cbd_pct_min", "cbd_min")),
        "cbd_pct_max": parse_decimal(get_field(row, "cbd_pct_max", "cbd_max")),
        "weight_grams": parse_decimal(get_field(row, "weight_grams", "weight_g", "weight")),
        "unit_count": parse_int(get_field(row, "unit_count", "count")),
        "ocs_sku": get_field(row, "ocs_sku"),
        "in_stock": parse_bool(get_field(row, "in_stock"), default=True),
        "is_active": parse_bool(get_field(row, "is_active"), default=True),
        "scraped_at": utc_now_iso(),
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

    ingested, failed = post_batches(records, endpoint="/ingest/products", batch_size=batch_size)

    if temp_file and temp_file.exists():
        temp_file.unlink(missing_ok=True)

    print(f"Rows read: {len(rows)}")
    print(f"Rows transformed: {len(records)}")
    print(f"Rows ingested: {ingested}")
    print(f"Invalid rows skipped: {skipped}")
    print(f"Failed batches: {failed}")

    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Store product ingestion.")
    parser.add_argument("--csv-path", type=str, default=None)
    parser.add_argument("--csv-url", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=250)
    args = parser.parse_args()

    raise SystemExit(run(csv_path=args.csv_path, csv_url=args.csv_url, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
