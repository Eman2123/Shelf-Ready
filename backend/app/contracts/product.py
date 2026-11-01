"""One normalized product record. Every importer and the PayPal connector must produce this."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from .common import Cents, Contract, CountryCode, CurrencyCode, Id

NonNegInt = Annotated[int, Field(ge=0)]


class Variant(Contract):
    sku: str | None
    # e.g. {"size": "M", "color": "blue"}
    attributes: dict[str, str]
    price_cents: Cents | None
    # None = stock not stated by the seller (an audit issue), 0 = out of stock
    stock: NonNegInt | None


class Shipping(Contract):
    regions: list[CountryCode]
    cost_cents: Cents | None
    min_days: NonNegInt | None
    max_days: NonNegInt | None


class Returns(Contract):
    window_days: NonNegInt | None
    free_returns: bool | None
    policy_text: str | None


class Image(Contract):
    url: str
    alt: str | None


class Product(Contract):
    id: Id
    store_id: Id
    paypal_product_id: str | None
    name: Annotated[str, StringConstraints(min_length=1)]
    description: str
    # None when the source only says something vague such as "from $20"
    price_cents: Cents | None
    # the raw price text exactly as found in the source, kept for provenance
    price_text: str | None
    currency: CurrencyCode
    # product-level stock; None = not stated
    stock: NonNegInt | None
    variants: list[Variant]
    shipping: Shipping | None
    returns: Returns | None
    sku: str | None
    gtin: str | None
    images: list[Image]
    category: str | None
    home_url: str | None
    # true when checkout needs a human step (for example "confirm size by phone")
    checkout_requires_human: bool
    # hash of the normalized source data, used for dedupe and drift detection
    source_hash: Annotated[str, StringConstraints(min_length=1)]
