"""Keys wired into the running app, admin guard, security headers, validator route, rate limit."""

import pytest
from fastapi.testclient import TestClient

from app.contracts import CreateOrderInput, GetProductInput, GuardedOrderItem
from app.core.runtime import store_service
from app.core.security import limiter
from app.main import app

ADMIN = {"X-Admin-Token": "test-admin-token"}
KEY_BODY = {
    "agent_id": "agent_test",
    "scopes": ["read", "quote", "order"],
    "per_order_max_cents": 20000,
    "per_day_budget_cents": 30000,
    "allowed_categories": ["apparel"],
}


@pytest.fixture(autouse=True)
def _reset_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
    return TestClient(app)


def _order_args() -> CreateOrderInput:
    quotes = store_service.get_product(GetProductInput(product_id="prod_tee"))["quotes"]
    quote = next(q for q in quotes if q["variant_sku"] == "TEE-BLU-M")
    return CreateOrderInput(
        items=[
            GuardedOrderItem(
                product_id="prod_tee",
                variant_sku="TEE-BLU-M",
                quantity=1,
                quote_id=quote["quote_id"],
            )
        ],
        ship_to_country="US",
        idempotency_key="idem-test-0001",
    )


def test_key_endpoints_are_off_when_no_admin_token_is_set(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert TestClient(app).get("/api/keys").status_code == 503


def test_wrong_or_missing_admin_token_is_refused(client):
    assert client.get("/api/keys").status_code == 401
    assert client.get("/api/keys", headers={"X-Admin-Token": "nope"}).status_code == 401
    assert client.post("/api/keys", json=KEY_BODY).status_code == 401


def test_created_key_is_shown_once_and_never_listed_with_secret_or_hash(client):
    created = client.post("/api/keys", json=KEY_BODY, headers=ADMIN)
    assert created.status_code == 201
    body = created.json()
    assert body["raw_key"].startswith("srk_") and body["shown_once"] is True
    listing = client.get("/api/keys", headers=ADMIN).text
    assert body["raw_key"] not in listing
    assert "key_hash" not in listing and "hash" not in listing


def test_bad_key_body_is_rejected(client):
    bad = {**KEY_BODY, "scopes": []}
    assert client.post("/api/keys", json=bad, headers=ADMIN).status_code == 422
    extra = {**KEY_BODY, "surprise": 1}
    assert client.post("/api/keys", json=extra, headers=ADMIN).status_code == 422


def test_running_store_refuses_unknown_key_and_revoked_key_on_the_next_request(client):
    args = _order_args()
    assert store_service.create_order(args, "srk_made-up") == {"error": "KEY_UNKNOWN"}

    created = client.post("/api/keys", json=KEY_BODY, headers=ADMIN).json()
    raw, key_id = created["raw_key"], created["key"]["key_id"]
    # valid key passes the key and quote checks; there is no PayPal backend, so nothing is created
    assert store_service.create_order(args, raw) == {"error": "ORDER_BACKEND_NOT_CONNECTED"}

    assert client.post(f"/api/keys/{key_id}/revoke", headers=ADMIN).status_code == 200
    assert store_service.create_order(args, raw) == {"error": "KEY_REVOKED"}


def test_revoking_an_unknown_key_is_404(client):
    assert client.post("/api/keys/key_nope/revoke", headers=ADMIN).status_code == 404


def test_security_headers_are_on_every_response(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert "strict-transport-security" not in r.headers  # plain http
    https = client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert "strict-transport-security" in https.headers


def test_swagger_docs_are_not_blocked_by_the_api_csp(client):
    assert "content-security-policy" not in client.get("/docs").headers


def test_cors_allows_only_the_configured_frontend_origin(client):
    ok = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    other = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_validate_route_accepts_supported_and_rejects_invented_values(client):
    source = "Soft tee. Machine wash cold."
    good = client.post(
        "/api/fixes/validate",
        json={
            "source_text": source,
            "proposed": "Machine wash cold",
            "snippet": "Machine wash cold.",
            "method": "AI_EXTRACT",
        },
    ).json()
    assert good["status"] == "PASSED_EXACT" and good["confidence"] == 1.0
    bad = client.post(
        "/api/fixes/validate",
        json={
            "source_text": source,
            "proposed": "100% organic cotton",
            "snippet": "100% organic cotton",
            "method": "AI_EXTRACT",
        },
    ).json()
    assert bad["status"] == "REJECTED_NO_SUPPORT" and bad["confidence"] == 0.0
    assert "not in the source" in bad["reason"]


def test_validate_route_rejects_oversized_input(client):
    body = {"source_text": "x" * 20_001, "proposed": "a", "snippet": "a", "method": "RULE"}
    assert client.post("/api/fixes/validate", json=body).status_code == 422


def test_public_routes_are_rate_limited(client):
    payload = {"source_text": "a", "proposed": "a", "snippet": "a", "method": "RULE"}
    codes = [client.post("/api/fixes/validate", json=payload).status_code for _ in range(61)]
    assert codes[:60] == [200] * 60
    assert codes[60] == 429
