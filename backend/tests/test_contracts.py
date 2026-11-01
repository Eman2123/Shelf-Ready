from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.contracts import (
    GENESIS_HASH,
    SCORE_WEIGHTS,
    STORE_TOOL_NAMES,
    AgentMode,
    AgentRun,
    AgentRunOutcome,
    AgentStep,
    FixEvidence,
    FixMethod,
    FixRecord,
    FixStatus,
    GuardedOrderRequest,
    Product,
    Quote,
    RunEvent,
    compute_quote_hash,
    hash_output,
)


def _product(**over):
    base = {
        "id": "p1",
        "store_id": "s1",
        "paypal_product_id": None,
        "name": "Tee",
        "description": "d",
        "price_cents": 2000,
        "price_text": "$20.00",
        "currency": "USD",
        "stock": 3,
        "variants": [],
        "shipping": None,
        "returns": None,
        "sku": None,
        "gtin": None,
        "images": [],
        "category": "apparel",
        "home_url": None,
        "checkout_requires_human": False,
        "source_hash": "h",
    }
    base.update(over)
    return Product(**base)


def test_product_ok_and_money_is_integer_cents():
    assert _product().price_cents == 2000
    with pytest.raises(ValidationError):
        _product(price_cents=-1)
    with pytest.raises(ValidationError):
        _product(price_cents=20.5)


def test_product_rejects_bad_currency_and_unknown_fields():
    with pytest.raises(ValidationError):
        _product(currency="usd")
    with pytest.raises(ValidationError):
        _product(surprise="x")


def test_score_weights_total_100():
    assert sum(SCORE_WEIGHTS.values()) == 100


def test_store_tool_names_are_the_four_mcp_tools():
    assert STORE_TOOL_NAMES == ("search_products", "get_product", "get_policy", "create_order")


def test_applied_fix_needs_evidence():
    with pytest.raises(ValidationError):
        FixRecord(
            id="f",
            product_id="p",
            field="x",
            old_value=None,
            new_value="v",
            status=FixStatus.APPLIED,
            evidence=None,
        )


def test_ai_extract_needs_snippet():
    ev = FixEvidence(
        source_field="description", source_snippet="  ", method=FixMethod.AI_EXTRACT, confidence=0.5
    )
    with pytest.raises(ValidationError):
        FixRecord(
            id="f",
            product_id="p",
            field="x",
            old_value=None,
            new_value="v",
            status=FixStatus.APPLIED,
            evidence=ev,
        )


def test_seller_input_fix_has_no_value_yet():
    with pytest.raises(ValidationError):
        FixRecord(
            id="f",
            product_id="p",
            field="x",
            old_value=None,
            new_value="v",
            status=FixStatus.NEEDS_SELLER_INPUT,
            evidence=None,
        )


def test_quote_hash_is_deterministic_and_detects_price_change():
    h1 = compute_quote_hash("p1", None, 2000, "USD", 3)
    assert h1 == compute_quote_hash("p1", None, 2000, "USD", 3)
    assert h1 != compute_quote_hash("p1", None, 2100, "USD", 3)
    assert h1 != compute_quote_hash("p1", None, 2000, "USD", 2)
    q = Quote(
        quote_id="q1",
        product_id="p1",
        variant_sku=None,
        unit_price_cents=2000,
        currency="USD",
        stock=3,
        hash=h1,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    assert q.is_consistent()
    assert not q.model_copy(update={"unit_price_cents": 1}).is_consistent()


def test_order_items_require_a_quote_id():
    with pytest.raises(ValidationError):
        GuardedOrderRequest(
            agent_key="k",
            ship_to_country="US",
            idempotency_key="idem-0001",
            items=[{"product_id": "p1", "quantity": 1}],
        )


def test_agent_run_totals():
    steps = [
        AgentStep(index=0, tool="fetch_page", input={}, output={}, ok=True, html_bytes=1000),
        AgentStep(index=1, tool="fetch_page", input={}, output={}, ok=True, html_bytes=500),
    ]
    run = AgentRun(
        id="r",
        mode=AgentMode.BEFORE,
        agent_config="m@v t=0",
        task_id="A2",
        steps=steps,
        outcome=AgentRunOutcome.FAILED,
        fail_reason="guessed",
        duration_ms=1,
    )
    assert run.tool_calls == 2 and run.html_bytes == 1500


def test_run_event_chain_changes_when_anything_changes():
    e1 = RunEvent(
        id="e1",
        type="audit_run",
        inputs=[],
        output_hash=hash_output({"a": 1}),
        prev_hash=GENESIS_HASH,
    )
    e2 = RunEvent(
        id="e2",
        type="fix_version",
        inputs=["e1"],
        output_hash=hash_output({"b": 2}),
        prev_hash=e1.link_hash(),
    )
    assert e2.prev_hash == e1.link_hash()
    tampered = e1.model_copy(update={"output_hash": hash_output({"a": 2})})
    assert tampered.link_hash() != e1.link_hash()
    assert hash_output({"a": 1, "b": 2}) == hash_output({"b": 2, "a": 1})
