"""Record real LLM benchmark runs. Refuses to run without an API key and model.

    python -m app.scripts.record_llm_runs --tasks A2,B4 --k 1
    python -m app.scripts.record_llm_runs --check        # config check only, no model call

Set AI_PROVIDER and the matching *_API_KEY / *_MODEL in backend/.env (never commit it).
"""

from __future__ import annotations

import argparse
import sys

from app.services.ai.client import ChatClient, LLMError, load_llm_config
from app.services.benchmark.llm_runner import LLM_RUNS_PATH, run_llm_suite_resumable


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--tasks", default="", help="comma list, e.g. A2,B4 (default: all 12)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ping", action="store_true", help="one tiny real call, then stop")
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
    if args.ping:
        try:
            reply = client.chat([{"role": "user", "content": "Reply with the single word: ok"}])
        except LLMError as exc:
            print(f"LLM call failed: {exc}")
            return 1
        print(f"PING OK model={client.last_model} reply={reply.content!r}")
        return 0
    ids = [t.strip() for t in args.tasks.split(",") if t.strip()] or None
    runs, error, sha = run_llm_suite_resumable(client, args.k, ids)
    ok = sum(r["run"]["outcome"] == "SUCCESS" for r in runs)
    unsafe = sum(bool(r["unsafe_action"]) for r in runs)
    print(f"{len(runs)} real LLM runs saved in {LLM_RUNS_PATH}  sha256={sha}")
    print(f"SUCCESS {ok}/{len(runs)}  unsafe actions {unsafe}")
    if error:
        print(f"STOPPED: {error}")
        print("Saved runs are kept. Run the same command again to continue the missing ones.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
