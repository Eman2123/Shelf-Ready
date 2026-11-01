"""Store MCP logic (PRD M5, owner: B). Pure Python, no transport, so it is easy to test.

Quote binding (PRD 4.3): get_product issues a quote per variant that pins price, stock and a
hash. create_order refuses with PRICE_CHANGED / STOCK_CHANGED if the product moved since.
The money step itself (policy + PayPal) is A's create_guarded_order, injected as `guarded_order`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from app.contracts import (
    CreateOrderInput,
    GetProductInput,
    GuardedOrderRequest,
    GuardedOrderResult,
    PolicyRules,
    Product,
    Quote,
    QuoteError,
    SearchProductsInput,
    Variant,
    compute_quote_hash,
)

QUOTE_TTL = timedelta(minutes=10)

GuardedOrderFn = Callable[[GuardedOrderRequest], GuardedOrderResult]


def _variant(product: Product, sku: str | None) -> Variant | None:
    if sku is None:
        return None
    return next((v for v in product.variants if v.sku == sku), None)


def unit_price(product: Product, variant: Variant | None) -> int | None:
    if variant is not None and variant.price_cents is not None:
        return variant.price_cents
    return product.price_cents


def unit_stock(product: Product, variant: Variant | None) -> int | None:
    return variant.stock if variant is not None else product.stock


class StoreService:
    def __init__(
        self,
        products: Mapping[str, Product],
        rules: PolicyRules,
        guarded_order: GuardedOrderFn | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.products = products
        self.rules = rules
        self.guarded_order = guarded_order
        self.clock = clock
        self.quotes: dict[str, Quote] = {}

    # --- quotes -------------------------------------------------------------------------
    def issue_quote(self, product: Product, variant_sku: str | None) -> Quote | None:
        variant = _variant(product, variant_sku)
        price, stock = unit_price(product, variant), unit_stock(product, variant)
        if price is None or stock is None:
            return None  # data not stated: nothing safe to pin
        quote = Quote(
            quote_id=f"q_{uuid.uuid4().hex[:12]}",
            product_id=product.id,
            variant_sku=variant_sku,
            unit_price_cents=price,
            currency=product.currency,
            stock=stock,
            hash=compute_quote_hash(product.id, variant_sku, price, product.currency, stock),
            expires_at=self.clock() + QUOTE_TTL,
        )
        self.quotes[quote.quote_id] = quote
        return quote

    def check_quote(self, quote_id: str, product_id: str, quantity: int) -> QuoteError | None:
        quote = self.quotes.get(quote_id)
        product = self.products.get(product_id)
        if quote is None or product is None or quote.product_id != product_id:
            return QuoteError.QUOTE_UNKNOWN
        if self.clock() > quote.expires_at:
            return QuoteError.QUOTE_EXPIRED
        variant = _variant(product, quote.variant_sku)
        price, stock = unit_price(product, variant), unit_stock(product, variant)
        if price != quote.unit_price_cents:
            return QuoteError.PRICE_CHANGED
        if stock != quote.stock or (stock is not None and quantity > stock):
            return QuoteError.STOCK_CHANGED
        return None

    # --- the four MCP tools -------------------------------------------------------------
    def search_products(self, args: SearchProductsInput) -> list[dict[str, Any]]:
        q = args.query.strip().lower()
        out: list[dict[str, Any]] = []
        for p in self.products.values():
            if q and q not in f"{p.name} {p.description} {p.category or ''}".lower():
                continue
            if args.category and p.category != args.category:
                continue
            if args.max_price_cents is not None and (
                p.price_cents is None or p.price_cents > args.max_price_cents
            ):
                continue
            out.append(
                {
                    "product_id": p.id,
                    "name": p.name,
                    "price_cents": p.price_cents,
                    "currency": p.currency,
                    "category": p.category,
                    "in_stock": None if p.stock is None else p.stock > 0,
                }
            )
        return out[: args.limit]

    def get_product(self, args: GetProductInput) -> dict[str, Any]:
        product = self.products.get(args.product_id)
        if product is None:
            return {"error": "PRODUCT_NOT_FOUND", "product_id": args.product_id}
        skus: list[str | None] = [v.sku for v in product.variants] or [None]
        quotes = [q for sku in skus if (q := self.issue_quote(product, sku))]
        return {
            "product": product.model_dump(mode="json"),
            "quotes": [q.model_dump(mode="json") for q in quotes],
        }

    def get_policy(self) -> dict[str, Any]:
        return self.rules.model_dump(mode="json")

    def create_order(self, args: CreateOrderInput, agent_key: str) -> dict[str, Any]:
        for item in args.items:
            err = self.check_quote(item.quote_id, item.product_id, item.quantity)
            if err is not None:
                return {
                    "error": err.value,
                    "product_id": item.product_id,
                    "quote_id": item.quote_id,
                }
        if self.guarded_order is None:
            return {"error": "ORDER_BACKEND_NOT_CONNECTED"}
        request = GuardedOrderRequest(
            agent_key=agent_key,
            items=args.items,
            ship_to_country=args.ship_to_country,
            idempotency_key=args.idempotency_key,
        )
        return self.guarded_order(request).model_dump(mode="json")
