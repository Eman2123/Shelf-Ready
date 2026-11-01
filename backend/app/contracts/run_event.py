"""RunEvent: one link of the hash chain behind the Readiness Receipt (PRD 4.4)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .common import Contract, Id

GENESIS_HASH = "0" * 64


def hash_output(output: Any) -> str:
    """Canonical SHA-256 of an output (sorted keys, no whitespace)."""
    raw = json.dumps(output, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


class RunEvent(Contract):
    id: Id
    # source_snapshot, audit_run, fix_version, published_data, agent_decision, quote,
    # policy_decision, paypal_order, webhook, final_result
    type: str
    inputs: list[Id]
    output_hash: str
    prev_hash: str

    def link_hash(self) -> str:
        raw = f"{self.id}|{self.type}|{','.join(self.inputs)}|{self.output_hash}|{self.prev_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()
