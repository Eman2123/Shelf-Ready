"""Guarded order contracts (body of the store MCP create_order tool)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from .common import Contract, CountryCode, Id
from .policy import PolicyResult


class OrderStatus(StrEnum):
    DENIED = "DENIED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    VOIDED = "VOIDED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class GuardedOrderItem(Contract):
    product_id: Id
    variant_sku: str | None = None
    quantity: Annotated[int, Field(ge=1)]
    # every item is priced from a quote, never from what the agent says
    quote_id: Id


class GuardedOrderRequest(Contract):
    # raw agent key; only its hash is ever stored
    agent_key: Annotated[str, Field(min_length=1)]
    items: Annotated[list[GuardedOrderItem], Field(min_length=1)]
    ship_to_country: CountryCode
    # retry-safe: the same key never creates two PayPal orders
    idempotency_key: Annotated[str, Field(min_length=8)]


class GuardedOrderResult(Contract):
    order_id: Id
    status: OrderStatus
    paypal_order_id: str | None
    decision: PolicyResult
    # set when the order needs the seller or buyer to approve
    approval_url: str | None
