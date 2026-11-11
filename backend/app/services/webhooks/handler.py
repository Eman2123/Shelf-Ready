"""PayPal webhook verification + idempotent event handling.

Events are verified through PayPal's verify-webhook-signature API, then deduped by event id.
Webhooks only RECORD state. They never trigger a capture, so duplicate, delayed or
out-of-order delivery cannot cause a double capture.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.services.paypal.client import PayPalClient

REQUIRED_HEADERS = (
    "paypal-transmission-id",
    "paypal-transmission-time",
    "paypal-transmission-sig",
    "paypal-cert-url",
    "paypal-auth-algo",
)


class WebhookRejected(Exception):
    """Signature missing, malformed or not verified by PayPal."""


class EventStore(Protocol):
    def add_if_new(self, event_id: str, event: dict[str, Any]) -> bool:
        """Store the event. Return False if this event id was already stored."""


@dataclass
class InMemoryEventStore:
    """Default store. A Postgres table with a UNIQUE paypal_event_id replaces it."""

    events: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_if_new(self, event_id: str, event: dict[str, Any]) -> bool:
        if event_id in self.events:
            return False
        self.events[event_id] = event
        return True


async def verify_signature(
    client: PayPalClient, webhook_id: str, headers: Mapping[str, str], event: dict[str, Any]
) -> bool:
    lowered = {k.lower(): v for k, v in headers.items()}
    if not webhook_id or any(h not in lowered for h in REQUIRED_HEADERS):
        return False
    result = await client.post(
        "/v1/notifications/verify-webhook-signature",
        json={
            "auth_algo": lowered["paypal-auth-algo"],
            "cert_url": lowered["paypal-cert-url"],
            "transmission_id": lowered["paypal-transmission-id"],
            "transmission_sig": lowered["paypal-transmission-sig"],
            "transmission_time": lowered["paypal-transmission-time"],
            "webhook_id": webhook_id,
            "webhook_event": event,
        },
    )
    return result.get("verification_status") == "SUCCESS"


class WebhookHandler:
    def __init__(self, client: PayPalClient, webhook_id: str, store: EventStore) -> None:
        self.client = client
        self.webhook_id = webhook_id
        self.store = store

    async def handle(self, headers: Mapping[str, str], raw_body: bytes) -> str:
        """Return "processed" or "duplicate". Raise WebhookRejected if not verified."""
        try:
            event = json.loads(raw_body)
        except ValueError as exc:
            raise WebhookRejected("body is not valid JSON") from exc
        if not isinstance(event, dict) or not event.get("id"):
            raise WebhookRejected("event has no id")
        if not await verify_signature(self.client, self.webhook_id, headers, event):
            raise WebhookRejected("signature not verified")
        is_new = self.store.add_if_new(str(event["id"]), event)
        return "processed" if is_new else "duplicate"
