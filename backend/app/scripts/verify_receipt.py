"""Check the receipt chain over the stored benchmark runs: python -m app.scripts.verify_receipt

Rebuilds the hash chain from backend/data/benchmark/runs.json, recomputes every event's output
hash, and prints the head hash. Exit code 1 if any link or output differs.

Scope: this covers the benchmark runs only. The full Purchase Trace (source snapshot, audit,
quote, PayPal order, webhook) needs the live event store, which comes with the PayPal layer.
"""

from __future__ import annotations

import sys

from app.services.benchmark.runner import DATA_PATH, load_runs
from app.services.receipt import ledger_from_runs


def main() -> int:
    runs = load_runs(DATA_PATH)
    ledger, outputs = ledger_from_runs(runs)
    check = ledger.verify(outputs)
    if not check.ok:
        print(f"BROKEN at {check.broken_at}: {check.reason}")
        return 1
    print(f"Receipt chain: intact ({check.checked} events, head {ledger.head_hash[:16]}...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
