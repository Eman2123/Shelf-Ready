from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import agent_ready, audit
from app.services.fixtures.demo_store import DEFAULT_POLICY, PUBLISHED_PRODUCTS
from app.services.mcp_store import StoreService
from app.services.mcp_store.server import build_server

# Demo wiring: published demo catalog, no order backend yet (A's create_guarded_order plugs in here).
store_service = StoreService(PUBLISHED_PRODUCTS, DEFAULT_POLICY)
mcp_server = build_server(store_service)
mcp_app = mcp_server.streamable_http_app()  # serves POST /mcp


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="Shelf Ready API", version="0.1.0", lifespan=lifespan)
app.include_router(agent_ready.router)
app.include_router(audit.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": "paypal-sandbox"}


# Mounted last so the routes above win; the MCP app only answers /mcp.
app.mount("/", mcp_app)
