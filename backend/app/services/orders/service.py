"""Guarded order flow (PRD M6/M8). AI never reaches this code: it takes ids and numbers only.

verify key -> price every item from its quote -> evaluate_policy -> create PayPal order with
intent AUTHORIZE -> buyer approves at PayPal -> authorize -> (ALLOW or seller approval) ->
read-only witness -> capture. Reject or timeout voids the authorization.

Status only moves forward (see RANK), so duplicate or out-of-order webhooks are harmless.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.contracts import (
    GuardedOrderRequest,
    GuardedOrderResult,
    KeyFailureReason,
    OrderDraft,
    OrderItemDraft,
    OrderStatus,
    PolicyDecision,
    PolicyResult,
    ReasonCode,
)
from app.db.models import ApprovalRow, OrderRow
from app.db.repositories import OrderRepository, _aware
from app.services.keys import KeyStore
from app.services.mcp_store.errors import OrderBackendUnavailable, OrderRejected
from app.services.mcp_store.service import StoreService
from app.services.paypal import OrderLine, PayPalError, PayPalOrders
from app.services.policy.engine import evaluate_policy

APPROVAL_TTL = timedelta(hours=24)

# Forward-only ordering. VOIDED / DENIED / FAILED are terminal and never overwritten.
RANK = {
    OrderStatus.NEEDS_APPROVAL: 0,
    OrderStatus.CREATED: 0,
    OrderStatus.AUTHORIZED: 1,
    OrderStatus.CAPTURED: 2,
    OrderStatus.REFUNDED: 3,
}
TERMINAL = {OrderStatus.VOIDED, OrderStatus.DENIED, OrderStatus.FAILED}


__all__ = ["OrderBackendUnavailable", "OrderRejected", "OrderService"]


class OrderService:
    def __init__(
        self,
        *,
        store: StoreService,
        key_store: KeyStore,
        repo: OrderRepository,
        paypal: PayPalOrders | None,
        return_url: str = "http://localhost:3000/checkout/return",
        cancel_url: str = "http://localhost:3000/checkout/cancel",
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.store = store
        self.key_store = key_store
        self.repo = repo
        self.paypal = paypal
        self.return_url = return_url
        self.cancel_url = cancel_url
        self.clock = clock

    # --- creating an order --------------------------------------------------------------
    async def create(self, req: GuardedOrderRequest) -> GuardedOrderResult:
        existing = self.repo.by_idempotency(req.idempotency_key)
        if existing is not None:
            return self._result(existing)  # retry-safe: same key, same order, no 2nd PayPal call
        if self.paypal is None:
            raise OrderBackendUnavailable

        identified = self.key_store.identify(req.agent_key)
        if not identified.ok:
            return self._denied(identified.reason)
        agent = identified.agent

        draft, lines, currency = self._draft(req, agent.store_id, agent.agent_id)
        draft = draft.model_copy(
            update={"spent_today_cents": self.key_store.spent_today(agent.key_id)}
        )
        decision = evaluate_policy(self.store.rules, draft, agent.limits)

        order = OrderRow(
            id=f"ord_{uuid.uuid4().hex[:12]}",
            idempotency_key=req.idempotency_key,
            agent_id=agent.agent_id,
            key_id=agent.key_id,
            store_id=agent.store_id,
            status=(
                OrderStatus.DENIED
                if decision.decision is PolicyDecision.DENY
                else OrderStatus.NEEDS_APPROVAL
                if decision.decision is PolicyDecision.NEEDS_APPROVAL
                else OrderStatus.CREATED
            ).value,
            currency=currency,
            total_cents=draft.total_cents,
            items=[line.model_dump(mode="json") for line in draft.items],
            decision=decision.model_dump(mode="json"),
            seller_approved=False,
        )
        if self.repo.insert_order(order) is None:  # lost a race on the idempotency key
            winner = self.repo.by_idempotency(req.idempotency_key)
            assert winner is not None
            return self._result(winner)
        self.repo.log(order.id, "POLICY_DECISION", decision.model_dump(mode="json"))
        if decision.decision is PolicyDecision.DENY:
            return self._result(order)  # money never moves: no PayPal call at all

        try:
            created = await self.paypal.create_order(
                reference_id=order.id,
                lines=lines,
                currency=currency,
                request_id=f"{order.id}-create",
                return_url=self.return_url,
                cancel_url=self.cancel_url,
            )
        except PayPalError as exc:
            order = self.repo.update(order.id, status=OrderStatus.FAILED.value, failure=str(exc))
            self.repo.log(order.id, "PAYPAL_CREATE_FAILED", {"error": str(exc)})
            return self._result(order)

        order = self.repo.update(
            order.id, paypal_order_id=created.paypal_order_id, approval_url=created.approval_url
        )
        self.repo.log(
            order.id, "PAYPAL_ORDER_CREATED", {"paypal_order_id": created.paypal_order_id}
        )
        if decision.decision is PolicyDecision.NEEDS_APPROVAL:
            self.repo.insert_approval(
                ApprovalRow(
                    id=f"apr_{uuid.uuid4().hex[:12]}",
                    order_id=order.id,
                    status="PENDING",
                    reason=decision.reason.value,
                    detail=decision.detail,
                    created_at=self.clock(),
                    expires_at=self.clock() + APPROVAL_TTL,
                )
            )
            self.repo.log(order.id, "APPROVAL_REQUESTED", {"reason": decision.reason.value})
        return self._result(order)

    def _draft(
        self, req: GuardedOrderRequest, store_id: str, agent_id: str
    ) -> tuple[OrderDraft, list[OrderLine], str]:
        """Prices come from OUR quotes, never from anything the agent sent."""
        items: list[OrderItemDraft] = []
        lines: list[OrderLine] = []
        currencies: set[str] = set()
        for item in req.items:
            quote = self.store.quotes.get(item.quote_id)
            product = self.store.products.get(item.product_id)
            if quote is None or product is None or quote.product_id != item.product_id:
                raise OrderRejected("QUOTE_UNKNOWN")
            currencies.add(quote.currency)
            items.append(
                OrderItemDraft(
                    product_id=product.id,
                    variant_sku=quote.variant_sku,
                    quantity=item.quantity,
                    unit_price_cents=quote.unit_price_cents,
                    category=product.category,
                    in_stock=quote.stock >= item.quantity,
                )
            )
            lines.append(
                OrderLine(
                    name=product.name,
                    sku=quote.variant_sku or product.sku,
                    quantity=item.quantity,
                    unit_price_cents=quote.unit_price_cents,
                )
            )
        if len(currencies) != 1:
            raise OrderRejected("MIXED_CURRENCY")
        total = sum(i.unit_price_cents * i.quantity for i in items)
        currency = currencies.pop()
        draft = OrderDraft(
            store_id=store_id,
            agent_id=agent_id,
            currency=currency,
            items=items,
            total_cents=total,
            spent_today_cents=0,
        )
        return draft, lines, currency

    # --- webhook-driven steps -----------------------------------------------------------
    async def on_buyer_approved(self, paypal_order_id: str) -> str:
        order = self.repo.by_paypal_order(paypal_order_id)
        if order is None:
            return "UNKNOWN_ORDER"
        if self._status(order) in TERMINAL or RANK.get(self._status(order), 0) >= 1:
            return "ALREADY_PROCESSED"
        assert self.paypal is not None
        try:
            witness = await self.paypal.authorize_order(
                paypal_order_id, request_id=f"{order.id}-authorize"
            )
        except PayPalError as exc:
            self.repo.update(order.id, failure=str(exc))
            self.repo.log(order.id, "AUTHORIZE_FAILED", {"error": str(exc)})
            raise
        if not witness.authorization_id:
            self.repo.update(order.id, failure="NO_AUTHORIZATION_IN_RESPONSE")
            return "NO_AUTHORIZATION"
        order = self.repo.update(
            order.id, status=OrderStatus.AUTHORIZED.value, authorization_id=witness.authorization_id
        )
        self.repo.log(order.id, "AUTHORIZED", {"authorization_id": witness.authorization_id})
        return await self._capture_if_allowed(order)

    async def _capture_if_allowed(self, order: OrderRow) -> str:
        decision = PolicyResult.model_validate(order.decision)
        if decision.decision is PolicyDecision.ALLOW or order.seller_approved:
            return await self._capture(order)
        return "WAITING_FOR_SELLER_APPROVAL"

    async def _capture(self, order: OrderRow) -> str:
        """Capture only after the read-only witness agrees with what we stored."""
        assert self.paypal is not None
        if self._status(order) is not OrderStatus.AUTHORIZED or not order.authorization_id:
            return "NOT_AUTHORIZED"
        witness = await self.paypal.witness(order.paypal_order_id or "")
        problems = []
        if witness.custom_id != order.id:
            problems.append("custom_id")
        if witness.total_cents != order.total_cents:
            problems.append("total")
        if witness.currency != order.currency:
            problems.append("currency")
        if witness.authorization_id != order.authorization_id:
            problems.append("authorization_id")
        if witness.authorization_status not in ("CREATED", "PENDING"):
            problems.append(f"authorization_status={witness.authorization_status}")
        if problems:
            await self._void_quietly(order)
            self.repo.update(
                order.id,
                status=OrderStatus.FAILED.value,
                failure="WITNESS_MISMATCH: " + ", ".join(problems),
            )
            self.repo.log(order.id, "WITNESS_MISMATCH", {"fields": problems})
            return "WITNESS_MISMATCH"
        self.repo.log(order.id, "WITNESS_OK", {"authorization_id": witness.authorization_id})
        try:
            captured = await self.paypal.capture_authorization(
                order.authorization_id,
                request_id=f"{order.id}-capture",
                amount_cents=order.total_cents,
                currency=order.currency,
            )
        except PayPalError as exc:
            self.repo.update(order.id, failure=str(exc))
            self.repo.log(order.id, "CAPTURE_FAILED", {"error": str(exc)})
            raise
        capture_id = captured.get("id")
        if captured.get("status") == "COMPLETED":
            self._mark_captured(order, capture_id)
            return "CAPTURED"
        self.repo.update(order.id, capture_id=capture_id)  # PENDING: the webhook finishes it
        return "CAPTURE_PENDING"

    def _mark_captured(self, order: OrderRow, capture_id: str | None) -> bool:
        current = self.repo.get(order.id) or order
        if RANK.get(self._status(current), -1) >= RANK[OrderStatus.CAPTURED] or (
            self._status(current) in TERMINAL
        ):
            return False
        self.repo.update(order.id, status=OrderStatus.CAPTURED.value, capture_id=capture_id)
        self.key_store.record_spend(order.key_id, order.total_cents)
        self.repo.log(order.id, "CAPTURED", {"capture_id": capture_id})
        return True

    async def on_capture_completed(
        self, capture_id: str, paypal_order_id: str | None, custom_id: str | None
    ) -> str:
        order = (
            (self.repo.get(custom_id) if custom_id else None)
            or (self.repo.by_paypal_order(paypal_order_id) if paypal_order_id else None)
            or self.repo.by_capture(capture_id)
        )
        if order is None:
            return "UNKNOWN_ORDER"
        # A capture can only come from our own capture call; if it arrives first (out of order)
        # we still record it, and the status never moves backwards.
        return "CAPTURED" if self._mark_captured(order, capture_id) else "ALREADY_PROCESSED"

    async def on_authorization_voided(self, authorization_id: str) -> str:
        order = self.repo.by_authorization(authorization_id)
        if order is None:
            return "UNKNOWN_ORDER"
        if RANK.get(self._status(order), -1) >= RANK[OrderStatus.CAPTURED]:
            return "ALREADY_PROCESSED"
        self.repo.update(order.id, status=OrderStatus.VOIDED.value)
        self.repo.log(order.id, "VOIDED", {"source": "webhook"})
        return "VOIDED"

    async def on_capture_refunded(self, refund_id: str, capture_id: str | None) -> str:
        order = self.repo.by_capture(capture_id) if capture_id else None
        if order is None:
            return "UNKNOWN_ORDER"
        if self._status(order) is OrderStatus.REFUNDED:
            return "ALREADY_PROCESSED"
        self.repo.update(order.id, status=OrderStatus.REFUNDED.value, refund_id=refund_id)
        self.repo.log(order.id, "REFUNDED", {"refund_id": refund_id, "source": "webhook"})
        return "REFUNDED"

    # --- seller actions -----------------------------------------------------------------
    async def approve(self, approval_id: str) -> dict[str, Any]:
        approval = self.repo.get_approval(approval_id)
        if approval is None:
            raise KeyError(approval_id)
        if _aware(approval.expires_at) <= self.clock():
            self.repo.decide_approval(approval_id, "EXPIRED", self.clock())
            await self._void_order(approval.order_id, "EXPIRED")
            return {"approval_id": approval_id, "status": "EXPIRED", "action": "VOIDED"}
        if not self.repo.decide_approval(approval_id, "APPROVED", self.clock()):
            return {"approval_id": approval_id, "status": self._approval_status(approval_id)}
        order = self.repo.update(approval.order_id, seller_approved=True)
        self.repo.log(order.id, "SELLER_APPROVED", {"approval_id": approval_id})
        action = "WAITING_FOR_BUYER"
        if self._status(order) is OrderStatus.AUTHORIZED:
            action = await self._capture(order)
        return {"approval_id": approval_id, "status": "APPROVED", "action": action}

    async def reject(self, approval_id: str) -> dict[str, Any]:
        approval = self.repo.get_approval(approval_id)
        if approval is None:
            raise KeyError(approval_id)
        if not self.repo.decide_approval(approval_id, "REJECTED", self.clock()):
            return {"approval_id": approval_id, "status": self._approval_status(approval_id)}
        await self._void_order(approval.order_id, "SELLER_REJECTED")
        return {"approval_id": approval_id, "status": "REJECTED", "action": "VOIDED"}

    async def expire_pending(self) -> list[str]:
        """Timeout: pending approvals past their deadline are expired and their orders voided."""
        expired = []
        for approval in self.repo.list_approvals("PENDING"):
            overdue = _aware(approval.expires_at) <= self.clock()
            if overdue and self.repo.decide_approval(approval.id, "EXPIRED", self.clock()):
                await self._void_order(approval.order_id, "EXPIRED")
                expired.append(approval.id)
        return expired

    async def refund(self, order_id: str, amount_cents: int | None = None) -> dict[str, Any]:
        order = self.repo.get(order_id)
        if order is None:
            raise KeyError(order_id)
        if self._status(order) is not OrderStatus.CAPTURED or not order.capture_id:
            return {"error": "NOT_REFUNDABLE", "status": order.status}
        if amount_cents is not None and not 0 < amount_cents <= order.total_cents:
            return {"error": "BAD_REFUND_AMOUNT"}
        assert self.paypal is not None
        data = await self.paypal.refund_capture(
            order.capture_id,
            request_id=f"{order.id}-refund-{amount_cents or 'full'}",
            amount_cents=amount_cents,
            currency=order.currency,
        )
        self.repo.update(order.id, status=OrderStatus.REFUNDED.value, refund_id=data.get("id"))
        self.repo.log(order.id, "REFUNDED", {"refund_id": data.get("id"), "amount": amount_cents})
        return {"order_id": order.id, "status": "REFUNDED", "refund_id": data.get("id")}

    # --- helpers ------------------------------------------------------------------------
    async def _void_order(self, order_id: str, why: str) -> None:
        order = self.repo.get(order_id)
        if order is None or self._status(order) in TERMINAL:
            return
        if RANK.get(self._status(order), 0) >= RANK[OrderStatus.CAPTURED]:
            return  # already captured: voiding is impossible, use refund
        await self._void_quietly(order)
        self.repo.update(order.id, status=OrderStatus.VOIDED.value)
        self.repo.log(order.id, "VOIDED", {"why": why})

    async def _void_quietly(self, order: OrderRow) -> None:
        if self.paypal is None or not order.authorization_id:
            return  # nothing authorized yet: the unapproved PayPal order just expires
        try:
            await self.paypal.void_authorization(
                order.authorization_id, request_id=f"{order.id}-void"
            )
        except PayPalError as exc:
            self.repo.log(order.id, "VOID_FAILED", {"error": str(exc)})

    def _approval_status(self, approval_id: str) -> str:
        row = self.repo.get_approval(approval_id)
        return row.status if row else "UNKNOWN"

    @staticmethod
    def _status(order: OrderRow) -> OrderStatus:
        return OrderStatus(order.status)

    def _denied(self, reason: KeyFailureReason) -> GuardedOrderResult:
        return GuardedOrderResult(
            order_id="denied",
            status=OrderStatus.DENIED,
            paypal_order_id=None,
            decision=PolicyResult(
                decision=PolicyDecision.DENY, reason=ReasonCode(reason.value), detail=None
            ),
            approval_url=None,
        )

    def _result(self, order: OrderRow) -> GuardedOrderResult:
        return GuardedOrderResult(
            order_id=order.id,
            status=OrderStatus(order.status),
            paypal_order_id=order.paypal_order_id,
            decision=PolicyResult.model_validate(order.decision),
            approval_url=order.approval_url,
        )
