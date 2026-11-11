"""Process-wide singletons shared by main.py and the API routers (avoids circular imports).

In-memory for now: keys and spend reset when the server restarts. The Postgres repository
replaces KeyStore here without changing any caller.
"""

from __future__ import annotations

from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.keys import KeyStore
from app.services.mcp_store import StoreService

key_store = KeyStore()
# Every order call is key-checked. There is no order backend yet, so a valid key still ends in
# ORDER_BACKEND_NOT_CONNECTED (PayPal is not connected); nothing is ever created.
store_service = StoreService(PUBLISHED_PRODUCTS, DEFAULT_POLICY, verify_key=key_store.verify)
