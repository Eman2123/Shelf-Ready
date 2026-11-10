"""Read-only audit routes for the demo store (PRD M3). No writes, no money, no keys.

The score comes from the rule engine, never from stored numbers, and every result carries the
run_id it was computed under.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.security import limiter
from app.services.audit import audit_store
from app.services.fixtures.demo_store import PUBLISHED_PRODUCTS

router = APIRouter(prefix="/api/audit", tags=["audit"])

DEMO_RUN_ID = "run_demo_audit"


@router.get("/demo-store")
@limiter.limit("60/minute")
def audit_demo_store(request: Request) -> dict:
    audit = audit_store(list(PUBLISHED_PRODUCTS.values()), run_id=DEMO_RUN_ID)
    return {
        "run_id": audit.run_id,
        "store_score": audit.store_score,
        "store_cap_applied": audit.store_cap_applied,
        "notes": audit.notes,
        "products": [
            {
                "product_id": pa.result.product_id,
                "score": pa.score,
                "issues": [i.model_dump(mode="json") for i in pa.result.issues],
                "waterfall": [
                    {"label": s.label, "delta": s.delta, "evidence": s.evidence}
                    for s in pa.waterfall
                ],
            }
            for pa in audit.products
        ],
    }
