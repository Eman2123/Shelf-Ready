"""Errors the order backend raises; the store service turns them into MCP error codes."""

from __future__ import annotations


class OrderBackendUnavailable(Exception):
    """PayPal credentials are not configured, so no order can be created."""


class OrderRejected(Exception):
    """The request itself is unusable (unknown quote, mixed currencies). Maps to an error code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
