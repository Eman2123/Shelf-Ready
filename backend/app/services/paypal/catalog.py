"""Read the seller's PayPal Catalog Products (sandbox) and hand them to the connector."""

from __future__ import annotations

from typing import Any

from .client import PayPalClient

PAGE_SIZE = 20
MAX_PAGES = 25  # hard stop so a bad response can never loop forever


async def fetch_catalog_products(client: PayPalClient) -> list[dict[str, Any]]:
    """All catalog products (id, name, description, category, image_url, home_url).

    The list endpoint returns summaries; this feeds `normalize_paypal_product` directly.
    """
    products: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        data = await client.get(
            "/v1/catalogs/products",
            params={"page_size": PAGE_SIZE, "page": page, "total_required": "true"},
        )
        batch = data.get("products") or []
        products.extend(batch)
        total_pages = data.get("total_pages")
        if not batch or (total_pages is not None and page >= int(total_pages)):
            break
    return products
