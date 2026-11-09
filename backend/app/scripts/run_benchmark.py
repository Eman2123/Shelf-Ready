"""Run the 12-task benchmark (k runs per task, BEFORE and AFTER) and store every run.

    python -m app.scripts.run_benchmark [--k 3] [--no-frontend]

Writes backend/data/benchmark/runs.json (the recorded set that replay mode and the Report read)
and a camelCase copy for the frontend. Prints the hash of the stored file for the receipt.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from app.contracts import AgentMode
from app.services.benchmark.runner import (
    DATA_PATH,
    DEFAULT_K,
    RunRecord,
    metrics,
    run_suite,
    save_runs,
)
from app.services.benchmark.tasks import TASKS

FRONTEND_PATH = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "lib"
    / "fixtures"
    / "recorded-runs.json"
)


# Raw tool traffic keeps its real (snake_case) keys, so the UI shows what the MCP really returned.
_RAW_KEYS = {"input", "output", "final"}


def _camel(value):
    if isinstance(value, dict):
        return {
            re.sub(r"_([a-z])", lambda m: m.group(1).upper(), k): (
                v if k in _RAW_KEYS else _camel(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_camel(v) for v in value]
    return value


def export_frontend(records: list[RunRecord], sha: str, k: int, path: Path = FRONTEND_PATH) -> None:
    body = {
        "sourceSha256": sha,
        "k": k,
        "agentConfigs": sorted({r.run.agent_config for r in records}),
        "tasks": [t.task.model_dump(mode="json") for t in TASKS],
        "metrics": metrics(records),
        "runs": [r.model_dump(mode="json") for r in records],
    }
    path.write_text(json.dumps(_camel(body), indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--no-frontend", action="store_true")
    args = ap.parse_args(argv)
    records = run_suite(k=args.k)
    sha = save_runs(records, k=args.k)
    if not args.no_frontend:
        export_frontend(records, sha, args.k)
    m = metrics(records)
    print(f"{len(records)} runs stored in {DATA_PATH}  sha256={sha}")
    for mode in (AgentMode.BEFORE, AgentMode.AFTER):
        x = m[mode.value]
        print(
            f"{mode.value:6} completion {x['completion']['success']}/{x['completion']['runs']}  "
            f"safe-stop {x['safe_stop']['success']}/{x['safe_stop']['runs']}  "
            f"unsafe actions {x['unsafe_actions']}  wrong purchases {x['wrong_purchases']}  "
            f"html bytes {x['html_bytes']}"
        )


if __name__ == "__main__":
    main()
