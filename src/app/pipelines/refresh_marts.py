from pathlib import Path

from sqlalchemy import text

from app.core.db import SessionLocal


def refresh_marts(sql_file: str = "sql/marts.sql") -> None:
    sql_path = Path(sql_file)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    sql_text = sql_path.read_text(encoding="utf-8")

    with SessionLocal() as db:
        db.execute(text(sql_text))
        db.commit()


def main() -> None:
    refresh_marts()
    print("Marts refreshed successfully.")


if __name__ == "__main__":
    main()
