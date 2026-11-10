"""Seed the demo: import the 12-product messy catalog and print what the audit will see.

python -m app.scripts.seed_demo
"""

from __future__ import annotations

from pathlib import Path

from app.services.importer.csv_import import import_csv

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "demo" / "messy_catalog.csv"


def main() -> None:
    result = import_csv(CSV_PATH.read_text(encoding="utf-8"))
    print(f"imported {len(result.products)} of {result.rows_seen} rows from {CSV_PATH.name}")
    for e in result.errors:
        print(f"  line {e.line}: {e.field}: {e.message}")
    vague = [p.name for p in result.products if p.price_cents is None]
    nostock = [p.name for p in result.products if p.stock is None]
    noship = [p.name for p in result.products if p.shipping is None]
    print(
        f"vague or missing price: {len(vague)}; stock not stated: {len(nostock)}; "
        f"no shipping: {len(noship)}"
    )


if __name__ == "__main__":
    main()
