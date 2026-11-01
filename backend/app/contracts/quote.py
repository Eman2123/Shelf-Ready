"""Quote binding (PRD 4.3): create_order needs a quote_id that pins price, stock and a hash."""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field

from .common import Cents, Contract, CurrencyCode, Id


class QuoteError(StrEnum):
    PRICE_CHANGED = "PRICE_CHANGED"
    STOCK_CHANGED = "STOCK_CHANGED"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"
    QUOTE_UNKNOWN = "QUOTE_UNKNOWN"


def compute_quote_hash(
    product_id: str, variant_sku: str | None, price_cents: int, currency: str, stock: int
) -> str:
    """SHA-256 over the fields a quote pins. Both sides must use this exact function."""
    raw = f"{product_id}|{variant_sku or ''}|{price_cents}|{currency}|{stock}"
    return hashlib.sha256(raw.encode()).hexdigest()


class Quote(Contract):
    quote_id: Id
    product_id: Id
    variant_sku: str | None
    unit_price_cents: Cents
    currency: CurrencyCode
    stock: Annotated[int, Field(ge=0)]
    hash: str
    expires_at: datetime

    def is_consistent(self) -> bool:
        return self.hash == compute_quote_hash(
            self.product_id,
            self.variant_sku,
            self.unit_price_cents,
            self.currency,
            self.stock,
        )
