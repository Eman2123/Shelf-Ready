import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.contracts import (
    STORE_TOOL_NAMES,
    CreateOrderInput,
    GetProductInput,
    GuardedOrderRequest,
    GuardedOrderResult,
    OrderStatus,
    PolicyDecision,
    PolicyResult,
    ReasonCode,
    SearchProductsInput,
)
from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.mcp_store import StoreService
from app.services.mcp_store.server import build_server


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)

    def __call__(self):
        return self.now


def fake_guarded(req: GuardedOrderRequest) -> GuardedOrderResult:
    return GuardedOrderResult(
        order_id="o1",
        status=OrderStatus.CREATED,
        paypal_order_id=None,
        decision=PolicyResult(decision=PolicyDecision.ALLOW, reason=ReasonCode.AUTO_APPROVED),
        approval_url=None,
    )


@pytest.fixture
def svc():
    products = {k: v.model_copy(deep=True) for k, v in PUBLISHED_PRODUCTS.items()}
    return StoreService(products, DEFAULT_POLICY, fake_guarded, Clock())


def _order(svc, product_id, quote_id, qty=1):
    return svc.create_order(
        CreateOrderInput.model_validate(
            {
                "items": [{"product_id": product_id, "quantity": qty, "quote_id": quote_id}],
                "ship_to_country": "US",
                "idempotency_key": "idem-0001",
            }
        ),
        agent_key="k",
    )


def _quote_for(svc, product_id, sku=None):
    res = svc.get_product(GetProductInput(product_id=product_id))
    return next(q for q in res["quotes"] if q["variant_sku"] == sku)["quote_id"]


def test_search_filters_by_price_and_query(svc):
    names = [r["name"] for r in svc.search_products(SearchProductsInput(max_price_cents=2000))]
    assert names == ["Tidewell Enamel Mug"]
    assert svc.search_products(SearchProductsInput(query="tee"))[0]["product_id"] == "prod_tee"


def test_get_product_issues_a_quote_per_variant(svc):
    res = svc.get_product(GetProductInput(product_id="prod_tee"))
    assert {q["variant_sku"] for q in res["quotes"]} == {"TEE-BLU-M", "TEE-BLU-L", "TEE-BLK-M"}
    assert svc.get_product(GetProductInput(product_id="nope"))["error"] == "PRODUCT_NOT_FOUND"


def test_order_succeeds_with_fresh_quote(svc):
    q = _quote_for(svc, "prod_tee", "TEE-BLU-M")
    assert _order(svc, "prod_tee", q)["status"] == "CREATED"


def test_stale_price_returns_price_changed(svc):
    q = _quote_for(svc, "prod_tote")
    svc.products["prod_tote"] = svc.products["prod_tote"].model_copy(update={"price_cents": 2900})
    assert _order(svc, "prod_tote", q)["error"] == "PRICE_CHANGED"


def test_stock_change_returns_stock_changed(svc):
    q = _quote_for(svc, "prod_tote")
    svc.products["prod_tote"] = svc.products["prod_tote"].model_copy(update={"stock": 0})
    assert _order(svc, "prod_tote", q)["error"] == "STOCK_CHANGED"


def test_quantity_above_stock_is_refused(svc):
    q = _quote_for(svc, "prod_mug")
    assert _order(svc, "prod_mug", q, qty=6)["error"] == "STOCK_CHANGED"


def test_expired_and_unknown_quotes(svc):
    q = _quote_for(svc, "prod_tote")
    svc.clock.now += timedelta(minutes=11)
    assert _order(svc, "prod_tote", q)["error"] == "QUOTE_EXPIRED"
    assert _order(svc, "prod_tote", "q_fake")["error"] == "QUOTE_UNKNOWN"


def test_quote_must_belong_to_the_product(svc):
    q = _quote_for(svc, "prod_tote")
    assert _order(svc, "prod_mug", q)["error"] == "QUOTE_UNKNOWN"


