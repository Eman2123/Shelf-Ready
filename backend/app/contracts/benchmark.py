"""Benchmark and buyer agent run contracts (PRD 4.5, M9/M10)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from .common import Contract, Id


class ExpectedOutcome(StrEnum):
    """What a correct run ends with. Success = expected outcome AND policy respected."""

    ORDER_CREATED = "ORDER_CREATED"
    REPORTED_OUT_OF_STOCK = "REPORTED_OUT_OF_STOCK"
    STOPPED_FOR_APPROVAL = "STOPPED_FOR_APPROVAL"
    DENIED_BY_POLICY = "DENIED_BY_POLICY"
    REPORTED_CANNOT_SHIP = "REPORTED_CANNOT_SHIP"
    INJECTION_IGNORED = "INJECTION_IGNORED"
    ASKED_CLARIFYING_QUESTION = "ASKED_CLARIFYING_QUESTION"
    PRICE_CHANGE_DETECTED = "PRICE_CHANGE_DETECTED"


class BenchmarkTask(Contract):
    id: Id
    title: str
    # the exact task text given to the agent, identical in BEFORE and AFTER mode
    prompt: str
    expected: ExpectedOutcome
    # what the check looks at, written down so the benchmark is honest and repeatable
    success_criteria: str


class AgentMode(StrEnum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"


class AgentStep(Contract):
    index: Annotated[int, Field(ge=0)]
    tool: str
    input: Any
    output: Any
    ok: bool
    # bytes of HTML the step read (fetch_page only); always 0 in AFTER mode
    html_bytes: Annotated[int, Field(ge=0)] = 0


class AgentRunOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    WRONG_RESULT = "WRONG_RESULT"
    POLICY_VIOLATION = "POLICY_VIOLATION"


class AgentRun(Contract):
    id: Id
    mode: AgentMode
    # model + version, temperature 0, recorded for every run
    agent_config: str
    task_id: Id
    steps: list[AgentStep]
    outcome: AgentRunOutcome
    fail_reason: str | None
    duration_ms: Annotated[int, Field(ge=0)]

    @property
    def tool_calls(self) -> int:
        return len(self.steps)

    @property
    def html_bytes(self) -> int:
        return sum(s.html_bytes for s in self.steps)
