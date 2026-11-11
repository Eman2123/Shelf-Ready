"""Orders and approvals for the seller (PRD M6/M8/M13). Admin only: send X-Admin-Token."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.runtime import order_repo, order_service
from app.core.security import limiter, require_admin
from app.db.models import ApprovalRow, OrderRow
from app.services.paypal import PayPalError

router = APIRouter(prefix="/api", tags=["orders"], dependencies=[Depends(require_admin)])


def _order(row: OrderRow) -> dict[str, Any]:
    return {
        "order_id": row.id,
        "status": row.status,
        "agent_id": row.agent_id,
        "key_id": row.key_id,
        "currency": row.currency,
        "total_cents": row.total_cents,
        "items": row.items,
        "decision": row.decision,
        "paypal_order_id": row.paypal_order_id,
        "authorization_id": row.authorization_id,
        "capture_id": row.capture_id,
        "refund_id": row.refund_id,
        "approval_url": row.approval_url,
        "seller_approved": row.seller_approved,
        "failure": row.failure,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _approval(row: ApprovalRow) -> dict[str, Any]:
    return {
        "approval_id": row.id,
        "order_id": row.order_id,
        "status": row.status,
        "reason": row.reason,
        "detail": row.detail,
        "created_at": row.created_at.isoformat(),
        "expires_at": row.expires_at.isoformat(),
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
    }


def _paypal_failure(exc: PayPalError) -> HTTPException:
    return HTTPException(
        status_code=502, detail={"error": "PAYPAL_ERROR", "debug_id": exc.debug_id}
    )


@router.get("/orders")
@limiter.limit("120/minute")
def list_orders(request: Request) -> dict:
    return {"orders": [_order(r) for r in order_repo.list_orders()]}


@router.get("/orders/{order_id}")
@limiter.limit("120/minute")
def get_order(request: Request, order_id: str) -> dict:
    row = order_repo.get(order_id)
    if row is None:
        raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
    return {
        "order": _order(row),
        "events": [
            {"type": e.type, "detail": e.detail, "at": e.at.isoformat()}
            for e in order_repo.events(order_id)
        ],
    }


class RefundBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_cents: Annotated[int, Field(ge=1)] | None = None


@router.post("/orders/{order_id}/refund")
@limiter.limit("20/minute")
async def refund_order(request: Request, order_id: str, body: RefundBody) -> dict:
    try:
        return await order_service.refund(order_id, body.amount_cents)
    except KeyError:
        raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND") from None
    except PayPalError as exc:
        raise _paypal_failure(exc) from exc


@router.get("/approvals")
@limiter.limit("120/minute")
def list_approvals(request: Request, status: str | None = None) -> dict:
    return {"approvals": [_approval(r) for r in order_repo.list_approvals(status)]}


@router.post("/approvals/expire")
@limiter.limit("20/minute")
async def expire_approvals(request: Request) -> dict:
    try:
        return {"expired": await order_service.expire_pending()}
    except PayPalError as exc:
        raise _paypal_failure(exc) from exc


@router.post("/approvals/{approval_id}/approve")
@limiter.limit("30/minute")
async def approve(request: Request, approval_id: str) -> dict:
    try:
        return await order_service.approve(approval_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="APPROVAL_NOT_FOUND") from None
    except PayPalError as exc:
        raise _paypal_failure(exc) from exc


@router.post("/approvals/{approval_id}/reject")
@limiter.limit("30/minute")
async def reject(request: Request, approval_id: str) -> dict:
    try:
        return await order_service.reject(approval_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="APPROVAL_NOT_FOUND") from None
    except PayPalError as exc:
        raise _paypal_failure(exc) from exc
