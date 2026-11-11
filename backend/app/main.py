import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import agent_ready, audit, fixes, keys, webhooks_paypal
from app.core.runtime import store_service
from app.core.security import SecurityHeadersMiddleware, limiter
from app.services.mcp_store.server import build_server

# Demo wiring: published demo catalog, every order call key-checked, no order backend yet
# (the PayPal create_guarded_order plugs in here).
mcp_server = build_server(store_service)
mcp_app = mcp_server.streamable_http_app()  # serves POST /mcp


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="Shelf Ready API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("APP_URL", "http://localhost:3000")],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.include_router(agent_ready.router)
app.include_router(audit.router)
app.include_router(fixes.router)
app.include_router(keys.router)
app.include_router(webhooks_paypal.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": "paypal-sandbox"}


# Mounted last so the routes above win; the MCP app only answers /mcp.
app.mount("/", mcp_app)
