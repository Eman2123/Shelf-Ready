"""Dispatch verified PayPal events to the order service. Dedupes by event id."""

from __future__ import annotations

from typing import Any

from app.db.repositories import OrderRepository
from app.services.orders import OrderService


class WebhookHandler:
    def __init__(self, repo: OrderRepository, orders: OrderService) -> None:
        self.repo = repo
        self.orders = orders

    async def handle(self, event: dict[str, Any]) -> str:
        """Returns the outcome. A redelivered event id returns DUPLICATE and does nothing."""
        event_id = str(event["id"])
        event_type = str(event.get("event_type", ""))
        resource = event.get("resource") or {}
        if not self.repo.claim_event(event_id, event_type, resource.get("id"), event):
            return "DUPLICATE"
        try:
            outcome = await self._dispatch(event_type, resource)
        except Exception:
            self.repo.release_event(event_id)  # let PayPal's retry process it again
            raise
        self.repo.set_event_outcome(event_id, outcome)
        return outcome

    async def _dispatch(self, event_type: str, resource: dict[str, Any]) -> str:
        if event_type == "CHECKOUT.ORDER.APPROVED":
            return await self.orders.on_buyer_approved(resource["id"])
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            related = (resource.get("supplementary_data") or {}).get("related_ids") or {}
            return await self.orders.on_capture_completed(
                resource["id"], related.get("order_id"), resource.get("custom_id")
            )
        if event_type == "PAYMENT.AUTHORIZATION.VOIDED":
            return await self.orders.on_authorization_voided(resource["id"])
        if event_type in ("PAYMENT.CAPTURE.REFUNDED", "PAYMENT.REFUND.COMPLETED"):
            capture_id = next(
                (
                    link["href"].rstrip("/").split("/")[-1]
                    for link in resource.get("links", [])
                    if link.get("rel") == "up" and "/captures/" in link.get("href", "")
                ),
                None,
            )
            return await self.orders.on_capture_refunded(resource["id"], capture_id)
        return "IGNORED"
