"""Policy engine contracts. The AI never decides; only code evaluates these."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from .common import Cents, Contract, CurrencyCode, Id


class PolicyRules(Contract):
    """total <= auto_approve -> ALLOW; <= hard_limit -> NEEDS_APPROVAL; above -> DENY."""

    auto_approve_limit_cents: Cents
    hard_limit_cents: Cents
    daily_cap_cents: Cents
    max_quantity: Annotated[int, Field(ge=1)]
    allowed_categories: list[str]


class OrderItemDraft(Contract):
    product_id: Id
    variant_sku: str | None
    quantity: Annotated[int, Field(ge=1)]
    unit_price_cents: Cents
    category: str | None
    in_stock: bool


class OrderDraft(Contract):
    store_id: Id
    agent_id: Id
    currency: CurrencyCode
    items: Annotated[list[OrderItemDraft], Field(min_length=1)]
    total_cents: Cents
    # what this agent has already spent today in this store, for the daily cap
    spent_today_cents: Cents


class PolicyDecision(StrEnum):
    ALLOW = "ALLOW"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    DENY = "DENY"


class ReasonCode(StrEnum):
    # policy rules
    AUTO_APPROVED = "AUTO_APPROVED"
    OVER_AUTO_APPROVE_LIMIT = "OVER_AUTO_APPROVE_LIMIT"
    OVER_HARD_LIMIT = "OVER_HARD_LIMIT"
    OVER_DAILY_CAP = "OVER_DAILY_CAP"
    OVER_MAX_QUANTITY = "OVER_MAX_QUANTITY"
    CATEGORY_NOT_ALLOWED = "CATEGORY_NOT_ALLOWED"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    # agent key checks (same codes as KeyFailureReason)
    KEY_UNKNOWN = "KEY_UNKNOWN"
    KEY_REVOKED = "KEY_REVOKED"
    KEY_EXPIRED = "KEY_EXPIRED"
    KEY_SCOPE_MISSING = "KEY_SCOPE_MISSING"
    RATE_LIMITED = "RATE_LIMITED"
    OVER_AGENT_BUDGET = "OVER_AGENT_BUDGET"
    OVER_PER_ORDER_MAX = "OVER_PER_ORDER_MAX"
    # quote binding (see mcp.QuoteError)
    PRICE_CHANGED = "PRICE_CHANGED"
    STOCK_CHANGED = "STOCK_CHANGED"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"


class PolicyResult(Contract):
    decision: PolicyDecision
    reason: ReasonCode
    detail: str | None = None
