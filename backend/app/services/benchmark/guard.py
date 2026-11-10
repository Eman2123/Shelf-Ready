"""BenchmarkGuard: a stand-in for Person A's key check and policy pipeline.

The benchmark needs a money guard to run against. Until A's `verify_key` and
`create_guarded_order` are wired in, this applies the same published rules (PolicyRules) so the
AFTER runs exercise real store-side checks. It never talks to PayPal and never creates a PayPal
order. Integration step: pass A's two functions to StoreService instead of these.
"""

from __future__ import annotations

from app.contracts import (
    GuardedOrderRequest,
    GuardedOrderResult,
    KeyFailureReason,
    KeyLimits,
    KeyRejected,
    KeyScope,
    KeyVerification,
    KeyVerified,
    OrderDraft,
    OrderItemDraft,
    OrderStatus,
    PolicyDecision,
    VerifiedAgent,
)
from app.services.mcp_store.service import StoreService
from app.services.policy import evaluate_policy

BENCH_KEY = "bench-key-0001"


class BenchmarkGuard:
    def __init__(self, service: StoreService, spent_today_cents: int = 0) -> None:
        self.service = service
        self.spent_today_cents = spent_today_cents
        self.revoked = False
        self._orders = 0

    def verify_key(self, key: str) -> KeyVerification:
        if self.revoked:
            return KeyRejected(reason=KeyFailureReason.KEY_REVOKED)
        rules = self.service.rules
        return KeyVerified(
            agent=VerifiedAgent(
                agent_id="agent_bench",
                key_id="key_bench",
                store_id="store_demo",
                scopes=[KeyScope.READ, KeyScope.QUOTE, KeyScope.ORDER],
                limits=KeyLimits(
                    per_order_max_cents=rules.hard_limit_cents,
                    per_day_budget_cents=rules.daily_cap_cents,
                    requests_per_minute=60,
                    allowed_categories=rules.allowed_categories,
                    expires_at=None,
                ),
            )
        )

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
        self._orders += 1
        return GuardedOrderResult(
            order_id=f"ord_sim_{self._orders:03d}",
            status=status,
            paypal_order_id=None,  # simulated: no PayPal order exists
            decision=decision,
            approval_url=None,
        )
