"""Benchmark runner: 12 tasks x 2 modes x k runs, stored per run, with replay (PRD 4.5, M9/M10)."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.contracts import AgentMode, AgentRun, AgentStep, Contract, PolicyRules
from app.services.benchmark.agents import AFTER_CONFIG, BEFORE_CONFIG, run_after, run_before
from app.services.benchmark.evaluate import evaluate
from app.services.benchmark.guard import BenchmarkGuard
from app.services.benchmark.tasks import TASKS, TASKS_BY_ID, TaskSpec
from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.mcp_store.service import StoreService

DEFAULT_K = 3
BENCH_NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "benchmark" / "runs.json"


class RunRecord(Contract):
    run: AgentRun
    replica: int
    # what the run ended with, as the agent reported it
    final: dict[str, Any]
    unsafe_action: bool


def _fresh_store(spec: TaskSpec, rules: PolicyRules) -> tuple[StoreService, BenchmarkGuard]:
    products = {k: v.model_copy(deep=True) for k, v in PUBLISHED_PRODUCTS.items()}
    counter = itertools.count(1)
    service = StoreService(
        products,
        rules,
        clock=lambda: BENCH_NOW,  # fixed time: quote expiry is part of the recorded output
        quote_id_factory=lambda: f"q_{spec.task.id}_{next(counter)}",
    )
    guard = BenchmarkGuard(service, spent_today_cents=spec.scenario.spent_today_cents)
    service.guarded_order, service.verify_key = guard.guarded_order, guard.verify_key
    return service, guard


def run_one(
    spec: TaskSpec, mode: AgentMode, replica: int, rules: PolicyRules = DEFAULT_POLICY
) -> RunRecord:
    if mode == AgentMode.BEFORE:
        result, config = run_before(spec), BEFORE_CONFIG
    else:
        service, guard = _fresh_store(spec, rules)
        result, config = run_after(spec, service, guard), AFTER_CONFIG
    outcome, reason, unsafe = evaluate(spec, result.final)
    steps = result.steps
    if mode == AgentMode.BEFORE and unsafe:
        # the recorded intent is the unsafe action; mark it so the UI shows it
        steps = [
            s.model_copy(update={"ok": False}) if s.tool == "record_intent" else s for s in steps
        ]
    run = AgentRun(
        id=f"run_{spec.task.id}_{mode.value.lower()}_{replica}",
        mode=mode,
        agent_config=config,
        task_id=spec.task.id,
        steps=steps,
        outcome=outcome,
        fail_reason=reason,
        duration_ms=result.duration_ms,
    )
    return RunRecord(run=run, replica=replica, final=result.final, unsafe_action=unsafe)


def run_suite(k: int = DEFAULT_K, task_ids: list[str] | None = None) -> list[RunRecord]:
    specs = [TASKS_BY_ID[i] for i in task_ids] if task_ids else list(TASKS)
    return [
        run_one(spec, mode, r)
        for spec in specs
        for mode in (AgentMode.BEFORE, AgentMode.AFTER)
        for r in range(1, k + 1)
    ]


def metrics(records: list[RunRecord]) -> dict[str, dict[str, Any]]:
    """Per mode: completion (A), safe-stop (B), unsafe actions, wrong purchases, steps, per task k/n."""
    out: dict[str, dict[str, Any]] = {}
    for mode in AgentMode:
        rs = [r for r in records if r.run.mode == mode]
        a = [r for r in rs if TASKS_BY_ID[r.run.task_id].group == "A"]
        b = [r for r in rs if TASKS_BY_ID[r.run.task_id].group == "B"]
        ok = lambda r: r.run.outcome.value == "SUCCESS"
        per_task: dict[str, dict[str, Any]] = {}
        for r in rs:
            cell = per_task.setdefault(r.run.task_id, {"success": 0, "runs": 0, "run_ids": []})
            cell["success"] += ok(r)
            cell["runs"] += 1
            cell["run_ids"].append(r.run.id)
        out[mode.value] = {
            "completion": {"success": sum(map(ok, a)), "runs": len(a)},
            "safe_stop": {"success": sum(map(ok, b)), "runs": len(b)},
            "unsafe_actions": sum(r.unsafe_action for r in rs),
            "wrong_purchases": sum(1 for r in a if r.run.outcome.value == "WRONG_RESULT"),
            "avg_steps": round(sum(len(r.run.steps) for r in rs) / max(len(rs), 1), 2),
            "html_bytes": sum(r.run.html_bytes for r in rs),
            "per_task": per_task,
        }
    return out


def save_runs(records: list[RunRecord], path: Path = DATA_PATH, k: int = DEFAULT_K) -> str:
    body = {
        "k": k,
        "temperature": "n/a (scripted, deterministic)",
        "runs": [r.model_dump(mode="json") for r in records],
    }
    payload = json.dumps(body, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)
    return hashlib.sha256(payload.encode()).hexdigest()


def load_runs(path: Path = DATA_PATH) -> list[RunRecord]:
    """Replay mode: re-read recorded runs exactly as stored; nothing is executed."""
    return [RunRecord.model_validate(r) for r in json.loads(path.read_text())["runs"]]


__all__ = [
    "DATA_PATH",
    "AgentStep",
    "RunRecord",
    "copy",
    "load_runs",
    "metrics",
    "run_one",
    "run_suite",
    "save_runs",
]
