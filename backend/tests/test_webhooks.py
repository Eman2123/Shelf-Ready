import json

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import webhooks_paypal
from app.services.paypal.client import PayPalClient, PayPalSettings
from app.services.webhooks.handler import (
    InMemoryEventStore,
    WebhookHandler,
    WebhookRejected,
)

BASE = "https://api-m.sandbox.paypal.com"
HEADERS = {
    "paypal-transmission-id": "t1",
    "paypal-transmission-time": "2026-11-11T10:00:00Z",
    "paypal-transmission-sig": "sig",
    "paypal-cert-url": "https://api.sandbox.paypal.com/cert",
    "paypal-auth-algo": "SHA256withRSA",
}


def make_handler(store=None) -> WebhookHandler:
    client = PayPalClient(PayPalSettings(client_id="id", client_secret="s", base_url=BASE))
    return WebhookHandler(client, "WH-1", store or InMemoryEventStore())


def mock_paypal(status: str = "SUCCESS"):
    respx.post(f"{BASE}/v1/oauth2/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
    )
    return respx.post(f"{BASE}/v1/notifications/verify-webhook-signature").mock(
        return_value=httpx.Response(200, json={"verification_status": status})
    )


def body(event_id="EV1", event_type="PAYMENT.CAPTURE.COMPLETED") -> bytes:
    return json.dumps({"id": event_id, "event_type": event_type}).encode()


@respx.mock
async def test_valid_event_is_processed_and_sent_to_paypal_for_verification():
    verify = mock_paypal()
    store = InMemoryEventStore()
    assert await make_handler(store).handle(HEADERS, body()) == "processed"
    sent = json.loads(verify.calls.last.request.content)
    assert sent["webhook_id"] == "WH-1"
    assert sent["transmission_id"] == "t1"
    assert sent["webhook_event"]["id"] == "EV1"
    assert "EV1" in store.events


@respx.mock
async def test_duplicate_event_is_not_processed_twice():
    mock_paypal()
    store = InMemoryEventStore()
    handler = make_handler(store)
    assert await handler.handle(HEADERS, body()) == "processed"
    assert await handler.handle(HEADERS, body()) == "duplicate"
    assert len(store.events) == 1


@respx.mock
async def test_out_of_order_events_are_all_recorded():
    mock_paypal()
    store = InMemoryEventStore()
    handler = make_handler(store)
    await handler.handle(HEADERS, body("EV2", "PAYMENT.CAPTURE.COMPLETED"))
    await handler.handle(HEADERS, body("EV1", "PAYMENT.AUTHORIZATION.CREATED"))
    assert set(store.events) == {"EV1", "EV2"}


@respx.mock
async def test_failed_verification_is_rejected_and_not_stored():
    mock_paypal(status="FAILURE")
    store = InMemoryEventStore()
    with pytest.raises(WebhookRejected):
        await make_handler(store).handle(HEADERS, body())
    assert store.events == {}


@respx.mock
async def test_missing_headers_rejected_without_calling_paypal():
    verify = mock_paypal()
    with pytest.raises(WebhookRejected):
        await make_handler().handle({"paypal-transmission-id": "t1"}, body())
    assert verify.call_count == 0


async def test_bad_json_rejected():
    with pytest.raises(WebhookRejected):
        await make_handler().handle(HEADERS, b"not json")


def test_endpoint_returns_503_when_paypal_not_configured(monkeypatch):
    for name in ("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(webhooks_paypal, "_handler", None)
    app = FastAPI()
    app.include_router(webhooks_paypal.router)
    res = TestClient(app).post("/api/webhooks/paypal", content=body(), headers=HEADERS)
    assert res.status_code == 503


def test_endpoint_returns_400_on_rejected_event(monkeypatch):
    class Rejecting:
        async def handle(self, headers, raw):
            raise WebhookRejected("signature not verified")

    monkeypatch.setattr(webhooks_paypal, "_handler", Rejecting())
    app = FastAPI()
    app.include_router(webhooks_paypal.router)
    res = TestClient(app).post("/api/webhooks/paypal", content=body(), headers=HEADERS)
    assert res.status_code == 400
