"""Store MCP tools (PRD M5). Names and inputs are a contract; change only with a heads-up."""

from __future__ import annotations

from typing import Annotated, Final

from pydantic import Field

from .common import Cents, Contract, CountryCode, Id
from .order import GuardedOrderItem

STORE_TOOL_NAMES: Final = ("search_products", "get_product", "get_policy", "create_order")


class SearchProductsInput(Contract):
    query: str = ""
    max_price_cents: Cents | None = None
    category: str | None = None
    limit: Annotated[int, Field(ge=1, le=50)] = 10


class GetProductInput(Contract):
    product_id: Id


class GetPolicyInput(Contract):
    pass


class CreateOrderInput(Contract):
    items: Annotated[list[GuardedOrderItem], Field(min_length=1)]
    ship_to_country: CountryCode
    idempotency_key: Annotated[str, Field(min_length=8)]
