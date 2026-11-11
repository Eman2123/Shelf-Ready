"""PayPal Orders v2 + Payments v2 calls (sandbox). Thin and typed; no business rules here.

Money step order used by Shelf Ready: create (intent AUTHORIZE) -> buyer approves at PayPal ->
authorize -> capture the authorization, or void it. Every write carries a PayPal-Request-Id
derived from our own idempotency key, so a retry never creates a second PayPal object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .client import PayPalClient, PayPalError

APPROVAL_RELS = ("payer-action", "approve")


def cents_to_value(cents: int) -> str:
    """Integer cents -> PayPal decimal string, e.g. 18000 -> "180.00". Never uses floats."""
    if cents < 0:
        raise ValueError("amount cannot be negative")
    return f"{cents // 100}.{cents % 100:02d}"


def value_to_cents(value: str | float) -> int:
    whole, _, frac = str(value).partition(".")
    return int(whole or 0) * 100 + int((frac + "00")[:2])


@dataclass(frozen=True)
class OrderLine:
    name: str
    sku: str | None
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True)
class PayPalOrder:
    paypal_order_id: str
    status: str
    approval_url: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class OrderWitness:
    """What PayPal itself says about an order, read-only. Used before every capture."""

    paypal_order_id: str
    status: str
    currency: str | None
    total_cents: int | None
    authorization_id: str | None
    authorization_status: str | None
    capture_id: str | None
    custom_id: str | None


def _approval_url(body: dict[str, Any]) -> str | None:
    for rel in APPROVAL_RELS:
        for link in body.get("links", []):
            if link.get("rel") == rel:
                return link.get("href")
    return None


class PayPalOrders:
    def __init__(self, client: PayPalClient) -> None:
        self.client = client

    async def create_order(
        self,
        *,
        reference_id: str,
        lines: list[OrderLine],
        currency: str,
        request_id: str,
        return_url: str,
        cancel_url: str,
        brand_name: str = "Shelf Ready",
    ) -> PayPalOrder:
        item_total = sum(line.unit_price_cents * line.quantity for line in lines)
        amount = {
            "currency_code": currency,
            "value": cents_to_value(item_total),
            "breakdown": {
                "item_total": {"currency_code": currency, "value": cents_to_value(item_total)}
            },
        }
        body = {
            "intent": "AUTHORIZE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "custom_id": reference_id,
                    "amount": amount,
                    "items": [
                        {
                            "name": line.name[:127],
                            "sku": (line.sku or "")[:127] or None,
                            "quantity": str(line.quantity),
                            "unit_amount": {
                                "currency_code": currency,
                                "value": cents_to_value(line.unit_price_cents),
                            },
                        }
                        for line in lines
                    ],
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "brand_name": brand_name,
                        "user_action": "PAY_NOW",
                        "shipping_preference": "NO_SHIPPING",
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                    }
                }
            },
        }
        for item in body["purchase_units"][0]["items"]:
            if item["sku"] is None:
                del item["sku"]
        data = await self.client.post("/v2/checkout/orders", json=body, request_id=request_id)
        return PayPalOrder(
            paypal_order_id=data["id"],
            status=data.get("status", "CREATED"),
            approval_url=_approval_url(data),
            raw=data,
        )

    async def get_order(self, paypal_order_id: str) -> dict[str, Any]:
        return await self.client.get(f"/v2/checkout/orders/{paypal_order_id}")

    async def authorize_order(self, paypal_order_id: str, *, request_id: str) -> OrderWitness:
        data = await self.client.post(
            f"/v2/checkout/orders/{paypal_order_id}/authorize", json={}, request_id=request_id
        )
        return self.witness_from(data)

    async def capture_authorization(
        self, authorization_id: str, *, request_id: str, amount_cents: int, currency: str
    ) -> dict[str, Any]:
        return await self.client.post(
            f"/v2/payments/authorizations/{authorization_id}/capture",
            json={
                "amount": {"currency_code": currency, "value": cents_to_value(amount_cents)},
                "final_capture": True,
            },
            request_id=request_id,
        )

    async def void_authorization(self, authorization_id: str, *, request_id: str) -> dict[str, Any]:
        return await self.client.post(
            f"/v2/payments/authorizations/{authorization_id}/void", request_id=request_id
        )

    async def refund_capture(
        self,
        capture_id: str,
        *,
        request_id: str,
        amount_cents: int | None = None,
        currency: str = "USD",
        note: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if amount_cents is not None:
            body["amount"] = {"currency_code": currency, "value": cents_to_value(amount_cents)}
        if note:
            body["note_to_payer"] = note[:255]
        return await self.client.post(
            f"/v2/payments/captures/{capture_id}/refund", json=body, request_id=request_id
        )

    # --- read-only witness ---------------------------------------------------------------
    @staticmethod
    def witness_from(data: dict[str, Any]) -> OrderWitness:
        units = data.get("purchase_units") or [{}]
        unit = units[0]
        amount = unit.get("amount") or {}
        payments = unit.get("payments") or {}
        auth = (payments.get("authorizations") or [None])[0] or {}
        capture = (payments.get("captures") or [None])[0] or {}
        value = amount.get("value")
        return OrderWitness(
            paypal_order_id=data.get("id", ""),
            status=data.get("status", ""),
            currency=amount.get("currency_code"),
            total_cents=value_to_cents(value) if value is not None else None,
            authorization_id=auth.get("id"),
            authorization_status=auth.get("status"),
            capture_id=capture.get("id"),
            custom_id=unit.get("custom_id") or unit.get("reference_id"),
        )

    async def witness(self, paypal_order_id: str) -> OrderWitness:
        """Independent read of the order straight from PayPal (PRD M8: confirms before capture)."""
        return self.witness_from(await self.get_order(paypal_order_id))


__all__ = [
    "OrderLine",
    "OrderWitness",
    "PayPalError",
    "PayPalOrder",
    "PayPalOrders",
    "cents_to_value",
    "value_to_cents",
]
