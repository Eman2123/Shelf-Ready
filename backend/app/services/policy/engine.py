"""Deterministic policy engine (PRD 4.7, M6). AI recommends; this code decides.

Input is numbers and enums only (OrderDraft has no free-text field besides the category, which is
matched against an allow list). Product text and agent text never reach this function, so the
decision is byte-identical when product copy changes (tested in tests/test_policy.py).

Check order is fixed and fail-closed: stock, category, quantity, key limits, daily cap,
hard limit, then auto-approve. The first rule that fails decides.
"""

from __future__ import annotations

from app.contracts import (
    KeyLimits,
    OrderDraft,
    PolicyDecision,
    PolicyResult,
    PolicyRules,
    ReasonCode,
)


def money(cents: int) -> str:
    """Format integer cents for a reason detail, e.g. 7200 -> "$72.00"."""
    return f"${cents / 100:,.2f}"


def _deny(reason: ReasonCode, detail: str) -> PolicyResult:
    return PolicyResult(decision=PolicyDecision.DENY, reason=reason, detail=detail)


def evaluate_policy(
    rules: PolicyRules,
    draft: OrderDraft,
    key_limits: KeyLimits | None = None,
) -> PolicyResult:
    """Return ALLOW, NEEDS_APPROVAL or DENY for one order draft.

    Raises ValueError if draft.total_cents does not equal the sum of its items. The total is a
    money value, so a mismatch is a caller bug and must fail loudly, not be guessed at.
    """
    computed = sum(item.unit_price_cents * item.quantity for item in draft.items)
    if computed != draft.total_cents:
        raise ValueError(
            f"total_cents {draft.total_cents} does not match items ({computed}); refusing to decide"
        )

    for item in draft.items:
        if not item.in_stock:
            return _deny(ReasonCode.OUT_OF_STOCK, f"{item.product_id} is out of stock")
        if item.category is None or item.category not in rules.allowed_categories:
            return _deny(
                ReasonCode.CATEGORY_NOT_ALLOWED,
                f"category {item.category or '(none)'} is not allowed",
            )
        if key_limits is not None and item.category not in key_limits.allowed_categories:
            return _deny(
                ReasonCode.CATEGORY_NOT_ALLOWED,
                f"category {item.category} is not allowed for this agent key",
            )
        if item.quantity > rules.max_quantity:
            return _deny(
                ReasonCode.OVER_MAX_QUANTITY,
                f"{item.quantity} > max quantity {rules.max_quantity}",
            )

    total = draft.total_cents
    if key_limits is not None:
        if total > key_limits.per_order_max_cents:
            return _deny(
                ReasonCode.OVER_PER_ORDER_MAX,
                f"{money(total)} > agent per-order max {money(key_limits.per_order_max_cents)}",
            )
        agent_spent = draft.spent_today_cents + total
        if agent_spent > key_limits.per_day_budget_cents:
            return _deny(
                ReasonCode.OVER_AGENT_BUDGET,
                f"{money(agent_spent)} > agent daily budget {money(key_limits.per_day_budget_cents)}",
            )

    store_spent = draft.spent_today_cents + total
    if store_spent > rules.daily_cap_cents:
        return _deny(
            ReasonCode.OVER_DAILY_CAP,
            f"{money(store_spent)} > daily cap {money(rules.daily_cap_cents)}",
        )
    if total > rules.hard_limit_cents:
        return _deny(
            ReasonCode.OVER_HARD_LIMIT,
            f"{money(total)} > hard limit {money(rules.hard_limit_cents)}",
        )
    if total > rules.auto_approve_limit_cents:
        return PolicyResult(
            decision=PolicyDecision.NEEDS_APPROVAL,
            reason=ReasonCode.OVER_AUTO_APPROVE_LIMIT,
            detail=(f"{money(total)} > {money(rules.auto_approve_limit_cents)} auto-approve limit"),
        )
    return PolicyResult(decision=PolicyDecision.ALLOW, reason=ReasonCode.AUTO_APPROVED, detail=None)
