"""Run one task in both modes and print the two traces side by side (for demo and video).

python -m app.scripts.record_run A2
"""

from __future__ import annotations

import argparse
import json

from app.contracts import AgentMode
from app.services.benchmark.runner import run_one
from app.services.benchmark.tasks import TASKS_BY_ID


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id", choices=sorted(TASKS_BY_ID))
    args = ap.parse_args(argv)
    spec = TASKS_BY_ID[args.task_id]
    print(f"{spec.task.id}  {spec.task.prompt}\nexpected: {spec.task.expected.value}\n")
    for mode in (AgentMode.BEFORE, AgentMode.AFTER):
        rec = run_one(spec, mode, 1)
        run = rec.run
        print(f"--- {mode.value}  {run.agent_config}")
        for s in run.steps:
            print(f"  {s.index + 1}. {s.tool} ok={s.ok} html_bytes={s.html_bytes}")
            print(f"     in : {json.dumps(s.input)[:110]}")
            print(f"     out: {json.dumps(s.output)[:110]}")
        print(f"  => {run.outcome.value}  tool_calls={run.tool_calls} html_bytes={run.html_bytes}")
        if run.fail_reason:
            print(f"     why: {run.fail_reason}")
        print()


if __name__ == "__main__":
    main()
