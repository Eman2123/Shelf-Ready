"""POST /api/webhooks/paypal: PayPal sends order and payment events here."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.services.paypal.client import PayPalClient, PayPalConfigError, PayPalSettings
from app.services.webhooks.handler import InMemoryEventStore, WebhookHandler, WebhookRejected

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

event_store = InMemoryEventStore()
_handler: WebhookHandler | None = None


def get_handler() -> WebhookHandler:
    global _handler
    if _handler is None:
        try:
            settings = PayPalSettings.from_env()
        except PayPalConfigError as exc:
            raise HTTPException(status_code=503, detail="PayPal is not configured") from exc
        _handler = WebhookHandler(PayPalClient(settings), settings.webhook_id, event_store)
    return _handler


@router.post("/paypal")
async def paypal_webhook(request: Request) -> dict[str, str]:
    handler = get_handler()
    raw = await request.body()
    try:
        outcome = await handler.handle(dict(request.headers), raw)
    except WebhookRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": outcome}
