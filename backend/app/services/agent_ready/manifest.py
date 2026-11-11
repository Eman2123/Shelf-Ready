"""/.well-known/agent-store.json: tells an agent where the store MCP is and what it can do."""

from __future__ import annotations

from typing import Any

from app.contracts import STORE_TOOL_NAMES, KeyScope


def build_manifest(*, store_id: str, name: str, currency: str, base_url: str) -> dict[str, Any]:
    base = base_url.rstrip("/")
    return {
        "schema_version": "0.1",
        "environment": "paypal-sandbox",
        "store": {"id": store_id, "name": name, "currency": currency},
        "mcp": {
            "url": f"{base}/mcp",
            "transport": "streamable-http",
            "tools": list(STORE_TOOL_NAMES),
        },
        "auth": {"type": "bearer", "scopes": [s.value for s in KeyScope]},
        "catalog": {"product_jsonld": f"{base}/agent-ready/products/{{product_id}}/jsonld"},
        "notes": "Orders need a quote_id from get_product. Prices are integer cents.",
    }
