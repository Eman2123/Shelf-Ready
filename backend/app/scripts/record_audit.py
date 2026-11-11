"""Record the audit runs the Report shows: python -m app.scripts.record_audit [--check]

Audits two catalogs with the real rule engine and stores the result with a run id each:

- audit_messy_csv:      backend/data/demo/messy_catalog.csv (12 products, the BEFORE data)
- audit_published_demo: the hand-authored published demo catalog (4 products)

These are two DIFFERENT catalogs. The second is not the output of the fix engine, so the pair is
not a before/after of fixes and the Report must not present it as one.

A third record, receipt_benchmark_chain, is the hash chain over the stored benchmark runs
(same check as `python -m app.scripts.verify_receipt`).

Writes backend/data/audit/audit_runs.json and a camelCase copy for the frontend. With --check it
writes nothing and exits 1 if the stored files differ from a fresh recomputation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from app.scripts.run_benchmark import _camel
from app.services.audit import RULE_PACK_VERSION, StoreAudit, audit_store
from app.services.benchmark.runner import DATA_PATH, load_runs
from app.services.fixtures.demo_store import PUBLISHED_PRODUCTS
from app.services.importer.csv_import import import_csv
from app.services.receipt import ledger_from_runs

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "data" / "demo" / "messy_catalog.csv"
AUDIT_PATH = ROOT / "data" / "audit" / "audit_runs.json"
FRONTEND_AUDIT_PATH = ROOT.parent / "frontend" / "src" / "lib" / "fixtures" / "recorded-audit.json"

MESSY_RUN_ID = "audit_messy_csv"
PUBLISHED_RUN_ID = "audit_published_demo"
RECEIPT_RUN_ID = "receipt_benchmark_chain"


def _audit_record(run_id: str, label: str, source: str, audit: StoreAudit, names: dict) -> dict:
    return {
        "run_id": run_id,
        "label": label,
        "source": source,
        "rule_pack_version": RULE_PACK_VERSION,
        "store_score": audit.store_score,
        "store_cap_applied": audit.store_cap_applied,
        "notes": audit.notes,
        "products": [
            {
                "product_id": pa.result.product_id,
                "name": names[pa.result.product_id],
                "score": pa.score,
                "raw_score": pa.raw_score,
                "issue_codes": [i.code.value for i in pa.result.issues],
                "checks": [c.model_dump(mode="json") for c in pa.checks],
                "waterfall": [
                    {"label": s.label, "delta": s.delta, "evidence": s.evidence}
                    for s in pa.waterfall
                ],
            }
            for pa in audit.products
        ],
    }


def build_body() -> dict[str, Any]:
    messy = import_csv(CATALOG_PATH.read_text(encoding="utf-8"))
    published = list(PUBLISHED_PRODUCTS.values())
    ledger, outputs = ledger_from_runs(load_runs(DATA_PATH))
    chain = ledger.verify(outputs)
    return {
        "audits": [
            _audit_record(
                MESSY_RUN_ID,
                "Messy catalog (CSV import)",
                "backend/data/demo/messy_catalog.csv",
                audit_store(messy.products, MESSY_RUN_ID),
                {p.id: p.name for p in messy.products},
            ),
            _audit_record(
                PUBLISHED_RUN_ID,
                "Published demo catalog (hand-authored)",
                "backend/app/services/fixtures/demo_store.py",
                audit_store(published, PUBLISHED_RUN_ID),
                {p.id: p.name for p in published},
            ),
        ],
        "receipt": {
            "run_id": RECEIPT_RUN_ID,
            "covers": "stored benchmark runs only",
            "ok": chain.ok,
            "events": chain.checked,
            "head_hash": ledger.head_hash,
            "broken_at": chain.broken_at,
        },
    }


def _payload(body: dict[str, Any]) -> str:
    return json.dumps(body, indent=2, sort_keys=True) + "\n"


def _frontend_payload(body: dict[str, Any], sha: str) -> str:
    out = {"sourceSha256": sha, **_camel(body)}
    return json.dumps(out, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    body = build_body()
    payload = _payload(body)
    sha = hashlib.sha256(payload.encode()).hexdigest()
    frontend = _frontend_payload(body, sha)

    if args.check:
        problems = []
        if not AUDIT_PATH.exists() or AUDIT_PATH.read_text() != payload:
            problems.append(f"{AUDIT_PATH.name} differs from a fresh audit")
        if not FRONTEND_AUDIT_PATH.exists() or FRONTEND_AUDIT_PATH.read_text() != frontend:
            problems.append(f"{FRONTEND_AUDIT_PATH.name} differs from a fresh audit")
        if not body["receipt"]["ok"]:
            problems.append(f"receipt chain broken at {body['receipt']['broken_at']}")
        if problems:
            print("MISMATCH: " + "; ".join(problems))
            return 1
        print(f"OK: stored audit matches a fresh run (sha256 {sha[:16]}...)")
        return 0

    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(payload)
    FRONTEND_AUDIT_PATH.write_text(frontend)
    for a in body["audits"]:
        print(f"{a['run_id']}: store score {a['store_score']} ({len(a['products'])} products)")
    print(f"receipt chain ok={body['receipt']['ok']} events={body['receipt']['events']}")
    print(f"sha256 {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
