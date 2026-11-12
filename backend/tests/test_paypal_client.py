import httpx
import pytest
import respx

from app.services.paypal.client import PayPalClient, PayPalError, PayPalSettings

BASE = "https://api-m.sandbox.paypal.com"


def make_client() -> PayPalClient:
    return PayPalClient(
        PayPalSettings(client_id="test-id", client_secret="test-secret", base_url=BASE)
    )


def token_response(token: str = "tok-1", expires_in: int = 3600) -> httpx.Response:
    return httpx.Response(200, json={"access_token": token, "expires_in": expires_in})


@pytest.mark.asyncio
@respx.mock
async def test_token_is_cached_across_requests():
    token_route = respx.post(f"{BASE}/v1/oauth2/token").mock(return_value=token_response())
    respx.get(f"{BASE}/v2/checkout/orders/A").mock(
        return_value=httpx.Response(200, json={"id": "A"})
    )
    client = make_client()
    await client.get("/v2/checkout/orders/A")
    await client.get("/v2/checkout/orders/A")
    assert token_route.call_count == 1
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_write_requests_send_request_id():
    respx.post(f"{BASE}/v1/oauth2/token").mock(return_value=token_response())
    order_route = respx.post(f"{BASE}/v2/checkout/orders").mock(
        return_value=httpx.Response(201, json={"id": "ORDER1"})
    )
    client = make_client()
    await client.post("/v2/checkout/orders", json={"intent": "AUTHORIZE"}, request_id="req-123")
    assert order_route.calls.last.request.headers["PayPal-Request-Id"] == "req-123"
    await client.post("/v2/checkout/orders", json={"intent": "AUTHORIZE"})
    assert order_route.calls.last.request.headers["PayPal-Request-Id"]
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_get_does_not_send_request_id():
    respx.post(f"{BASE}/v1/oauth2/token").mock(return_value=token_response())
    route = respx.get(f"{BASE}/v2/checkout/orders/A").mock(
        return_value=httpx.Response(200, json={"id": "A"})
    )
    client = make_client()
    await client.get("/v2/checkout/orders/A")
    assert "PayPal-Request-Id" not in route.calls.last.request.headers
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_401_triggers_one_token_refresh_and_retry():
    token_route = respx.post(f"{BASE}/v1/oauth2/token").mock(
        side_effect=[token_response("old"), token_response("new")]
    )
    respx.get(f"{BASE}/v2/checkout/orders/A").mock(
        side_effect=[
            httpx.Response(401, json={"error": "invalid_token"}),
            httpx.Response(200, json={"id": "A"}),
        ]
    )
    client = make_client()
    result = await client.get("/v2/checkout/orders/A")
    assert result == {"id": "A"}
    assert token_route.call_count == 2
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_error_response_raises_paypal_error():
    respx.post(f"{BASE}/v1/oauth2/token").mock(return_value=token_response())
    respx.post(f"{BASE}/v2/checkout/orders").mock(
        return_value=httpx.Response(
            422, json={"name": "UNPROCESSABLE_ENTITY", "message": "Bad amount", "debug_id": "dbg1"}
        )
    )
    client = make_client()
    with pytest.raises(PayPalError) as exc:
        await client.post("/v2/checkout/orders", json={})
    assert exc.value.status_code == 422
    assert exc.value.debug_id == "dbg1"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_bad_credentials_raise_paypal_error():
    respx.post(f"{BASE}/v1/oauth2/token").mock(
        return_value=httpx.Response(
            401, json={"error": "invalid_client", "error_description": "Bad credentials"}
        )
    )
    client = make_client()
    with pytest.raises(PayPalError):
        await client.get_access_token()
    await client.aclose()
