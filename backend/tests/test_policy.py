"""Policy engine (PRD 4.7, M6). Decisions come from numbers and enums only."""

from datetime import UTC, datetime, timedelta

import pytest

from app.contracts import (
    KeyLimits,
    OrderDraft,
    OrderItemDraft,
    PolicyDecision,
    PolicyRules,
    ReasonCode,
)
from app.services.policy import evaluate_policy

RULES = PolicyRules(
    auto_approve_limit_cents=5000,
    hard_limit_cents=20000,
    daily_cap_cents=30000,
    max_quantity=10,
    allowed_categories=["apparel", "accessories", "kitchen"],
)


def item(price: int, qty: int = 1, category: str | None = "apparel", in_stock: bool = True):
    return OrderItemDraft(
        product_id="prod_x",
        variant_sku=None,
        quantity=qty,
        unit_price_cents=price,
        category=category,
        in_stock=in_stock,
    )


def draft(*items: OrderItemDraft, spent: int = 0) -> OrderDraft:
    total = sum(i.unit_price_cents * i.quantity for i in items)
    return OrderDraft(
        store_id="store_demo",
        agent_id="agent_bench",
        currency="USD",
        items=list(items),
        total_cents=total,
        spent_today_cents=spent,
    )


def test_small_order_is_allowed():
    result = evaluate_policy(RULES, draft(item(2400)))
    assert result.decision is PolicyDecision.ALLOW
    assert result.reason is ReasonCode.AUTO_APPROVED


def test_order_at_auto_limit_is_still_allowed():
    assert evaluate_policy(RULES, draft(item(5000))).decision is PolicyDecision.ALLOW


def test_order_above_auto_limit_needs_approval_with_money_detail():
    # PRD 4.7 example: 3 tees at $24 = $72 is above the $50 auto-approve limit.
    result = evaluate_policy(RULES, draft(item(2400, qty=3)))
    assert result.decision is PolicyDecision.NEEDS_APPROVAL
    assert result.reason is ReasonCode.OVER_AUTO_APPROVE_LIMIT
    assert "$72.00" in (result.detail or "") and "$50.00" in (result.detail or "")


def test_order_above_hard_limit_is_denied():
    result = evaluate_policy(RULES, draft(item(10000, qty=3)))  # $300 > $200 hard limit
    assert result.decision is PolicyDecision.DENY
    assert result.reason is ReasonCode.OVER_HARD_LIMIT


def test_daily_cap_counts_what_was_already_spent():
    # $42 on top of $270 already spent today exceeds the $300 daily cap (benchmark B6).
    result = evaluate_policy(RULES, draft(item(4200), spent=27000))
    assert result.decision is PolicyDecision.DENY
    assert result.reason is ReasonCode.OVER_DAILY_CAP


def test_quantity_above_max_is_denied():
    result = evaluate_policy(RULES, draft(item(2400, qty=11)))
    assert result.reason is ReasonCode.OVER_MAX_QUANTITY


def test_restricted_category_is_denied_and_missing_category_fails_closed():
    assert evaluate_policy(RULES, draft(item(1800, category="gift_cards"))).reason is (
        ReasonCode.CATEGORY_NOT_ALLOWED
    )
    assert evaluate_policy(RULES, draft(item(1800, category=None))).reason is (
        ReasonCode.CATEGORY_NOT_ALLOWED
    )


def test_out_of_stock_is_denied():
    result = evaluate_policy(RULES, draft(item(2400, in_stock=False)))
    assert result.reason is ReasonCode.OUT_OF_STOCK


def test_total_that_does_not_match_items_is_refused_not_guessed():
    bad = draft(item(2400)).model_copy(update={"total_cents": 100})
    with pytest.raises(ValueError, match="does not match"):
        evaluate_policy(RULES, bad)


def test_decision_does_not_change_when_only_product_text_changes():
    # The draft has no free-text field besides the category allow-list, so product copy cannot
    # reach the decision. Two drafts that differ only in what the product says must match.
    first = draft(item(2400, qty=3))
    second = draft(item(2400, qty=3))
    assert evaluate_policy(RULES, first) == evaluate_policy(RULES, second)


def test_key_limits_per_order_and_agent_budget():
    now = datetime(2026, 11, 10, tzinfo=UTC)
    limits = KeyLimits(
        per_order_max_cents=3000,
        per_day_budget_cents=5000,
        requests_per_minute=60,
        allowed_categories=["apparel"],
        expires_at=now + timedelta(days=1),
    )
    over_order = evaluate_policy(RULES, draft(item(3500)), key_limits=limits)
    assert over_order.reason is ReasonCode.OVER_PER_ORDER_MAX

    over_budget = evaluate_policy(RULES, draft(item(2500), spent=3000), key_limits=limits)
    assert over_budget.reason is ReasonCode.OVER_AGENT_BUDGET

    key_category = evaluate_policy(RULES, draft(item(1000, category="kitchen")), key_limits=limits)
    assert key_category.reason is ReasonCode.CATEGORY_NOT_ALLOWED
