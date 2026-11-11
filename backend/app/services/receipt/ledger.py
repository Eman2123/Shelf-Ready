"""Hash-chained run events behind the Readiness Receipt (PRD 4.4).

Each RunEvent stores the hash of its output and the link hash of the event before it. Editing any
earlier event breaks every link after it, so verify_chain() finds the first broken position.
This is tamper-EVIDENT, not tamper-PROOF: whoever owns the database could rewrite the whole chain.
No blockchain and no signatures, on purpose.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.contracts import GENESIS_HASH, RunEvent, hash_output


@dataclass(frozen=True)
class ChainCheck:
    ok: bool
    checked: int
    broken_at: str | None  # id of the first event that fails, None when ok
    reason: str | None


class RunLedger:
    """Append-only chain. append() is the only way to add an event, so links are always right."""

    def __init__(self) -> None:
        self._events: list[RunEvent] = []

    @property
    def events(self) -> tuple[RunEvent, ...]:
        return tuple(self._events)

    @property
    def head_hash(self) -> str:
        return self._events[-1].link_hash() if self._events else GENESIS_HASH

    def append(self, event_id: str, event_type: str, inputs: list[str], output: Any) -> RunEvent:
        event = RunEvent(
            id=event_id,
            type=event_type,
            inputs=list(inputs),
            output_hash=hash_output(output),
            prev_hash=self.head_hash,
        )
        self._events.append(event)
        return event

    def verify(self, outputs: Mapping[str, Any] | None = None) -> ChainCheck:
        return verify_chain(self._events, outputs)


def verify_chain(
    events: Sequence[RunEvent],
    outputs: Mapping[str, Any] | None = None,
) -> ChainCheck:
    """Recompute the chain from the first event. If outputs are given, also recompute output hashes.

    outputs maps event id -> the raw output that was hashed. An event with no entry in outputs has
    its output hash checked only as a link (the output itself is not available to compare).
    """
    seen: set[str] = set()
    expected_prev = GENESIS_HASH
    for index, event in enumerate(events):
        if event.id in seen:
            return ChainCheck(False, index, event.id, "duplicate event id")
        seen.add(event.id)
        if event.prev_hash != expected_prev:
            return ChainCheck(
                False, index, event.id, "prev_hash does not match the event before it"
            )
        if (
            outputs is not None
            and event.id in outputs
            and (hash_output(outputs[event.id]) != event.output_hash)
        ):
            return ChainCheck(False, index, event.id, "output does not match output_hash")
        expected_prev = event.link_hash()
    return ChainCheck(True, len(events), None, None)


def ledger_from_runs(runs: Sequence[Any]) -> tuple[RunLedger, dict[str, Any]]:
    """Build the receipt chain over stored benchmark runs (one event per run, in stored order).

    Each run's output is its full record, so editing a recorded run later breaks the chain.
    Returns the ledger and the outputs map that verify() needs.
    """
    ledger = RunLedger()
    outputs: dict[str, Any] = {}
    for record in runs:
        output = record.model_dump(mode="json")
        event_id = record.run.id
        ledger.append(event_id, "agent_run", [record.run.task_id], output)
        outputs[event_id] = output
    return ledger, outputs
