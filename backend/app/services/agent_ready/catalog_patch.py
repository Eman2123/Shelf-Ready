"""PayPal Catalog PATCH body (JSON Patch) built from the published product.

PayPal's catalog update supports replacing description, category, image_url and home_url.
Only fields we actually have are included, and nothing is invented.
"""

from __future__ import annotations

from typing import Any

from app.contracts import Product


def build_catalog_patch(product: Product) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    if product.description.strip():
        ops.append({"op": "replace", "path": "/description", "value": product.description})
    if product.category:
        ops.append({"op": "replace", "path": "/category", "value": product.category})
    if product.images:
        ops.append({"op": "replace", "path": "/image_url", "value": product.images[0].url})
    if product.home_url:
        ops.append({"op": "replace", "path": "/home_url", "value": product.home_url})
    return ops
