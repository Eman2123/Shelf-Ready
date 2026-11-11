"""PayPal catalog -> Product (PRD M2). The HTTP source is injectable so tests never hit the network.

Dedupe rule: SKU first, then source_hash. Re-importing the same data never creates duplicates and
reports what was added, updated (hash changed) or skipped.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.contracts import Image, Product

FetchFn = Callable[[], list[dict[str, Any]]]


def _cents(value: Any) -> int | None:
    try:
        return int((Decimal(str(value)) * 100).to_integral_value())
    except (InvalidOperation, ValueError):
        return None


def normalize_paypal_product(raw: dict[str, Any], store_id: str) -> Product:
    """Accepts a PayPal Catalog Products item (id, name, description, category, image_url,
    home_url) plus optional `price` and `currency` extras some sellers attach."""
    price = raw.get("price")
    cents = _cents(price) if price is not None else None
    digest = hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest()[:16]
    image = raw.get("image_url")
    return Product(
        id=f"pp_{raw['id']}",
        store_id=store_id,
        paypal_product_id=str(raw["id"]),
        name=(raw.get("name") or "").strip() or str(raw["id"]),
        description=(raw.get("description") or "").strip(),
        price_cents=cents,
        price_text=str(price) if price is not None else None,
        currency=str(raw.get("currency") or "USD").upper(),
        stock=None,  # PayPal catalog has no inventory, so it is "not stated"
        variants=[],
        shipping=None,
        returns=None,
        sku=raw.get("sku"),
        gtin=None,
        images=[Image(url=image, alt=None)] if image else [],
        category=(str(raw["category"]).lower() if raw.get("category") else None),
        home_url=raw.get("home_url"),
        checkout_requires_human=False,
        source_hash=digest,
    )


@dataclass
class SyncReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def sync_catalog(
    existing: dict[str, Product], fetch: FetchFn, store_id: str = "store_demo"
) -> SyncReport:
    """Merge fetched PayPal products into `existing` (keyed by product id), in place."""
    report = SyncReport()
    by_key = {(p.sku or p.paypal_product_id or p.id): pid for pid, p in existing.items()}
    for raw in fetch():
        p = normalize_paypal_product(raw, store_id)
        key = p.sku or p.paypal_product_id or p.id
        pid = by_key.get(key)
        if pid is None:
            existing[p.id] = p
            by_key[key] = p.id
            report.added.append(p.id)
        elif existing[pid].source_hash == p.source_hash:
            report.skipped.append(pid)
        else:
            existing[pid] = p.model_copy(update={"id": pid})
            report.updated.append(pid)
    return report
