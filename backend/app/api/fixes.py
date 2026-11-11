"""Provenance validator as a read-only route (PRD 4.2). Stateless: nothing is stored or applied.

It answers one question: is this proposed value backed by this source text? The verdict is made
by deterministic code, never a model.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.contracts import FixMethod
from app.core.security import limiter
from app.services.fixes import validate_value

router = APIRouter(prefix="/api/fixes", tags=["fixes"])


class ValidateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_text: Annotated[str, Field(max_length=20_000)]
    proposed: Any
    snippet: Annotated[str, Field(max_length=2_000)]
    method: FixMethod


@router.post("/validate")
@limiter.limit("60/minute")
def validate(request: Request, body: ValidateBody) -> dict:
    verdict = validate_value(body.source_text, body.proposed, body.snippet, body.method)
    return {
        "status": verdict.status.value,
        "confidence": verdict.confidence,
        "reason": verdict.reason,
    }
