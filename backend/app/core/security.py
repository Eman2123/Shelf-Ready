"""Security headers, admin check and the shared rate limiter (PRD M15).

Headers are added by a pure ASGI middleware, not BaseHTTPMiddleware, so the streaming MCP
endpoint is not buffered.
"""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.types import ASGIApp, Message, Receive, Scope, Send

limiter = Limiter(key_func=get_remote_address)

_DOC_PATHS = ("/docs", "/redoc", "/openapi.json")
_BASE_HEADERS = {
    b"x-content-type-options": b"nosniff",
    b"x-frame-options": b"DENY",
    b"referrer-policy": b"no-referrer",
    b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
}
_CSP = b"default-src 'none'; frame-ancestors 'none'"
_HSTS = b"max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        headers = dict(scope.get("headers", []))
        https = scope.get("scheme") == "https" or headers.get(b"x-forwarded-proto") == b"https"

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                out = list(message.get("headers", []))
                present = {k.lower() for k, _ in out}
                extra = dict(_BASE_HEADERS)
                if not path.startswith(_DOC_PATHS):  # Swagger UI needs scripts; the API does not
                    extra[b"content-security-policy"] = _CSP
                if https:
                    extra[b"strict-transport-security"] = _HSTS
                out.extend((k, v) for k, v in extra.items() if k not in present)
                message = {**message, "headers": out}
            await send(message)

        await self.app(scope, receive, send_with_headers)


def require_admin(request: Request) -> None:
    """Guards key management. ADMIN_TOKEN unset means the endpoints are switched off."""
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_DISABLED")
    sent = request.headers.get("x-admin-token", "")
    if not secrets.compare_digest(sent.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="ADMIN_TOKEN_INVALID")
