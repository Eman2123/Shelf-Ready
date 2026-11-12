"""Process-wide singletons shared by main.py and the API routers (avoids circular imports).

DATABASE_URL decides where keys, orders, approvals and webhook events live. Unset means an
in-memory SQLite database (demo and tests; resets on restart). Set it to Postgres for deploys.
PayPal is connected only when PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are set; without them an
order call ends in ORDER_BACKEND_NOT_CONNECTED and nothing is ever created.
"""

from __future__ import annotations

import os

from app.core import env as _env  # noqa: F401  (loads backend/.env before anything reads it)
from app.db import Base, make_engine, make_session_factory
from app.db.repositories import OrderRepository, SqlKeyRepository
from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.keys import KeyStore
from app.services.mcp_store import StoreService
from app.services.orders import OrderService
from app.services.paypal import PayPalClient, PayPalConfigError, PayPalOrders, PayPalSettings
from app.services.webhooks import WebhookHandler

engine = make_engine()
if engine.dialect.name == "sqlite":
    Base.metadata.create_all(engine)  # Postgres schema comes from `alembic upgrade head`
session_factory = make_session_factory(engine)

key_store = KeyStore(repository=SqlKeyRepository(session_factory))
store_service = StoreService(PUBLISHED_PRODUCTS, DEFAULT_POLICY, verify_key=key_store.verify)

order_repo = OrderRepository(session_factory)

paypal_client: PayPalClient | None
try:
    paypal_client = PayPalClient(PayPalSettings.from_env())
except PayPalConfigError:
    paypal_client = None

_app_url = os.environ.get("APP_URL", "http://localhost:3000").rstrip("/")
order_service = OrderService(
    store=store_service,
    key_store=key_store,
    repo=order_repo,
    paypal=PayPalOrders(paypal_client) if paypal_client else None,
    return_url=f"{_app_url}/checkout/return",
    cancel_url=f"{_app_url}/checkout/cancel",
)
store_service.async_guarded_order = order_service.create
webhook_handler = WebhookHandler(order_repo, order_service)
