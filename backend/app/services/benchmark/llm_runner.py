"""Run and store REAL LLM benchmark runs, apart from the scripted record.

Written to data/benchmark/llm_runs.json, with the model id on every run. Never touches runs.json,
so the "no LLM" fingerprint and the Report numbers stay as they are. Needs an API key.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.contracts import AgentMode, AgentRun
from app.services.agent.llm_agent import agent_config, run_llm
from app.services.ai.client import ChatClient, LLMError
from app.services.benchmark.evaluate import evaluate
from app.services.benchmark.runner import RunRecord, _fresh_store
from app.services.benchmark.tasks import TASKS, TASKS_BY_ID
from app.services.fixtures.demo_store import DEFAULT_POLICY

LLM_RUNS_PATH = Path(__file__).resolve().parents[3] / "data" / "benchmark" / "llm_runs.json"


def run_llm_one(client: ChatClient, task_id: str, replica: int) -> RunRecord:
    spec = TASKS_BY_ID[task_id]
    service, guard = _fresh_store(spec, DEFAULT_POLICY)
    result = run_llm(spec, service, guard, client)
    answered_by = client.last_model or client.config.model  # an alias like *-latest can move
    outcome, reason, unsafe = evaluate(spec, result.final)
    run = AgentRun(
        id=f"run_{task_id}_llm_{replica}",
        mode=AgentMode.AFTER,
        agent_config=agent_config(answered_by, client.temperature_note),
        task_id=task_id,
        steps=result.steps,
        outcome=outcome,
        fail_reason=reason,
        duration_ms=result.duration_ms,
    )
    return RunRecord(run=run, replica=replica, final=result.final, unsafe_action=unsafe)


def _body(client: ChatClient, k: int, runs: list[dict]) -> dict:
    return {
        "label": "real LLM runs (not the scripted no-LLM record)",
        "provider": client.config.provider,
        "requested_model": client.config.model,
        "temperature": 0 if client.send_temperature else "provider default (param rejected)",
        "k": k,
        "recorded_at": datetime.now(UTC).isoformat(),
        "runs": runs,
    }


def _write(body: dict, path: Path) -> str:
    payload = json.dumps(body, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)
    return hashlib.sha256(payload.encode()).hexdigest()


def load_saved_runs(path: Path = LLM_RUNS_PATH) -> list[dict]:
    if not path.exists():
        return []
    return list(json.loads(path.read_text()).get("runs", []))


def run_llm_suite_resumable(
    client: ChatClient,
    k: int = 1,
    task_ids: list[str] | None = None,
    path: Path = LLM_RUNS_PATH,
    runner=run_llm_one,
) -> tuple[list[dict], str | None, str | None]:
    """Run missing (task, replica) pairs and save after EVERY run.

    Runs already in the file are kept and skipped, so a quota error in the middle loses nothing
    and running again continues where it stopped. Returns (all saved runs, error text or None,
    sha256 of the saved file). Every run keeps the model id it was answered by.
    """
    runs = load_saved_runs(path)
    done = {r["run"]["id"] for r in runs}
    ids = task_ids or [t.task.id for t in TASKS]
    sha = None
    for task_id in ids:
        for replica in range(1, k + 1):
            if f"run_{task_id}_llm_{replica}" in done:
                continue
            try:
                rec = runner(client, task_id, replica)
            except LLMError as exc:
                return runs, str(exc), sha
            runs.append(rec.model_dump(mode="json"))
            sha = _write(_body(client, k, runs), path)
    return runs, None, sha


def run_llm_suite(
    client: ChatClient, k: int = 1, task_ids: list[str] | None = None
) -> list[RunRecord]:
    ids = task_ids or [t.task.id for t in TASKS]
    return [run_llm_one(client, i, r) for i in ids for r in range(1, k + 1)]


def save_llm_runs(
    records: list[RunRecord], client: ChatClient, k: int, path: Path = LLM_RUNS_PATH
) -> str:
    body = {
        "label": "real LLM runs (not the scripted no-LLM record)",
        "provider": client.config.provider,
        "requested_model": client.config.model,
        "temperature": 0 if client.send_temperature else "provider default (param rejected)",
        "k": k,
        "recorded_at": datetime.now(UTC).isoformat(),
        "runs": [r.model_dump(mode="json") for r in records],
    }
    payload = json.dumps(body, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)
    return hashlib.sha256(payload.encode()).hexdigest()
