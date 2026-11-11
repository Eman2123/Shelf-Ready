"""PayPal REST client: OAuth token manager + thin async HTTP wrapper.

Sandbox only. Secrets come from environment variables, never from code.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api-m.sandbox.paypal.com"
TOKEN_PATH = "/v1/oauth2/token"
WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
# Refresh the token this many seconds before it really expires.
EXPIRY_MARGIN_SECONDS = 60


class PayPalError(Exception):
    """Raised when PayPal returns an error response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        debug_id: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(f"PayPal {status_code}: {message} (debug_id={debug_id})")
        self.status_code = status_code
        self.message = message
        self.debug_id = debug_id
        self.details = details


class PayPalConfigError(Exception):
    """Raised when required PayPal environment variables are missing."""


@dataclass(frozen=True)
class PayPalSettings:
    client_id: str
    client_secret: str
    base_url: str = DEFAULT_BASE_URL
    webhook_id: str = ""

    @classmethod
    def from_env(cls) -> PayPalSettings:
        client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            raise PayPalConfigError(
                "PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set in the environment."
            )
        # .env.example documents PAYPAL_API_BASE; PAYPAL_BASE_URL is accepted too.
        base_url = (
            os.getenv("PAYPAL_API_BASE") or os.getenv("PAYPAL_BASE_URL") or DEFAULT_BASE_URL
        ).strip()
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url.rstrip("/"),
            webhook_id=os.getenv("PAYPAL_WEBHOOK_ID", "").strip(),
        )


class PayPalClient:
    """Async PayPal client with cached, auto-refreshing OAuth token."""

    def __init__(
        self,
        settings: PayPalSettings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or PayPalSettings.from_env()
        self._http = http_client or httpx.AsyncClient(timeout=30.0)
        self._owns_http = http_client is None
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    # ---- token management -------------------------------------------------

    def _token_is_valid(self) -> bool:
        return self._token is not None and time.monotonic() < self._token_expires_at

    def invalidate_token(self) -> None:
        self._token = None
        self._token_expires_at = 0.0

    async def get_access_token(self) -> str:
        if self._token_is_valid():
            return self._token  # type: ignore[return-value]
        async with self._lock:
            # Another coroutine may have refreshed while we waited.
            if self._token_is_valid():
                return self._token  # type: ignore[return-value]
            response = await self._http.post(
                f"{self.settings.base_url}{TOKEN_PATH}",
                auth=(self.settings.client_id, self.settings.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"},
            )
            if response.status_code >= 400:
                raise self._to_error(response)
            payload = response.json()
            self._token = payload["access_token"]
            expires_in = int(payload.get("expires_in", 300))
            self._token_expires_at = time.monotonic() + max(expires_in - EXPIRY_MARGIN_SECONDS, 0)
            return self._token

    # ---- requests ---------------------------------------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request. Writes always carry PayPal-Request-Id.

        Pass the same request_id when retrying the same logical write, so
        PayPal treats it as one operation (idempotency).
        """
        method = method.upper()
        response = await self._send(method, path, json, params, request_id, extra_headers)
        if response.status_code == 401:
            # Token may have been revoked or expired early: refresh once and retry.
            self.invalidate_token()
            response = await self._send(method, path, json, params, request_id, extra_headers)
        if response.status_code >= 400:
            raise self._to_error(response)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    async def _send(
        self,
        method: str,
        path: str,
        json: Any,
        params: dict[str, Any] | None,
        request_id: str | None,
        extra_headers: dict[str, str] | None,
    ) -> httpx.Response:
        token = await self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if method in WRITE_METHODS:
            headers["PayPal-Request-Id"] = request_id or str(uuid.uuid4())
        if extra_headers:
            headers.update(extra_headers)
        return await self._http.request(
            method,
            f"{self.settings.base_url}{path}",
            json=json,
            params=params,
            headers=headers,
        )

    @staticmethod
    def _to_error(response: httpx.Response) -> PayPalError:
        try:
            body = response.json()
        except ValueError:
            body = {}
        message = (
            body.get("message")
            or body.get("error_description")
            or body.get("error")
            or response.text[:200]
            or "Unknown PayPal error"
        )
        return PayPalError(
            status_code=response.status_code,
            message=str(message),
            debug_id=body.get("debug_id"),
            details=body.get("details"),
        )

    # ---- convenience helpers ---------------------------------------------

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("POST", path, **kwargs)
