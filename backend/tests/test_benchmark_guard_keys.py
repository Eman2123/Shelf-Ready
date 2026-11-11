"""BenchmarkGuard runs on the real KeyStore: revoke, hashing and spend are not faked."""

from datetime import UTC, datetime

from app.contracts import KeyFailureReason
from app.services.benchmark.guard import BenchmarkGuard
from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.mcp_store import StoreService

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def _guard(spent: int = 0) -> BenchmarkGuard:
    service = StoreService(dict(PUBLISHED_PRODUCTS), DEFAULT_POLICY, clock=lambda: NOW)
    return BenchmarkGuard(service, spent_today_cents=spent)


def test_key_is_checked_and_only_its_hash_is_stored():
    g = _guard()
    assert g.verify_key(g.raw_key).ok
    assert g.verify_key("wrong").reason is KeyFailureReason.KEY_UNKNOWN
    assert g.verify_key("  ").reason is KeyFailureReason.KEY_UNKNOWN
    assert g.raw_key not in repr(g.keys.list_keys())


def test_revoking_fails_the_very_next_verify():
    g = _guard()
    assert not g.revoked
    g.revoked = True
    assert g.revoked and g.verify_key(g.raw_key).reason is KeyFailureReason.KEY_REVOKED


def test_seeded_daily_spend_is_the_keys_spend():
    assert _guard(27000).spent_today_cents == 27000
