"""Agent keys (PRD M7): hashed storage, revoke on the next request, expiry, rate limit, budget."""

from datetime import UTC, datetime, timedelta

import pytest

from app.contracts import (
    CreateOrderInput,
    GuardedOrderItem,
    KeyLimits,
    KeyRejected,
    KeyScope,
    KeyVerified,
)
from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.keys import KeyStore, hash_key
from app.services.mcp_store import StoreService


class Clock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: int) -> None:
        self.now += timedelta(**kwargs)


T0 = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def limits(**overrides) -> KeyLimits:
    base: dict = {
        "per_order_max_cents": 20000,
        "per_day_budget_cents": 30000,
        "requests_per_minute": 60,
        "allowed_categories": ["apparel", "accessories", "kitchen"],
        "expires_at": None,
    }
    base.update(overrides)
    return KeyLimits(**base)


def new_store(clock: Clock) -> tuple[KeyStore, str]:
    store = KeyStore(clock=clock)
    issued = store.create_key(
        "agent_1", "store_demo", [KeyScope.READ, KeyScope.QUOTE, KeyScope.ORDER], limits()
    )
    return store, issued.raw_key


def test_raw_key_is_never_stored_only_its_hash():
    store = KeyStore(clock=Clock(T0))
    issued = store.create_key("agent_1", "store_demo", [KeyScope.ORDER], limits())
    assert issued.raw_key.startswith("srk_")
    assert issued.record.key_hash == hash_key(issued.raw_key)
    assert issued.raw_key not in repr(issued.record)


def test_valid_key_verifies_and_carries_scopes_and_limits():
    store, raw = new_store(Clock(T0))
    result = store.verify(raw)
    assert isinstance(result, KeyVerified)
    assert result.agent.agent_id == "agent_1"
    assert KeyScope.ORDER in result.agent.scopes


def test_unknown_and_empty_keys_are_refused():
    store, _ = new_store(Clock(T0))
    unknown = store.verify("srk_not-a-real-key")
    assert isinstance(unknown, KeyRejected)
    assert unknown.reason.value == "KEY_UNKNOWN"
    assert store.verify("   ").reason.value == "KEY_UNKNOWN"


def test_revoked_key_fails_on_the_very_next_request():
    clock = Clock(T0)
    store, raw = new_store(clock)
    assert store.verify(raw).ok
    store.revoke(store.get("key_0001").key_id)
    assert store.verify(raw).reason.value == "KEY_REVOKED"


def test_expired_key_fails():
    clock = Clock(T0)
    store = KeyStore(clock=clock)
    issued = store.create_key(
        "agent_1",
        "store_demo",
        [KeyScope.ORDER],
        limits(expires_at=T0 + timedelta(hours=1)),
    )
    assert store.verify(issued.raw_key).ok
    clock.advance(hours=2)
    assert store.verify(issued.raw_key).reason.value == "KEY_EXPIRED"


def test_over_rate_limit_is_refused_then_recovers_after_the_window():
    clock = Clock(T0)
    store = KeyStore(clock=clock)
    issued = store.create_key(
        "agent_1", "store_demo", [KeyScope.ORDER], limits(requests_per_minute=2)
    )
    assert store.verify(issued.raw_key).ok
    assert store.verify(issued.raw_key).ok
    assert store.verify(issued.raw_key).reason.value == "RATE_LIMITED"
    clock.advance(minutes=1)
    assert store.verify(issued.raw_key).ok


def test_spend_is_tracked_per_key_per_day():
    clock = Clock(T0)
    store = KeyStore(clock=clock)
    issued = store.create_key("agent_1", "store_demo", [KeyScope.ORDER], limits())
    store.record_spend(issued.record.key_id, 2400)
    store.record_spend(issued.record.key_id, 1200)
    assert store.spent_today(issued.record.key_id) == 3600
    clock.advance(days=1)
    assert store.spent_today(issued.record.key_id) == 0


def test_a_key_needs_a_scope_and_negative_spend_is_refused():
    store = KeyStore(clock=Clock(T0))
    with pytest.raises(ValueError):
        store.create_key("agent_1", "store_demo", [], limits())
    issued = store.create_key("agent_1", "store_demo", [KeyScope.ORDER], limits())
    with pytest.raises(ValueError):
        store.record_spend(issued.record.key_id, -1)


def _order_args() -> CreateOrderInput:
    product = PUBLISHED_PRODUCTS["prod_tee"]
    return CreateOrderInput(
        items=[
            GuardedOrderItem(
                product_id=product.id,
                variant_sku="TEE-BLU-M",
                quantity=1,
                quote_id="placeholder",
            )
        ],
        ship_to_country="US",
        idempotency_key="idem-0001-abcd",
    )


def test_store_refuses_a_revoked_key_before_touching_any_quote():
    clock = Clock(T0)
    keys = KeyStore(clock=clock)
    issued = keys.create_key(
        "agent_bench", "store_demo", [KeyScope.READ, KeyScope.QUOTE, KeyScope.ORDER], limits()
    )
    service = StoreService(PUBLISHED_PRODUCTS, DEFAULT_POLICY, verify_key=keys.verify, clock=clock)
    keys.revoke(issued.record.key_id)
    args = _order_args()
    response = service.create_order(args, issued.raw_key)
    assert response == {"error": "KEY_REVOKED"}


def test_store_refuses_a_key_without_the_order_scope():
    clock = Clock(T0)
    keys = KeyStore(clock=clock)
    issued = keys.create_key("agent_bench", "store_demo", [KeyScope.READ], limits())
    service = StoreService(PUBLISHED_PRODUCTS, DEFAULT_POLICY, verify_key=keys.verify, clock=clock)
    assert service.create_order(_order_args(), issued.raw_key) == {"error": "KEY_SCOPE_MISSING"}
