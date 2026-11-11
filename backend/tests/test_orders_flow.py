"""Money-path tests against a mocked PayPal sandbox (no network, no credentials)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.contracts import (
    GuardedOrderItem,
    GuardedOrderRequest,
    KeyLimits,
    KeyScope,
    OrderStatus,
    PolicyDecision,
)
from app.db import Base, make_engine, make_session_factory
from app.db.repositories import OrderRepository, SqlKeyRepository
from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.keys import KeyStore
from app.services.mcp_store import StoreService
from app.services.orders import OrderService
from app.services.paypal import PayPalClient, PayPalOrders, PayPalSettings
from app.services.webhooks import WebhookHandler

BASE = "https://api-m.sandbox.paypal.com"


class FakePayPal:
    """Records every call and answers like the sandbox would."""

    def __init__(self, router: respx.MockRouter) -> None:
        self.router = router
        self.order_total = None  # lets a test make the witness disagree
        self.auth_status = "CREATED"
        self.capture_status = "COMPLETED"
        self.created: dict | None = None
        router.post(f"{BASE}/v1/oauth2/token").mock(
            return_value=httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        )
        self.create = router.post(f"{BASE}/v2/checkout/orders").mock(side_effect=self._create)
        self.get = router.get(url__regex=rf"{BASE}/v2/checkout/orders/.+").mock(
            side_effect=self._get
        )
        self.authorize = router.post(url__regex=rf"{BASE}/v2/checkout/orders/.+/authorize").mock(
            side_effect=self._authorize
        )
        self.capture = router.post(
            url__regex=rf"{BASE}/v2/payments/authorizations/.+/capture"
        ).mock(side_effect=self._capture)
        self.void = router.post(url__regex=rf"{BASE}/v2/payments/authorizations/.+/void").mock(
            return_value=httpx.Response(204)
        )
        self.refund = router.post(url__regex=rf"{BASE}/v2/payments/captures/.+/refund").mock(
            return_value=httpx.Response(201, json={"id": "REF-1", "status": "COMPLETED"})
        )

    def _create(self, request: httpx.Request) -> httpx.Response:
        self.created = json.loads(request.content)
        return httpx.Response(
            201,
            json={
                "id": "PP-ORDER-1",
                "status": "PAYER_ACTION_REQUIRED",
                "links": [{"rel": "payer-action", "href": "https://sandbox.paypal.com/approve/1"}],
            },
        )

    def _unit(self) -> dict:
        assert self.created is not None
        unit = self.created["purchase_units"][0]
        amount = dict(unit["amount"])
        if self.order_total is not None:
            amount["value"] = self.order_total
        return {
            "custom_id": unit["custom_id"],
            "amount": amount,
            "payments": {"authorizations": [{"id": "AUTH-1", "status": self.auth_status}]},
        }

    def _get(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"id": "PP-ORDER-1", "status": "COMPLETED", "purchase_units": [self._unit()]}
        )

    def _authorize(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201, json={"id": "PP-ORDER-1", "status": "COMPLETED", "purchase_units": [self._unit()]}
        )

    def _capture(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"id": "CAP-1", "status": self.capture_status})


class Env:
    def __init__(self, router: respx.MockRouter) -> None:
        engine = make_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.factory = make_session_factory(engine)
        self.keys = KeyStore(repository=SqlKeyRepository(self.factory))
        products = {k: v.model_copy(deep=True) for k, v in PUBLISHED_PRODUCTS.items()}
        self.store = StoreService(products, DEFAULT_POLICY, verify_key=self.keys.verify)
        self.repo = OrderRepository(self.factory)
        self.paypal = FakePayPal(router)
        client = PayPalClient(PayPalSettings("id", "secret", BASE, webhook_id="WH-1"))
        self.orders = OrderService(
            store=self.store,
            key_store=self.keys,
            repo=self.repo,
            paypal=PayPalOrders(client),
        )
        self.hooks = WebhookHandler(self.repo, self.orders)
        issued = self.keys.create_key(
            "agent-1",
            "store_demo",
            [KeyScope.READ, KeyScope.QUOTE, KeyScope.ORDER],
            KeyLimits(
                per_order_max_cents=100_000,
                per_day_budget_cents=100_000,
                requests_per_minute=100,
                allowed_categories=["apparel", "bags", "home"],
                expires_at=None,
            ),
        )
        self.raw_key = issued.raw_key
        self.key_id = issued.record.key_id

    def request(self, product_id: str, qty: int, idem: str = "idem-0001") -> GuardedOrderRequest:
        product = self.store.products[product_id]
        sku = product.variants[0].sku if product.variants else None
        quote = self.store.issue_quote(product, sku)
        assert quote is not None
        return GuardedOrderRequest(
            agent_key=self.raw_key,
            items=[
                GuardedOrderItem(
                    product_id=product_id, variant_sku=sku, quantity=qty, quote_id=quote.quote_id
                )
            ],
            ship_to_country="US",
            idempotency_key=idem,
        )


@pytest.fixture
def env():
    with respx.mock(assert_all_called=False) as router:
        yield Env(router)


def calls(route) -> int:
    return route.call_count


async def test_allowed_order_is_captured_after_buyer_approves(env):
    result = await env.orders.create(env.request("prod_mug", 2))  # $36.00 <= $50 auto-approve
    assert result.decision.decision is PolicyDecision.ALLOW
    assert result.status is OrderStatus.CREATED
    assert result.approval_url == "https://sandbox.paypal.com/approve/1"
    assert env.paypal.created["intent"] == "AUTHORIZE"
    assert env.paypal.created["purchase_units"][0]["amount"]["value"] == "36.00"

    outcome = await env.orders.on_buyer_approved("PP-ORDER-1")
    assert outcome == "CAPTURED"
    row = env.repo.get(result.order_id)
    assert row.status == "CAPTURED"
    assert row.capture_id == "CAP-1"
    assert env.keys.spent_today(env.key_id) == 3600
    body = json.loads(env.paypal.capture.calls.last.request.content)
    assert body["amount"]["value"] == "36.00" and body["final_capture"] is True
    assert "PayPal-Request-Id" in env.paypal.capture.calls.last.request.headers


async def test_over_auto_approve_waits_for_seller_then_captures(env):
    result = await env.orders.create(env.request("prod_tote", 3))  # $72.00 > $50
    assert result.status is OrderStatus.NEEDS_APPROVAL
    approval = env.repo.approval_for_order(result.order_id)
    assert approval.status == "PENDING"

    assert await env.orders.on_buyer_approved("PP-ORDER-1") == "WAITING_FOR_SELLER_APPROVAL"
    assert env.repo.get(result.order_id).status == "AUTHORIZED"
    assert calls(env.paypal.capture) == 0  # nothing captured without the seller

    done = await env.orders.approve(approval.id)
    assert done["action"] == "CAPTURED"
    assert env.repo.get(result.order_id).status == "CAPTURED"
    assert calls(env.paypal.capture) == 1


async def test_seller_can_approve_before_buyer_pays(env):
    result = await env.orders.create(env.request("prod_tote", 3))
    approval = env.repo.approval_for_order(result.order_id)
    assert (await env.orders.approve(approval.id))["action"] == "WAITING_FOR_BUYER"
    assert calls(env.paypal.capture) == 0
    assert await env.orders.on_buyer_approved("PP-ORDER-1") == "CAPTURED"


async def test_reject_voids_the_authorization(env):
    result = await env.orders.create(env.request("prod_tote", 3))
    await env.orders.on_buyer_approved("PP-ORDER-1")
    approval = env.repo.approval_for_order(result.order_id)
    assert (await env.orders.reject(approval.id))["status"] == "REJECTED"
    assert env.repo.get(result.order_id).status == "VOIDED"
    assert calls(env.paypal.void) == 1
    assert calls(env.paypal.capture) == 0
    # deciding twice does nothing
    assert (await env.orders.approve(approval.id))["status"] == "REJECTED"
    assert calls(env.paypal.capture) == 0


async def test_timeout_voids_pending_orders(env):
    result = await env.orders.create(env.request("prod_tote", 3))
    await env.orders.on_buyer_approved("PP-ORDER-1")
    from datetime import UTC, datetime, timedelta

    env.orders.clock = lambda: datetime.now(UTC) + timedelta(days=2)
    assert len(await env.orders.expire_pending()) == 1
    assert env.repo.get(result.order_id).status == "VOIDED"
    assert calls(env.paypal.void) == 1


async def test_over_hard_limit_never_reaches_paypal(env):
    result = await env.orders.create(env.request("prod_tote", 9))  # $216 > $200 hard limit
    assert result.status is OrderStatus.DENIED
    assert result.decision.decision is PolicyDecision.DENY
    assert calls(env.paypal.create) == 0
    assert result.paypal_order_id is None


async def test_same_idempotency_key_creates_one_paypal_order(env):
    first = await env.orders.create(env.request("prod_mug", 1, "idem-same-1"))
    second = await env.orders.create(env.request("prod_mug", 1, "idem-same-1"))
    assert first.order_id == second.order_id
    assert calls(env.paypal.create) == 1


async def test_revoked_key_is_denied_without_paypal(env):
    request = env.request("prod_mug", 1)
    env.keys.revoke(env.key_id)
    result = await env.orders.create(request)
    assert result.status is OrderStatus.DENIED
    assert result.decision.reason.value == "KEY_REVOKED"
    assert calls(env.paypal.create) == 0


async def test_witness_mismatch_voids_and_does_not_capture(env):
    result = await env.orders.create(env.request("prod_mug", 2))
    env.paypal.order_total = "1.00"  # PayPal says a different amount than we stored
    assert await env.orders.on_buyer_approved("PP-ORDER-1") == "WITNESS_MISMATCH"
    row = env.repo.get(result.order_id)
    assert row.status == "FAILED" and "total" in row.failure
    assert calls(env.paypal.capture) == 0
    assert calls(env.paypal.void) == 1


async def test_duplicate_webhook_does_not_double_capture(env):
    await env.orders.create(env.request("prod_mug", 2))
    event = {
        "id": "WH-EVT-1",
        "event_type": "CHECKOUT.ORDER.APPROVED",
        "resource": {"id": "PP-ORDER-1"},
    }
    assert await env.hooks.handle(event) == "CAPTURED"
    assert await env.hooks.handle(event) == "DUPLICATE"
    # a different event id for the same approval (PayPal re-sends) is also harmless
    again = {**event, "id": "WH-EVT-2"}
    assert await env.hooks.handle(again) == "ALREADY_PROCESSED"
    assert calls(env.paypal.capture) == 1
    assert env.keys.spent_today(env.key_id) == 3600


async def test_out_of_order_capture_event_never_moves_status_backwards(env):
    result = await env.orders.create(env.request("prod_mug", 2))
    done = {
        "id": "WH-EVT-9",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {"id": "CAP-1", "custom_id": result.order_id},
    }
    assert await env.hooks.handle(done) == "CAPTURED"
    late = {
        "id": "WH-EVT-10",
        "event_type": "CHECKOUT.ORDER.APPROVED",
        "resource": {"id": "PP-ORDER-1"},
    }
    assert await env.hooks.handle(late) == "ALREADY_PROCESSED"
    assert calls(env.paypal.authorize) == 0
    assert env.repo.get(result.order_id).status == "CAPTURED"
    assert env.keys.spent_today(env.key_id) == 3600  # counted once


async def test_failed_handler_releases_event_so_paypal_retry_works(env):
    await env.orders.create(env.request("prod_mug", 2))
    env.paypal.router.post(url__regex=rf"{BASE}/v2/checkout/orders/.+/authorize").mock(
        return_value=httpx.Response(500, json={"message": "boom"})
    )
    event = {
        "id": "WH-EVT-5",
        "event_type": "CHECKOUT.ORDER.APPROVED",
        "resource": {"id": "PP-ORDER-1"},
    }
    from app.services.paypal import PayPalError

    with pytest.raises(PayPalError):
        await env.hooks.handle(event)
    assert env.repo.list_events() == []  # released, so the retry is not seen as a duplicate


async def test_refund_after_capture(env):
    result = await env.orders.create(env.request("prod_mug", 2))
    await env.orders.on_buyer_approved("PP-ORDER-1")
    out = await env.orders.refund(result.order_id)
    assert out["status"] == "REFUNDED"
    assert env.repo.get(result.order_id).refund_id == "REF-1"
    assert (await env.orders.refund(result.order_id))["error"] == "NOT_REFUNDABLE"


async def test_agent_cannot_choose_the_price(env):
    """The charged amount comes from the stored quote, never from the request."""
    result = await env.orders.create(env.request("prod_mug", 1))
    assert env.paypal.created["purchase_units"][0]["amount"]["value"] == "18.00"
    assert env.repo.get(result.order_id).total_cents == 1800


def test_keys_survive_a_restart(env):
    env.keys.revoke(env.key_id)
    env.keys.record_spend(env.key_id, 500)
    reborn = KeyStore(repository=SqlKeyRepository(env.factory))
    assert reborn.verify(env.raw_key).ok is False  # still revoked
    assert reborn.spent_today(env.key_id) == 500
    assert [r.key_id for r in reborn.list_keys()] == [env.key_id]
    fresh = reborn.create_key("a2", "store_demo", [KeyScope.READ], env.keys.get(env.key_id).limits)
    assert fresh.record.key_id != env.key_id  # counter continues, ids never reused
