import argparse
from pathlib import Path

from app.collectors.common import (
    download_csv,
    get_field,
    load_csv,
    parse_bool,
    parse_date,
    parse_decimal,
    post_batches,
    utc_now_iso,
)


def _to_record(row: dict[str, str]) -> dict | None:
    licence_number = get_field(row, "licence_number", "license_number", "store_licence_number")
    product_name = get_field(row, "product_name", "name", "item_name")
    regular_price = parse_decimal(get_field(row, "regular_price_cad", "regular_price", "price"))

    if not licence_number or not product_name or regular_price is None:
        return None

    return {
        "licence_number": licence_number,
        "pos_sku": get_field(row, "pos_sku", "sku", "product_id"),
        "product_name": product_name,
        "brand_name": get_field(row, "brand_name", "brand"),
        "regular_price_cad": regular_price,
        "sale_price_cad": parse_decimal(get_field(row, "sale_price_cad", "sale_price", "promo_price")),
        "promo_label": get_field(row, "promo_label", "promotion", "deal"),
        "promo_start_date": parse_date(get_field(row, "promo_start_date", "promo_start")),
        "promo_end_date": parse_date(get_field(row, "promo_end_date", "promo_end")),
        "in_stock": parse_bool(get_field(row, "in_stock"), default=True),
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

    ingested, failed = post_batches(records, endpoint="/ingest/pricing", batch_size=batch_size)

    if temp_file and temp_file.exists():
        temp_file.unlink(missing_ok=True)

    print(f"Rows read: {len(rows)}")
    print(f"Rows transformed: {len(records)}")
    print(f"Rows ingested: {ingested}")
    print(f"Invalid rows skipped: {skipped}")
    print(f"Failed batches: {failed}")

    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Product pricing ingestion.")
    parser.add_argument("--csv-path", type=str, default=None)
    parser.add_argument("--csv-url", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    raise SystemExit(run(csv_path=args.csv_path, csv_url=args.csv_url, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
