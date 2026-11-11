"""PayPal Orders v2 service (AUTHORIZE flow) with a read-only witness check.

Rule: only this deterministic code creates or captures money. Capture is refused unless an
independent order lookup matches the expected amount, currency and authorization status.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.services.paypal.client import PayPalClient


class WitnessMismatch(Exception):
    """The independent order lookup does not match what we expected."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def money(value: Decimal | str | float) -> str:
    """Format an amount the way PayPal expects: a string with 2 decimals."""
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def cents_to_amount(cents: int) -> str:
    return money(Decimal(cents) / Decimal(100))


class OrderService:
    def __init__(self, client: PayPalClient) -> None:
        self.client = client

    async def create_order(
        self,
        amount: Decimal | str | float,
        currency: str,
        reference_id: str,
        request_id: str,
    ) -> dict[str, str]:
        """Create an AUTHORIZE order. Returns order_id, status, approve_url."""
        body = {
            "intent": "AUTHORIZE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "amount": {"currency_code": currency.upper(), "value": money(amount)},
                }
            ],
        }
        order = await self.client.post("/v2/checkout/orders", json=body, request_id=request_id)
        approve_url = ""
        for link in order.get("links", []):
            if link.get("rel") in ("approve", "payer-action"):
                approve_url = link["href"]
                break
        return {
            "order_id": order["id"],
            "status": order.get("status", ""),
            "approve_url": approve_url,
        }

    async def authorize_order(self, order_id: str, request_id: str) -> str:
        """Authorize an order the buyer approved. Returns the authorization id."""
        result = await self.client.post(
            f"/v2/checkout/orders/{order_id}/authorize", json={}, request_id=request_id
        )
        auths = (
            result.get("purchase_units", [{}])[0].get("payments", {}).get("authorizations", [])
        )
        if not auths:
            raise WitnessMismatch(["authorize response has no authorization"])
        return auths[0]["id"]

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self.client.get(f"/v2/checkout/orders/{order_id}")

    async def witness_check(
        self,
        order_id: str,
        expected_amount: Decimal | str | float,
        expected_currency: str,
    ) -> str:
        """Independent read-only lookup. Returns the authorization id or raises."""
        order = await self.get_order(order_id)
        problems: list[str] = []
        unit = (order.get("purchase_units") or [{}])[0]
        amount = unit.get("amount", {})
        if amount.get("currency_code") != expected_currency.upper():
            problems.append(
                f"currency {amount.get('currency_code')} != {expected_currency.upper()}"
            )
        try:
            if Decimal(amount.get("value", "")) != Decimal(money(expected_amount)):
                problems.append(f"amount {amount.get('value')} != {money(expected_amount)}")
        except (InvalidOperation, TypeError):
            problems.append("amount missing or unreadable")
        auths = unit.get("payments", {}).get("authorizations", [])
        auth_id = ""
        if not auths:
            problems.append("no authorization on order")
        else:
            auth_id = auths[0]["id"]
            if auths[0].get("status") != "CREATED":
                problems.append(f"authorization status {auths[0].get('status')} != CREATED")
        if problems:
            raise WitnessMismatch(problems)
        return auth_id

    async def capture_guarded(
        self,
        order_id: str,
        amount: Decimal | str | float,
        currency: str,
        request_id: str,
    ) -> dict[str, Any]:
        """Capture only after the witness check passes."""
        auth_id = await self.witness_check(order_id, amount, currency)
        return await self.client.post(
            f"/v2/payments/authorizations/{auth_id}/capture",
            json={
                "amount": {"currency_code": currency.upper(), "value": money(amount)},
                "final_capture": True,
            },
            request_id=request_id,
        )

    async def void_authorization(self, authorization_id: str, request_id: str) -> dict[str, Any]:
        return await self.client.post(
            f"/v2/payments/authorizations/{authorization_id}/void", json={}, request_id=request_id
        )

    async def refund_capture(
        self,
        capture_id: str,
        request_id: str,
        amount: Decimal | str | float | None = None,
        currency: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if amount is not None and currency:
            body = {"amount": {"currency_code": currency.upper(), "value": money(amount)}}
        return await self.client.post(
            f"/v2/payments/captures/{capture_id}/refund", json=body, request_id=request_id
        )
