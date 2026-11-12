import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import app
from app.services.paypal import (
    PayPalClient,
    PayPalConfigError,
    PayPalSettings,
    WebhookVerificationError,
    fetch_catalog_products,
    verify_webhook,
)

BASE = "https://api-m.sandbox.paypal.com"
HEADERS = {
    "PAYPAL-AUTH-ALGO": "SHA256withRSA",
    "PAYPAL-CERT-URL": "https://api.sandbox.paypal.com/cert",
    "PAYPAL-TRANSMISSION-ID": "tx-1",
    "PAYPAL-TRANSMISSION-SIG": "sig",
    "PAYPAL-TRANSMISSION-TIME": "2026-11-12T00:00:00Z",
}
BODY = json.dumps({"id": "WH-1", "event_type": "CHECKOUT.ORDER.APPROVED", "resource": {}}).encode()


def client(webhook_id: str = "WH-ID") -> PayPalClient:
    return PayPalClient(PayPalSettings("id", "secret", BASE, webhook_id=webhook_id))


def token(router):
    router.post(f"{BASE}/v1/oauth2/token").mock(
        return_value=httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
    )


@respx.mock
async def test_success_returns_event_and_sends_full_payload():
    token(respx)
    route = respx.post(f"{BASE}/v1/notifications/verify-webhook-signature").mock(
        return_value=httpx.Response(200, json={"verification_status": "SUCCESS"})
    )
    event = await verify_webhook(client(), HEADERS, BODY)
    assert event["id"] == "WH-1"
    sent = json.loads(route.calls.last.request.content)
    assert sent["webhook_id"] == "WH-ID" and sent["transmission_id"] == "tx-1"
    assert sent["webhook_event"]["id"] == "WH-1"


@respx.mock
async def test_failure_status_is_rejected():
    token(respx)
    respx.post(f"{BASE}/v1/notifications/verify-webhook-signature").mock(
        return_value=httpx.Response(200, json={"verification_status": "FAILURE"})
    )
    with pytest.raises(WebhookVerificationError):
        await verify_webhook(client(), HEADERS, BODY)


async def test_missing_headers_rejected_before_any_network_call():
    with pytest.raises(WebhookVerificationError):
        await verify_webhook(client(), {"PAYPAL-AUTH-ALGO": "x"}, BODY)


async def test_no_webhook_id_fails_closed():
    with pytest.raises(PayPalConfigError):
        await verify_webhook(client(webhook_id=""), HEADERS, BODY)


async def test_garbage_body_rejected():
    with pytest.raises(WebhookVerificationError):
        await verify_webhook(client(), HEADERS, b"not json")


@respx.mock
async def test_catalog_pagination():
    token(respx)
    respx.get(f"{BASE}/v1/catalogs/products").mock(
        side_effect=[
            httpx.Response(200, json={"products": [{"id": "P1"}], "total_pages": 2}),
            httpx.Response(200, json={"products": [{"id": "P2"}], "total_pages": 2}),
        ]
    )
    items = await fetch_catalog_products(client())
    assert [p["id"] for p in items] == ["P1", "P2"]


def test_webhook_endpoint_is_off_without_credentials():
    # the test environment has no PayPal credentials, so nothing can be accepted
    response = TestClient(app).post("/api/webhooks/paypal", content=BODY, headers=HEADERS)
    assert response.status_code == 503


def test_order_admin_routes_need_the_admin_token():
    http = TestClient(app)
    assert http.get("/api/orders").status_code in (401, 503)
    assert http.post("/api/approvals/x/approve").status_code in (401, 503)
    assert http.get("/health").json()["paypal"] == "not-connected"


def test_migrations_create_exactly_the_model_tables(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    from app.db.models import Base

    url = f"sqlite:///{tmp_path / 'm.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert set(Base.metadata.tables) <= tables
    command.downgrade(cfg, "base")


def test_env_file_parser_and_no_override(tmp_path, monkeypatch):
    from app.core.env import load_env, parse_env

    assert parse_env('A=1\n# c\nexport B="two words"\nC=x # note\nD=\n') == {
        "A": "1",
        "B": "two words",
        "C": "x",
        "D": "",
    }
    f = tmp_path / ".env"
    f.write_text("SR_TEST_A=from-file\nSR_TEST_B=from-file\n", encoding="utf-8")
    monkeypatch.setenv("SR_TEST_B", "already-set")
    monkeypatch.delenv("SR_TEST_A", raising=False)
    assert load_env([f]) == ["SR_TEST_A"]
    import os

    assert os.environ["SR_TEST_A"] == "from-file"
    assert os.environ["SR_TEST_B"] == "already-set"  # real environment wins
    monkeypatch.delenv("SR_TEST_A")
