"""Public agent-ready routes: manifest and per-product JSON-LD."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.services.agent_ready import build_manifest, product_to_jsonld
from app.services.fixtures.demo_store import CURRENCY, PUBLISHED_PRODUCTS, STORE_ID, STORE_NAME

router = APIRouter()


@router.get("/.well-known/agent-store.json")
def agent_store_manifest(request: Request) -> dict:
    return build_manifest(
        store_id=STORE_ID, name=STORE_NAME, currency=CURRENCY, base_url=str(request.base_url)
    )


@router.get("/agent-ready/products/{product_id}/jsonld")
def product_jsonld(product_id: str) -> JSONResponse:
    product = PUBLISHED_PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="PRODUCT_NOT_FOUND")
    return JSONResponse(product_to_jsonld(product), media_type="application/ld+json")