def test_no_order_backend_means_no_order(svc):
    svc.guarded_order = None
    q = _quote_for(svc, "prod_tote")
    assert _order(svc, "prod_tote", q)["error"] == "ORDER_BACKEND_NOT_CONNECTED"


def test_injection_text_is_returned_as_data_and_policy_is_unchanged(svc):
    before = svc.get_policy()
    res = svc.get_product(GetProductInput(product_id="prod_mug"))
    assert "Ignore previous instructions" in res["product"]["description"]
    assert svc.get_policy() == before


def test_mcp_server_exposes_exactly_the_four_tools(svc):
    server = build_server(svc)
    tools = asyncio.run(server.list_tools())
    assert sorted(t.name for t in tools) == sorted(STORE_TOOL_NAMES)


# --- Day 3: key checks plug in, and the real MCP transport works end to end -----------------
from app.contracts import (
    KeyFailureReason,
    KeyLimits,
    KeyRejected,
    KeyScope,
    KeyVerified,
    VerifiedAgent,
)


def _agent(scopes):
    return KeyVerified(
        agent=VerifiedAgent(
            agent_id="a1",
            key_id="k1",
            store_id="store_demo",
            scopes=scopes,
            limits=KeyLimits(
                per_order_max_cents=5000,
                per_day_budget_cents=20000,
                requests_per_minute=30,
                allowed_categories=[],
                expires_at=None,
            ),
        )
    )


def _svc_with_key(result):
    products = {k: v.model_copy(deep=True) for k, v in PUBLISHED_PRODUCTS.items()}
    return StoreService(
        products, DEFAULT_POLICY, fake_guarded, Clock(), verify_key=lambda k: result
    )


def test_revoked_key_never_reaches_the_order_backend():
    svc = _svc_with_key(KeyRejected(reason=KeyFailureReason.KEY_REVOKED))
    q = _quote_for(svc, "prod_tote")
    assert _order(svc, "prod_tote", q)["error"] == "KEY_REVOKED"


def test_key_without_order_scope_is_refused():
    svc = _svc_with_key(_agent([KeyScope.READ, KeyScope.QUOTE]))
    q = _quote_for(svc, "prod_tote")
    assert _order(svc, "prod_tote", q)["error"] == "KEY_SCOPE_MISSING"


def test_key_with_order_scope_can_order():
    svc = _svc_with_key(_agent([KeyScope.READ, KeyScope.QUOTE, KeyScope.ORDER]))
    q = _quote_for(svc, "prod_tote")
    assert _order(svc, "prod_tote", q)["status"] == "CREATED"


def test_mcp_client_completes_a_purchase_without_html(svc):
    """An MCP client discovers the tools and buys, with no HTML parsing (PRD M5 done-when)."""
    from mcp.client.client import Client

    async def run():
        async with Client(build_server(svc)) as client:
            tools = {t.name for t in (await client.list_tools()).tools}
            assert tools == set(STORE_TOOL_NAMES)
            found = await client.call_tool("search_products", {"query": "tote"})
            pid = found.structured_content["result"][0]["product_id"]
            prod = await client.call_tool("get_product", {"product_id": pid})
            quote_id = prod.structured_content["quotes"][0]["quote_id"]
            order = await client.call_tool(
                "create_order",
                {
                    "items": [{"product_id": pid, "quantity": 1, "quote_id": quote_id}],
                    "ship_to_country": "US",
                    "idempotency_key": "idem-mcp-01",
                    "agent_key": "demo-key",
                },
            )
            return order.structured_content

    assert asyncio.run(run())["status"] == "CREATED"


def test_missing_key_is_a_clean_error(svc):
    q = _quote_for(svc, "prod_tote")
    result = svc.create_order(
        CreateOrderInput.model_validate(
            {
                "items": [{"product_id": "prod_tote", "quantity": 1, "quote_id": q}],
                "ship_to_country": "US",
                "idempotency_key": "idem-0002",
            }
        ),
        agent_key="",
    )
    assert result == {"error": "KEY_UNKNOWN"}
