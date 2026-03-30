import argparse

from app.collectors.agco import run as run_agco
from app.collectors.ocs import run as run_ocs
from app.collectors.pricing import run as run_pricing
from app.collectors.products import run as run_products
from app.pipelines.refresh_marts import refresh_marts


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ingestion collectors then refresh analytics marts.")
    parser.add_argument("--agco-csv", required=True, help="Path to AGCO stores CSV")
    parser.add_argument("--products-csv", required=True, help="Path to products CSV")
    parser.add_argument("--pricing-csv", required=True, help="Path to pricing CSV")
    parser.add_argument("--ocs-csv", required=True, help="Path to OCS catalog CSV")
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--keep-outside-radius", action="store_true")
    args = parser.parse_args()

    print("Running AGCO ingestion...")
    rc_agco = run_agco(
        csv_path=args.agco_csv,
        csv_url=None,
        keep_outside_radius=args.keep_outside_radius,
        batch_size=args.batch_size,
    )

    print("Running product ingestion...")
    rc_products = run_products(csv_path=args.products_csv, csv_url=None, batch_size=args.batch_size)

    print("Running pricing ingestion...")
    rc_pricing = run_pricing(csv_path=args.pricing_csv, csv_url=None, batch_size=args.batch_size)

    print("Running OCS ingestion...")
    rc_ocs = run_ocs(csv_path=args.ocs_csv, csv_url=None, batch_size=args.batch_size)

    if any(code != 0 for code in [rc_agco, rc_products, rc_pricing, rc_ocs]):
        raise SystemExit(1)

    print("Refreshing marts...")
    refresh_marts()
    print("Ingestion and marts refresh complete.")


if __name__ == "__main__":
    main()
