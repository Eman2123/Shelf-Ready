"""Agent key contracts. A revoked key must fail on the very next request."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from .common import Cents, Contract, Id


class KeyScope(StrEnum):
    READ = "read"
    QUOTE = "quote"
    ORDER = "order"


class KeyLimits(Contract):
    per_order_max_cents: Cents
    per_day_budget_cents: Cents
    requests_per_minute: Annotated[int, Field(ge=1)]
    allowed_categories: list[str]
    expires_at: datetime | None


class VerifiedAgent(Contract):
    agent_id: Id
    key_id: Id
    store_id: Id
    scopes: list[KeyScope]
    limits: KeyLimits


class KeyFailureReason(StrEnum):
    KEY_UNKNOWN = "KEY_UNKNOWN"
    KEY_REVOKED = "KEY_REVOKED"
    KEY_EXPIRED = "KEY_EXPIRED"
    KEY_SCOPE_MISSING = "KEY_SCOPE_MISSING"
    RATE_LIMITED = "RATE_LIMITED"
    OVER_AGENT_BUDGET = "OVER_AGENT_BUDGET"
    OVER_PER_ORDER_MAX = "OVER_PER_ORDER_MAX"


class KeyVerified(Contract):
    ok: Literal[True] = True
    agent: VerifiedAgent


class KeyRejected(Contract):
    ok: Literal[False] = False
    reason: KeyFailureReason


KeyVerification = Annotated[KeyVerified | KeyRejected, Field(discriminator="ok")]
