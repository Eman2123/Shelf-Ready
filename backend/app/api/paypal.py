"""PayPal-facing endpoints: webhook receiver and catalog preview."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.runtime import order_repo, paypal_client, store_service, webhook_handler
from app.core.security import limiter, require_admin
from app.services.connector.normalize import sync_catalog
from app.services.paypal import (
    PayPalConfigError,
    PayPalError,
    WebhookVerificationError,
    fetch_catalog_products,
    verify_webhook,
)

router = APIRouter(tags=["paypal"])


@router.post("/api/webhooks/paypal")
@limiter.limit("300/minute")
async def paypal_webhook(request: Request) -> dict:
    """Public URL PayPal calls. Nothing is trusted until PayPal's verify API says SUCCESS."""
    if paypal_client is None:
        raise HTTPException(status_code=503, detail="PAYPAL_NOT_CONNECTED")
    raw = await request.body()
    try:
        event = await verify_webhook(paypal_client, request.headers, raw)
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=400, detail=f"WEBHOOK_REJECTED: {exc}") from None
    except PayPalConfigError:
        raise HTTPException(status_code=503, detail="WEBHOOK_ID_NOT_SET") from None
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail="PAYPAL_VERIFY_FAILED") from exc
    try:
        outcome = await webhook_handler.handle(event)
    except PayPalError as exc:
        # 5xx makes PayPal redeliver; the event id was released so it is processed again
        raise HTTPException(status_code=500, detail="HANDLER_FAILED") from exc
    return {"event_id": event["id"], "outcome": outcome}


@router.get("/api/webhooks/events", dependencies=[Depends(require_admin)])
@limiter.limit("60/minute")
def webhook_log(request: Request) -> dict:
    return {
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "resource_id": e.resource_id,
                "outcome": e.outcome,
                "received_at": e.received_at.isoformat(),
            }
            for e in order_repo.list_events()
        ]
    }


@router.post("/api/paypal/catalog/sync", dependencies=[Depends(require_admin)])
@limiter.limit("10/minute")
async def catalog_sync(request: Request) -> dict:
    """Read the seller's PayPal Catalog Products and show what a sync would add or update.
    Works on a copy: the published demo catalog is not changed."""
    if paypal_client is None:
        raise HTTPException(status_code=503, detail="PAYPAL_NOT_CONNECTED")
    try:
        raw = await fetch_catalog_products(paypal_client)
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail="PAYPAL_CATALOG_FAILED") from exc
    merged = dict(store_service.products)
    report = sync_catalog(merged, lambda: raw)
    return {
        "fetched": len(raw),
        "added": report.added,
        "updated": report.updated,
        "skipped": report.skipped,
    }
