"""CSV import (PRD M1): rows become normalized Products; bad rows are reported by line number.

Vague prices such as "from $20" are NOT guessed: price_cents stays None and the raw text is
kept in price_text, so the audit can flag it. Blank stock stays None ("not stated"), which is
different from 0 ("out of stock"). One bad row never stops the import.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field

from app.contracts import Image, Product, Returns, Shipping, Variant

REQUIRED_COLUMNS = ("name",)
KNOWN_COLUMNS = (
    "sku",
    "name",
    "description",
    "price",
    "currency",
    "stock",
    "category",
    "ship_regions",
    "ship_cost",
    "ship_min_days",
    "ship_max_days",
    "return_days",
    "image_url",
    "variants",
)
_PRICE_RE = re.compile(r"^\$?\s*(\d{1,6})(?:[.,](\d{1,2}))?$")


@dataclass(frozen=True)
class RowError:
    line: int  # 1-based line number in the file, the header is line 1
    field: str
    message: str


@dataclass
class ImportResult:
    products: list[Product] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    rows_seen: int = 0


class _Bad(Exception):
    def __init__(self, field_name: str, message: str) -> None:
        super().__init__(message)
        self.field_name = field_name
        self.message = message


def parse_price(text: str) -> int | None:
    """'$24.00' -> 2400. Vague or empty text -> None (never guessed). Garbage -> _Bad."""
    t = text.strip()
    if not t:
        return None
    m = _PRICE_RE.match(t)
    if m:
        whole, frac = m.group(1), (m.group(2) or "0").ljust(2, "0")
        return int(whole) * 100 + int(frac)
    if re.search(
        r"from|starting|up to|~|approx|pick|choose|varies|call|contact|ask|custom", t, re.IGNORECASE
    ):
        return None  # vague on purpose, kept as price_text
    raise _Bad("price", f"cannot read price {text!r}")


def _int(raw: str, name: str) -> int | None:
    t = raw.strip()
    if not t:
        return None
    if not re.fullmatch(r"-?\d+", t):
        raise _Bad(name, f"{name} must be a whole number, got {raw!r}")
    n = int(t)
    if n < 0:
        raise _Bad(name, f"{name} cannot be negative, got {n}")
    return n


def _row_to_product(row: dict[str, str], store_id: str, line: int) -> Product:
    name = (row.get("name") or "").strip()
    if not name:
        raise _Bad("name", "name is required")
    currency = (row.get("currency") or "USD").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise _Bad("currency", f"currency must be a 3-letter code, got {currency!r}")
    price_text = (row.get("price") or "").strip() or None
    price_cents = parse_price(price_text or "")
    stock = _int(row.get("stock") or "", "stock")
    regions = [r.strip().upper() for r in (row.get("ship_regions") or "").split("|") if r.strip()]
    for r in regions:
        if not re.fullmatch(r"[A-Z]{2}", r):
            raise _Bad("ship_regions", f"region must be a 2-letter code, got {r!r}")
    ship_cost = parse_price(row.get("ship_cost") or "")
    min_d, max_d = (
        _int(row.get("ship_min_days") or "", "ship_min_days"),
        _int(row.get("ship_max_days") or "", "ship_max_days"),
    )
    if min_d is not None and max_d is not None and min_d > max_d:
        raise _Bad("ship_min_days", "ship_min_days is larger than ship_max_days")
    shipping = (
        Shipping(regions=regions, cost_cents=ship_cost, min_days=min_d, max_days=max_d)
        if (regions or ship_cost is not None or min_d is not None or max_d is not None)
        else None
    )
    ret_days = _int(row.get("return_days") or "", "return_days")
    returns = (
        Returns(window_days=ret_days, free_returns=None, policy_text=None)
        if ret_days is not None
        else None
    )
    variants: list[Variant] = []
    for part in [p for p in (row.get("variants") or "").split("|") if p.strip()]:
        # "size=M,color=blue:3" -> attributes and stock
        attrs_part, _, stock_part = part.partition(":")
        attrs = {}
        for kv in attrs_part.split(","):
            k, sep, v = kv.partition("=")
            if not sep or not k.strip() or not v.strip():
                raise _Bad("variants", f"variant {part!r} must look like size=M,color=blue:3")
            attrs[k.strip()] = v.strip()
        variants.append(
            Variant(
                sku=None,
                attributes=attrs,
                price_cents=price_cents,
                stock=_int(stock_part, "variants") if stock_part.strip() else None,
            )
        )
    sku = (row.get("sku") or "").strip() or None
    image = (row.get("image_url") or "").strip()
    normalized = {
        "name": name,
        "sku": sku,
        "price_text": price_text,
        "stock": stock,
        "regions": regions,
        "ship_cost": ship_cost,
        "ret": ret_days,
    }
    digest = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()[:16]
    return Product(
        id=f"imp_{sku.lower() if sku else f'line{line}'}",
        store_id=store_id,
        paypal_product_id=None,
        name=name,
        description=(row.get("description") or "").strip(),
        price_cents=price_cents,
        price_text=price_text,
        currency=currency,
        stock=stock,
        variants=variants,
        shipping=shipping,
        returns=returns,
        sku=sku,
        gtin=None,
        images=[Image(url=image, alt=None)] if image else [],
        category=(row.get("category") or "").strip() or None,
        home_url=None,
        checkout_requires_human=False,
        source_hash=digest,
    )


def import_csv(text: str, store_id: str = "store_demo") -> ImportResult:
    result = ImportResult()
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    try:
        header = [h.strip().lower() for h in next(reader)]
    except StopIteration:
        result.errors.append(RowError(1, "file", "file is empty"))
        return result
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        result.errors.append(RowError(1, "header", f"missing required column(s): {missing}"))
        return result
    seen_sku: dict[str, int] = {}
    for rec in reader:
        line = reader.line_num
        if not any(c.strip() for c in rec):
            continue  # blank line
        result.rows_seen += 1
        if len(rec) != len(header):
            result.errors.append(
                RowError(line, "row", f"expected {len(header)} columns, found {len(rec)}")
            )
            continue
        row = dict(zip(header, rec, strict=True))
        try:
            product = _row_to_product(row, store_id, line)
        except _Bad as e:
            result.errors.append(RowError(line, e.field_name, e.message))
            continue
        if product.sku:
            if product.sku in seen_sku:
                result.errors.append(
                    RowError(
                        line,
                        "sku",
                        f"duplicate sku {product.sku!r}, first on line {seen_sku[product.sku]}",
                    )
                )
                continue
            seen_sku[product.sku] = line
        result.products.append(product)
    return result
