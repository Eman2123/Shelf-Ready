"""schema.org JSON-LD for a product, so any crawler or agent can read typed price and stock."""

from __future__ import annotations

from typing import Any

from app.contracts import Product, Variant

IN_STOCK = "https://schema.org/InStock"
OUT_OF_STOCK = "https://schema.org/OutOfStock"


def format_price(cents: int) -> str:
    """Integer cents to a decimal string ("2400" -> "24.00"). Two-decimal currencies only."""
    return f"{cents // 100}.{cents % 100:02d}"


def _availability(stock: int | None) -> str | None:
    if stock is None:
        return None  # not stated by the seller: say nothing rather than guess
    return IN_STOCK if stock > 0 else OUT_OF_STOCK


def _offer(product: Product, variant: Variant | None) -> dict[str, Any] | None:
    price = (
        variant.price_cents if variant and variant.price_cents is not None else product.price_cents
    )
    if price is None:
        return None
    stock = variant.stock if variant else product.stock
    offer: dict[str, Any] = {
        "@type": "Offer",
        "price": format_price(price),
        "priceCurrency": product.currency,
    }
    if variant and variant.sku:
        offer["sku"] = variant.sku
    if variant and variant.attributes:
        offer["additionalProperty"] = [
            {"@type": "PropertyValue", "name": k, "value": v} for k, v in variant.attributes.items()
        ]
    availability = _availability(stock)
    if availability:
        offer["availability"] = availability
    if stock is not None:
        offer["inventoryLevel"] = {"@type": "QuantitativeValue", "value": stock}
    return offer


def product_to_jsonld(product: Product) -> dict[str, Any]:
    offers = (
        [_offer(product, v) for v in product.variants]
        if product.variants
        else [_offer(product, None)]
    )
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "@id": product.home_url or product.id,
        "name": product.name,
        "description": product.description,
        "offers": [o for o in offers if o],
    }
    if product.sku:
        data["sku"] = product.sku
    if product.gtin:
        data["gtin"] = product.gtin
    if product.category:
        data["category"] = product.category
    if product.images:
        data["image"] = [
            {"@type": "ImageObject", "url": i.url, **({"caption": i.alt} if i.alt else {})}
            for i in product.images
        ]
    if product.shipping and product.shipping.cost_cents is not None:
        data["shippingDetails"] = {
            "@type": "OfferShippingDetails",
            "shippingRate": {
                "@type": "MonetaryAmount",
                "value": format_price(product.shipping.cost_cents),
                "currency": product.currency,
            },
            "shippingDestination": [
                {"@type": "DefinedRegion", "addressCountry": c} for c in product.shipping.regions
            ],
        }
    if product.returns and product.returns.window_days is not None:
        data["hasMerchantReturnPolicy"] = {
            "@type": "MerchantReturnPolicy",
            "merchantReturnDays": product.returns.window_days,
        }
    return data
