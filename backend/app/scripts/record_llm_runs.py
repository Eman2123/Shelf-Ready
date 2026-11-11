"""Record real LLM benchmark runs. Refuses to run without an API key and model.

    python -m app.scripts.record_llm_runs --tasks A2,B4 --k 1
    python -m app.scripts.record_llm_runs --check        # config check only, no model call

Set AI_PROVIDER and the matching *_API_KEY / *_MODEL in backend/.env (never commit it).
"""

from __future__ import annotations

import argparse
import sys

from app.services.ai.client import ChatClient, LLMError, load_llm_config
from app.services.benchmark.llm_runner import LLM_RUNS_PATH, run_llm_suite, save_llm_runs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--tasks", default="", help="comma list, e.g. A2,B4 (default: all 12)")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    cfg = load_llm_config()
    if cfg is None:
        print(
            "LLM not connected: set AI_PROVIDER and the matching *_API_KEY and *_MODEL "
            "(see .env.example). No run was made."
        )
        return 2
    print(f"LLM configured: provider={cfg.provider} model={cfg.model} (key set, not shown)")
    if args.check:
        return 0
    client = ChatClient(cfg)
    ids = [t.strip() for t in args.tasks.split(",") if t.strip()] or None
    try:
        records = run_llm_suite(client, args.k, ids)
    except LLMError as e:
        print(f"LLM call failed: {e}")
        return 1
    sha = save_llm_runs(records, client, args.k)
    ok = sum(r.run.outcome.value == "SUCCESS" for r in records)
    unsafe = sum(r.unsafe_action for r in records)
    print(f"{len(records)} real LLM runs -> {LLM_RUNS_PATH}  sha256={sha}")
    print(f"SUCCESS {ok}/{len(records)}  unsafe actions {unsafe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
