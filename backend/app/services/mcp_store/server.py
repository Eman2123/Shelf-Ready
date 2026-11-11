"""MCP transport for the store tools. Tool names and inputs come from app.contracts.mcp."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from app.contracts import CreateOrderInput, GetProductInput, SearchProductsInput

from .service import StoreService


def build_server(service: StoreService, name: str = "shelf-ready-store") -> MCPServer:
    server = MCPServer(name)

    @server.tool()
    def search_products(
        query: str = "",
        max_price_cents: int | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search the store catalog. Prices are integer cents."""
        return service.search_products(
            SearchProductsInput(
                query=query, max_price_cents=max_price_cents, category=category, limit=limit
            )
        )

    @server.tool()
    def get_product(product_id: str) -> dict[str, Any]:
        """Get one product with typed variants, stock and a quote_id per variant."""
        return service.get_product(GetProductInput(product_id=product_id))

    @server.tool()
    def get_policy() -> dict[str, Any]:
        """Get the seller's order rules (limits, categories). Read before ordering."""
        return service.get_policy()

    @server.tool()
    async def create_order(
        items: list[dict[str, Any]], ship_to_country: str, idempotency_key: str, agent_key: str = ""
    ) -> dict[str, Any]:
        """Create an order. Every item needs the quote_id returned by get_product."""
        args = CreateOrderInput.model_validate(
            {"items": items, "ship_to_country": ship_to_country, "idempotency_key": idempotency_key}
        )
        return await service.acreate_order(args, agent_key)

    return server
