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
    OrderStatus,
    PolicyDecision,
    PolicyResult,
    ReasonCode,
    VerifiedAgent,
)
from app.services.mcp_store.service import StoreService

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
        total = 0
        decision, reason, detail = PolicyDecision.ALLOW, ReasonCode.AUTO_APPROVED, None
        denied = False
        for item in req.items:
            quote = self.service.quotes[item.quote_id]
            product = self.service.products[item.product_id]
            total += quote.unit_price_cents * item.quantity
            if product.category not in rules.allowed_categories and not denied:
                decision, reason, denied = (
                    PolicyDecision.DENY,
                    ReasonCode.CATEGORY_NOT_ALLOWED,
                    True,
                )
                detail = f"category {product.category} is not allowed"
            elif item.quantity > rules.max_quantity and not denied:
                decision, reason, denied = PolicyDecision.DENY, ReasonCode.OVER_MAX_QUANTITY, True
                detail = f"{item.quantity} > max quantity {rules.max_quantity}"
        if not denied:
            if self.spent_today_cents + total > rules.daily_cap_cents:
                decision, reason, denied = PolicyDecision.DENY, ReasonCode.OVER_DAILY_CAP, True
                detail = f"{self.spent_today_cents + total} > daily cap {rules.daily_cap_cents}"
            elif total > rules.hard_limit_cents:
                decision, reason, denied = PolicyDecision.DENY, ReasonCode.OVER_HARD_LIMIT, True
                detail = f"{total} > hard limit {rules.hard_limit_cents}"
            elif total > rules.auto_approve_limit_cents:
                decision, reason = PolicyDecision.NEEDS_APPROVAL, ReasonCode.OVER_AUTO_APPROVE_LIMIT
                detail = f"{total} > auto-approve limit {rules.auto_approve_limit_cents}"
        status = {
            PolicyDecision.ALLOW: OrderStatus.CREATED,
            PolicyDecision.NEEDS_APPROVAL: OrderStatus.NEEDS_APPROVAL,
            PolicyDecision.DENY: OrderStatus.DENIED,
        }[decision]
        self._orders += 1
        return GuardedOrderResult(
            order_id=f"ord_sim_{self._orders:03d}",
            status=status,
            paypal_order_id=None,  # simulated: no PayPal order exists
            decision=PolicyResult(decision=decision, reason=reason, detail=detail),
            approval_url=None,
        )
