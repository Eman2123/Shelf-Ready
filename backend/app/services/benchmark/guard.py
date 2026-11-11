"""BenchmarkGuard: the benchmark's money step, on the real key store and policy engine.

It never talks to PayPal and never creates a PayPal order (`paypal_order_id` is always None).
"""

from __future__ import annotations

from app.contracts import (
    GuardedOrderRequest,
    GuardedOrderResult,
    KeyLimits,
    KeyScope,
    KeyVerification,
    OrderDraft,
    OrderItemDraft,
    OrderStatus,
    PolicyDecision,
)
from app.services.keys import KeyStore
from app.services.mcp_store.service import StoreService
from app.services.policy import evaluate_policy


class BenchmarkGuard:
    """Money guard for the benchmark, built on the real KeyStore and policy engine.

    Keys: one agent key is issued by `KeyStore.create_key` (raw key in `raw_key`, only its hash
    is stored); `verify_key` is `KeyStore.verify`, so revoke, expiry and rate limits are the real
    ones. Policy: `evaluate_policy`. Still simulated: PayPal (no PayPal order is ever created).
    """

    def __init__(self, service: StoreService, spent_today_cents: int = 0) -> None:
        self.service = service
        rules = service.rules
        self.keys = KeyStore(service.clock)
        issued = self.keys.create_key(
            "agent_bench",
            "store_demo",
            [KeyScope.READ, KeyScope.QUOTE, KeyScope.ORDER],
            KeyLimits(
                per_order_max_cents=rules.hard_limit_cents,
                per_day_budget_cents=rules.daily_cap_cents,
                requests_per_minute=60,
                allowed_categories=rules.allowed_categories,
                expires_at=None,
            ),
        )
        self.raw_key, self.key_id = issued.raw_key, issued.record.key_id
        if spent_today_cents:
            self.keys.record_spend(self.key_id, spent_today_cents)
        self._orders = 0

    @property
    def spent_today_cents(self) -> int:
        return self.keys.spent_today(self.key_id)

    @property
    def revoked(self) -> bool:
        record = self.keys.get(self.key_id)
        return record is not None and record.revoked_at is not None

    @revoked.setter
    def revoked(self, value: bool) -> None:
        if value:
            self.keys.revoke(self.key_id)

    def verify_key(self, key: str) -> KeyVerification:
        return self.keys.verify(key)

    def guarded_order(self, req: GuardedOrderRequest) -> GuardedOrderResult:
        rules = self.service.rules
        lines: list[OrderItemDraft] = []
        store_id = next(iter(self.service.products.values())).store_id
        currency = next(iter(self.service.products.values())).currency
        for item in req.items:
            quote = self.service.quotes[item.quote_id]
            product = self.service.products[item.product_id]
            lines.append(
                OrderItemDraft(
                    product_id=product.id,
                    variant_sku=item.variant_sku,
                    quantity=item.quantity,
                    unit_price_cents=quote.unit_price_cents,
                    category=product.category,
                    in_stock=quote.stock > 0,
                )
            )
        draft = OrderDraft(
            store_id=store_id,
            agent_id="agent_bench",
            currency=currency,
            items=lines,
            total_cents=sum(i.unit_price_cents * i.quantity for i in lines),
            spent_today_cents=self.spent_today_cents,
        )
        # The real policy engine decides (app/services/policy). Same rules, same order of checks.
        decision = evaluate_policy(rules, draft)
        status = {
            PolicyDecision.ALLOW: OrderStatus.CREATED,
            PolicyDecision.NEEDS_APPROVAL: OrderStatus.NEEDS_APPROVAL,
            PolicyDecision.DENY: OrderStatus.DENIED,
        }[decision.decision]
        if decision.decision is PolicyDecision.ALLOW:
            self.keys.record_spend(self.key_id, draft.total_cents)
        self._orders += 1
        return GuardedOrderResult(
            order_id=f"ord_sim_{self._orders:03d}",
            status=status,
            paypal_order_id=None,  # simulated: no PayPal order exists
            decision=decision,
            approval_url=None,
        )
