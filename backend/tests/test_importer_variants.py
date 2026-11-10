from pathlib import Path

from app.services.benchmark.variants import run_variants
from app.services.connector.normalize import sync_catalog
from app.services.importer.csv_import import import_csv, parse_price

CSV = Path(__file__).resolve().parents[1] / "data" / "demo" / "messy_catalog.csv"


def test_demo_csv_has_twelve_products_and_keeps_vague_prices_unguessed():
    r = import_csv(CSV.read_text())
    assert len(r.products) == 12 and not r.errors
    tee = next(p for p in r.products if p.sku == "TEE")
    assert tee.price_cents is None and tee.price_text == "from $20" and tee.stock is None
    mug = next(p for p in r.products if p.sku == "MUG")
    assert [v.stock for v in mug.variants] == [0, None]


def test_invalid_rows_are_reported_with_line_numbers_and_do_not_stop_import():
    text = (
        "sku,name,price,stock\n"
        "A,Good,$5.00,3\n"
        ",,$1.00,1\n"
        "B,Bad stock,$2.00,many\n"
        "A,Dup,$3.00,1\n"
        "C,Short row\n"
        "D,Fine,$7.50,0\n"
    )
    r = import_csv(text)
    assert [p.sku for p in r.products] == ["A", "D"]
    assert [(e.line, e.field) for e in r.errors] == [
        (3, "name"),
        (4, "stock"),
        (5, "sku"),
        (6, "row"),
    ]


def test_missing_name_column_and_empty_file():
    assert import_csv("sku,price\nA,1").errors[0].field == "header"
    assert import_csv("").errors[0].message == "file is empty"


def test_parse_price():
    assert parse_price("$24.00") == 2400 and parse_price("18") == 1800
    assert parse_price("from $20") is None and parse_price("") is None


def test_sync_catalog_dedupes_and_detects_changes():
    items = [{"id": "P1", "name": "Tee", "price": "24.00", "sku": "TEE"}]
    store: dict = {}
    assert sync_catalog(store, lambda: items).added == ["pp_P1"]
    again = sync_catalog(store, lambda: items)
    assert again.skipped == ["pp_P1"] and len(store) == 1
    items[0]["price"] = "26.00"
    changed = sync_catalog(store, lambda: items)
    assert changed.updated == ["pp_P1"] and store["pp_P1"].price_cents == 2600


def test_variants_only_clean_page_is_fully_readable_and_injection_is_ignored():
    res = {r.variant: r for r in run_variants()}
    assert len(res) == 5
    assert res["clean"].passed
    assert not res["price_ambiguous"].passed and not res["stock_missing"].passed
    assert not res["shipping_hidden"].passed
    assert res["injection"].passed and not res["injection"].obeyed_injection
