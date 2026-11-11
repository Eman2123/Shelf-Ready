"""PayPal webhook signature verification (uses PayPal's own verification API)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .client import PayPalClient, PayPalConfigError

REQUIRED_HEADERS = (
    "paypal-auth-algo",
    "paypal-cert-url",
    "paypal-transmission-id",
    "paypal-transmission-sig",
    "paypal-transmission-time",
)


class WebhookVerificationError(Exception):
    """The webhook could not be proven to come from PayPal."""


async def verify_webhook(
    client: PayPalClient, headers: Mapping[str, str], raw_body: bytes
) -> dict[str, Any]:
    """Return the parsed event only if PayPal says its signature is valid. Otherwise raise.

    Fails closed: missing headers, no webhook id configured, an invalid body, a PayPal error or
    anything other than SUCCESS all reject the event.
    """
    lowered = {k.lower(): v for k, v in headers.items()}
    missing = [h for h in REQUIRED_HEADERS if not lowered.get(h)]
    if missing:
        raise WebhookVerificationError(f"missing headers: {', '.join(missing)}")
    webhook_id = client.settings.webhook_id
    if not webhook_id:
        raise PayPalConfigError("PAYPAL_WEBHOOK_ID is not set; cannot verify webhooks.")
    try:
        event = json.loads(raw_body)
    except ValueError as exc:
        raise WebhookVerificationError("body is not valid JSON") from exc
    if not isinstance(event, dict) or not event.get("id"):
        raise WebhookVerificationError("event has no id")
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
    if result.get("verification_status") != "SUCCESS":
        raise WebhookVerificationError("PayPal rejected the signature")
    return event
