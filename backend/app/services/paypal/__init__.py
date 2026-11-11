"""PayPal sandbox integration: OAuth client, Orders/Payments, webhooks, catalog."""

from .catalog import fetch_catalog_products
from .client import PayPalClient, PayPalConfigError, PayPalError, PayPalSettings
from .orders import OrderLine, OrderWitness, PayPalOrder, PayPalOrders
from .webhooks import WebhookVerificationError, verify_webhook

__all__ = [
    "OrderLine",
    "OrderWitness",
    "PayPalClient",
    "PayPalConfigError",
    "PayPalError",
    "PayPalOrder",
    "PayPalOrders",
    "PayPalSettings",
    "WebhookVerificationError",
    "fetch_catalog_products",
    "verify_webhook",
]
