"""End to end (PRD Day 5 e2e): import -> store MCP -> benchmark -> report numbers.

Scope, stated plainly: nothing here turns the imported messy catalog into the published one
(the published catalog is hand-written, not fix-engine output). The MCP serves the frozen published fixture, and
the money step is BenchmarkGuard on the real KeyStore and policy engine (PayPal is not
connected, so no PayPal order exists). What this proves is that
every hop that exists today agrees with the next one, and that the numbers the Report shows are
recomputed from stored runs, not typed in.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp.client.client import Client

from app.scripts.run_benchmark import export_frontend, export_variants
from app.services.benchmark.guard import BenchmarkGuard
from app.services.benchmark.runner import BENCH_NOW, load_runs, metrics, run_suite, save_runs
from app.services.benchmark.variants import load_variants, run_variants, save_variants
from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.importer.csv_import import import_csv
from app.services.mcp_store import StoreService
from app.services.mcp_store.server import build_server

CSV = Path(__file__).resolve().parents[1] / "data" / "demo" / "messy_catalog.csv"


def _store() -> tuple[StoreService, BenchmarkGuard]:
    products = {k: v.model_copy(deep=True) for k, v in PUBLISHED_PRODUCTS.items()}
    service = StoreService(products, DEFAULT_POLICY, clock=lambda: BENCH_NOW)
    guard = BenchmarkGuard(service)
    service.guarded_order, service.verify_key = guard.guarded_order, guard.verify_key
    return service, guard


def test_import_keeps_unstated_facts_unstated():
    imported = import_csv(CSV.read_text(encoding="utf-8"))
    assert len(imported.products) == 12 and not imported.errors
    tee = next(p for p in imported.products if p.sku == "TEE")
    assert tee.price_cents is None and tee.price_text == "from $20" and tee.stock is None


def test_mcp_client_buys_the_exact_variant_with_no_html_and_a_checked_key():
    service, guard = _store()

    async def buy(agent_key: str):
        async with Client(build_server(service)) as client:
            found = await client.call_tool("search_products", {"query": "tee"})
            pid = found.structured_content["result"][0]["product_id"]
            prod = await client.call_tool("get_product", {"product_id": pid})
            quote = next(
                q for q in prod.structured_content["quotes"] if q["variant_sku"] == "TEE-BLU-M"
            )
            order = await client.call_tool(
                "create_order",
                {
                    "items": [{"product_id": pid, "quantity": 1, "quote_id": quote["quote_id"]}],
                    "ship_to_country": "US",
                    "idempotency_key": "idem-e2e-0001",
                    "agent_key": agent_key,
                },
            )
            return quote, order.structured_content

    quote, order = asyncio.run(buy(guard.raw_key))
    assert quote["unit_price_cents"] == 2400  # exact, where the messy page said "from $20"
    assert order["status"] == "CREATED"
    assert order["paypal_order_id"] is None  # simulated: this repo never claims a PayPal order

    # a blank key is refused by store code, not by the agent
    _, refused = asyncio.run(buy(" "))
    assert refused["error"] == "KEY_UNKNOWN"


def test_benchmark_to_report_numbers_are_recomputed_and_traceable(tmp_path):
    records = run_suite(k=1)
    m = metrics(records)
    assert len(records) == 24
    assert m["AFTER"]["unsafe_actions"] == 0 and m["AFTER"]["html_bytes"] == 0
    assert m["BEFORE"]["unsafe_actions"] > 0

    runs_path, front = tmp_path / "runs.json", tmp_path / "recorded-runs.json"
    sha = save_runs(records, path=runs_path, k=1)
    replayed = load_runs(runs_path)  # replay mode: re-read, nothing executed
    assert [r.run.id for r in replayed] == [r.run.id for r in records]
    assert metrics(replayed) == m

    export_frontend(records, sha, 1, path=front)
    exported = json.loads(front.read_text())
    assert exported["sourceSha256"] == sha
    run_ids = {r["run"]["id"] for r in exported["runs"]}
    for mode in ("BEFORE", "AFTER"):
        for task in exported["metrics"][mode]["perTask"].values():
            assert set(task["runIds"]) <= run_ids  # every number points at real runs
    assert exported["metrics"]["AFTER"]["unsafeActions"] == 0


def test_variants_are_recorded_exported_and_labelled(tmp_path):
    results = run_variants()
    vpath, vfront = tmp_path / "variants.json", tmp_path / "recorded-variants.json"
    vsha = save_variants(results, path=vpath)
    export_variants(results, vsha, path=vfront)
    assert load_variants(vpath) == results
    exported = json.loads(vfront.read_text())
    assert exported["label"] == "n=5 demo variants" and "no LLM" in exported["reader"]
    assert exported["sourceSha256"] == vsha
    assert len({r["runId"] for r in exported["runs"]}) == 5
    assert [r["variant"] for r in exported["runs"] if r["passed"]] == ["clean", "injection"]
