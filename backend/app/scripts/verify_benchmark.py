"""Check the stored benchmark record: python -m app.scripts.verify_benchmark

1. The file's SHA-256 is the fingerprint printed in the Report.
2. The numbers the Report shows (frontend export) equal numbers recomputed from the stored runs.
3. Re-running every task now gives the same outcomes as the stored runs (the record is honest).
Exit code 1 if anything differs.
"""

from __future__ import annotations

import hashlib
import json
import sys

from app.scripts.run_benchmark import FRONTEND_PATH, _camel
from app.services.benchmark.runner import DATA_PATH, load_runs, metrics, run_suite


def main() -> int:
    problems: list[str] = []
    stored = load_runs()
    sha = hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()
    k = json.loads(DATA_PATH.read_text())["k"]

    exported = json.loads(FRONTEND_PATH.read_text())
    if exported["sourceSha256"] != sha:
        problems.append("Report fingerprint differs from the stored runs file")
    if exported["metrics"] != _camel(metrics(stored)):
        problems.append("Report metrics differ from metrics recomputed from the stored runs")
    if len(exported["runs"]) != len(stored):
        problems.append("Report has a different number of runs than the stored file")

    fresh = {r.run.id: r for r in run_suite(k=k)}
    for r in stored:
        f = fresh.get(r.run.id)
        if f is None or (f.run.outcome, f.final) != (r.run.outcome, r.final):
            problems.append(f"{r.run.id}: re-running gives a different result")

    print(f"runs: {len(stored)}  k={k}  sha256={sha}")
    if problems:
        print("\n".join(f"FAIL {p}" for p in problems))
        return 1
    print("OK: fingerprint, report numbers and a fresh re-run all match the stored record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
