import httpx
import pytest
import respx

from app.services.orders.service import OrderService, WitnessMismatch, cents_to_amount, money
from app.services.paypal.client import PayPalClient, PayPalSettings

BASE = "https://api-m.sandbox.paypal.com"


def make_service() -> OrderService:
    return OrderService(
        PayPalClient(PayPalSettings(client_id="id", client_secret="secret", base_url=BASE))
    )


def mock_token() -> None:
    respx.post(f"{BASE}/v1/oauth2/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
    )


def order_json(value="24.00", currency="USD", auth_status="CREATED", with_auth=True):
    unit: dict = {"amount": {"currency_code": currency, "value": value}}
    if with_auth:
        unit["payments"] = {"authorizations": [{"id": "AUTH1", "status": auth_status}]}
    return {"id": "ORDER1", "status": "COMPLETED", "purchase_units": [unit]}


def test_money_format():
    assert money(24) == "24.00"
    assert money("24.5") == "24.50"
    assert money(19.999) == "20.00"
    assert cents_to_amount(2400) == "24.00"


@respx.mock
async def test_create_order_returns_approve_url_and_authorize_intent():
    mock_token()
    route = respx.post(f"{BASE}/v2/checkout/orders").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "ORDER1",
                "status": "CREATED",
                "links": [{"rel": "approve", "href": "https://paypal.test/approve"}],
            },
        )
    )
    result = await make_service().create_order(24, "usd", "ref-1", request_id="req-1")
    assert result["approve_url"] == "https://paypal.test/approve"
    sent = route.calls.last.request
    assert sent.headers["PayPal-Request-Id"] == "req-1"
    assert b'"AUTHORIZE"' in sent.content
    assert b'"24.00"' in sent.content


@respx.mock
async def test_capture_happens_when_witness_matches():
    mock_token()
    respx.get(f"{BASE}/v2/checkout/orders/ORDER1").mock(
        return_value=httpx.Response(200, json=order_json())
    )
    cap = respx.post(f"{BASE}/v2/payments/authorizations/AUTH1/capture").mock(
        return_value=httpx.Response(201, json={"id": "CAP1", "status": "COMPLETED"})
    )
    result = await make_service().capture_guarded("ORDER1", 24, "USD", request_id="cap-1")
    assert result["id"] == "CAP1"
    assert cap.call_count == 1


@respx.mock
async def test_no_capture_when_amount_mismatch():
    mock_token()
    respx.get(f"{BASE}/v2/checkout/orders/ORDER1").mock(
        return_value=httpx.Response(200, json=order_json(value="180.00"))
    )
    cap = respx.post(f"{BASE}/v2/payments/authorizations/AUTH1/capture").mock(
        return_value=httpx.Response(201, json={"id": "CAP1"})
    )
    with pytest.raises(WitnessMismatch):
        await make_service().capture_guarded("ORDER1", 24, "USD", request_id="cap-2")
    assert cap.call_count == 0


@respx.mock
async def test_no_capture_when_currency_differs():
    mock_token()
    respx.get(f"{BASE}/v2/checkout/orders/ORDER1").mock(
        return_value=httpx.Response(200, json=order_json(currency="EUR"))
    )
    cap = respx.post(f"{BASE}/v2/payments/authorizations/AUTH1/capture").mock(
        return_value=httpx.Response(201, json={"id": "CAP1"})
    )
    with pytest.raises(WitnessMismatch):
        await make_service().capture_guarded("ORDER1", 24, "USD", request_id="cap-3")
    assert cap.call_count == 0


@respx.mock
async def test_no_capture_when_authorization_missing_or_not_created():
    mock_token()
    cap = respx.post(f"{BASE}/v2/payments/authorizations/AUTH1/capture").mock(
        return_value=httpx.Response(201, json={"id": "CAP1"})
    )
    get_route = respx.get(f"{BASE}/v2/checkout/orders/ORDER1")
    svc = make_service()
    get_route.mock(return_value=httpx.Response(200, json=order_json(with_auth=False)))
    with pytest.raises(WitnessMismatch):
        await svc.capture_guarded("ORDER1", 24, "USD", request_id="c4")
    get_route.mock(return_value=httpx.Response(200, json=order_json(auth_status="VOIDED")))
    with pytest.raises(WitnessMismatch):
        await svc.capture_guarded("ORDER1", 24, "USD", request_id="c5")
    assert cap.call_count == 0


@respx.mock
async def test_void_and_refund_send_request_id():
    mock_token()
    void = respx.post(f"{BASE}/v2/payments/authorizations/AUTH1/void").mock(
        return_value=httpx.Response(204)
    )
    refund = respx.post(f"{BASE}/v2/payments/captures/CAP1/refund").mock(
        return_value=httpx.Response(201, json={"id": "REF1", "status": "COMPLETED"})
    )
    svc = make_service()
    await svc.void_authorization("AUTH1", request_id="void-1")
    assert void.calls.last.request.headers["PayPal-Request-Id"] == "void-1"
    result = await svc.refund_capture("CAP1", request_id="ref-1", amount=5, currency="USD")
    assert result["id"] == "REF1"
    assert b'"5.00"' in refund.calls.last.request.content
