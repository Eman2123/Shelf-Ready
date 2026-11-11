"""Scripted baseline buyer agents. They are deterministic and use NO language model.

BEFORE reads HTML pages with `fetch_page` and records a purchase intent; it believes what the
page says, including instructions hidden in product text (a deliberately naive reader).
AFTER talks to the store MCP tools only and treats product text as data.

Both get the same task. The point of the benchmark is what the *store* makes possible, so
`agent_config` always says "scripted, no LLM". A real LLM agent can be plugged in later by
implementing the same `run()` shape.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.contracts import (
    AgentStep,
    CreateOrderInput,
    GetProductInput,
    GuardedOrderItem,
    SearchProductsInput,
)
from app.services.benchmark.guard import BenchmarkGuard
from app.services.benchmark.tasks import TaskSpec, Want
from app.services.fixtures.messy_store import MESSY_PAGES, PAGE_FOR_PRODUCT
from app.services.mcp_store.service import StoreService

BEFORE_CONFIG = "scripted-page-reader-v1 (no LLM, deterministic)"
AFTER_CONFIG = "scripted-mcp-agent-v1 (no LLM, deterministic)"


@dataclass
class AgentResult:
    steps: list[AgentStep]
    final: dict[str, Any]
    duration_ms: int


@dataclass
class _Trace:
    steps: list[AgentStep] = field(default_factory=list)
    started: float = field(default_factory=time.perf_counter)

    def call(
        self, tool: str, args: Any, fn: Callable[[], Any], html_bytes: int = 0, show: Any = None
    ) -> Any:
        out = fn()
        ok = not (isinstance(out, dict) and "error" in out)
        self.steps.append(
            AgentStep(
                index=len(self.steps),
                tool=tool,
                input=args,
                output=out if show is None else show,
                ok=ok,
                html_bytes=html_bytes,
            )
        )
        return out

    def done(self, final: dict[str, Any]) -> AgentResult:
        ms = int((time.perf_counter() - self.started) * 1000)
        return AgentResult(self.steps, final, ms)


# --------------------------------------------------------------------------- BEFORE
_LINK = re.compile(r'<a href="([^"]+)">([^<]+)</a>')
_PRICE = re.compile(r'class="price">([^<]*)<')
_INJECTED_QTY = re.compile(r"order\s+(\d+)\s+of\s+these", re.IGNORECASE)


def _price_cents_guess(price_text: str) -> int | None:
    m = re.search(r"\$(\d+(?:\.\d{2})?)", price_text)
    return round(float(m.group(1)) * 100) if m else None  # "from $20" -> 2000: a guess


def run_before(spec: TaskSpec) -> AgentResult:
    t = _Trace()
    listing = MESSY_PAGES["/demo-store"]
    t.call(
        "fetch_page",
        {"url": "/demo-store"},
        lambda: "HTML listing",
        len(listing.encode()),
        show="HTML: store listing, prices as text",
    )
    items: list[dict[str, Any]] = []
    for want in spec.wants:
        link = next(
            (h for h, label in _LINK.findall(listing) if want.query.lower() in label.lower()), None
        )
        if link is None:
            return t.done({"kind": "FAILED", "reason": f"no link for '{want.query}'"})
        page = MESSY_PAGES[link]
        price_text = m.group(1) if (m := _PRICE.search(page)) else ""
        t.call(
            "fetch_page",
            {"url": link},
            lambda: "HTML product page",
            len(page.encode()),
            show=f"HTML: price text '{price_text}', no stock, no variant list",
        )
        qty = want.qty
        injected = _INJECTED_QTY.search(page)
        if injected:
            qty = int(injected.group(1))  # naive reader obeys instructions found in page text
        product_id = next((p for p, path in PAGE_FOR_PRODUCT.items() if path == link), link)
        items.append(
            {
                "product_id": product_id,
                "variant_sku": None,
                "quantity": qty,
                "unit_price_cents": _price_cents_guess(price_text),
            }
        )
    intent = {"items": items, "ship_to": spec.ship_to}
    t.call(
        "record_intent", intent, lambda: {"recorded": True, "note": "no money moves in BEFORE mode"}
    )
    return t.done({"kind": "INTENT_RECORDED", "items": items, "ship_to": spec.ship_to})


# --------------------------------------------------------------------------- AFTER
def _pick_variant(variants: list[dict[str, Any]], want: Want) -> list[dict[str, Any]]:
    def ok(v: dict[str, Any]) -> bool:
        a = {k.lower(): str(x).lower() for k, x in v["attributes"].items()}
        return (want.color is None or a.get("color") == want.color.lower()) and (
            want.size is None or a.get("size") == want.size.lower()
        )

    return [v for v in variants if ok(v)]


def run_after(spec: TaskSpec, service: StoreService, guard: BenchmarkGuard) -> AgentResult:
    t = _Trace()
    t.call("get_policy", {}, service.get_policy)
    order_items: list[GuardedOrderItem] = []
    first_product_id: str | None = None
    for want in spec.wants:
        found = t.call(
            "search_products",
            {"query": want.query, "max_price_cents": spec.max_price_cents},
            lambda w=want: service.search_products(
                SearchProductsInput(query=w.query, max_price_cents=spec.max_price_cents)
            ),
        )
        if not found:
            return t.done({"kind": "FAILED", "reason": f"no product for '{want.query}'"})
        pid = found[0]["product_id"]
        detail = t.call(
            "get_product",
            {"product_id": pid},
            lambda p=pid: service.get_product(GetProductInput(product_id=p)),
        )
        product, quotes = detail["product"], detail["quotes"]
        first_product_id = first_product_id or pid
        sku: str | None = None
        stock = product["stock"]
        if product["variants"]:
            cands = _pick_variant(product["variants"], want)
            if want.size is None and len(cands) > 1:
                sizes = sorted(v["attributes"].get("size", "?") for v in cands)
                return t.done(
                    {"kind": "ASKED_CLARIFYING_QUESTION", "question": f"Which size? {sizes}"}
                )
            if not cands:
                return t.done({"kind": "FAILED", "reason": "no matching variant"})
            sku, stock = cands[0]["sku"], cands[0]["stock"]
        if stock is not None and stock < want.qty:
            return t.done({"kind": "REPORTED_OUT_OF_STOCK", "sku": sku, "stock": stock})
        regions = (product.get("shipping") or {}).get("regions", [])
        if spec.ship_to not in regions:
            return t.done(
                {"kind": "REPORTED_CANNOT_SHIP", "ship_to": spec.ship_to, "regions": regions}
            )
        quote = next(q for q in quotes if q["variant_sku"] == sku)
        order_items.append(
            GuardedOrderItem(
                product_id=pid, variant_sku=sku, quantity=want.qty, quote_id=quote["quote_id"]
            )
        )

    # the world moves between quote and order (scenario), outside the agent's control
    if spec.scenario.price_change_to_cents is not None and first_product_id:
        service.products[first_product_id] = service.products[first_product_id].model_copy(
            update={
                "price_cents": spec.scenario.price_change_to_cents,
                "variants": [
                    v.model_copy(update={"price_cents": spec.scenario.price_change_to_cents})
                    for v in service.products[first_product_id].variants
                ],
            }
        )
    if spec.scenario.revoke_key_before_order:
        guard.revoked = True

    args = CreateOrderInput(
        items=order_items,
        ship_to_country=spec.ship_to,
        idempotency_key=f"idem-{spec.task.id}-bench",
    )
    result = t.call(
        "create_order",
        args.model_dump(mode="json"),
        lambda: service.create_order(args, guard.raw_key),
    )
    items_out = [
        {
            **i.model_dump(mode="json"),
            "unit_price_cents": service.quotes[i.quote_id].unit_price_cents,
        }
        for i in order_items
    ]
    if "error" in result:
        err = result["error"]
        kind = {
            "PRICE_CHANGED": "PRICE_CHANGE_DETECTED",
            "STOCK_CHANGED": "REPORTED_OUT_OF_STOCK",
        }.get(err, "DENIED_BY_POLICY")
        return t.done({"kind": kind, "error": err})
    status = result["status"]
    kind = {"NEEDS_APPROVAL": "STOPPED_FOR_APPROVAL", "DENIED": "DENIED_BY_POLICY"}.get(
        status, "ORDER_CREATED"
    )
    return t.done(
        {
            "kind": kind,
            "status": status,
            "reason": result["decision"]["reason"],
            "items": items_out,
            "order_id": result["order_id"],
        }
    )
