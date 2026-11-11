"""Agent key management (PRD M7). Admin only: send X-Admin-Token. Off when ADMIN_TOKEN is unset.

The raw key is in the create response once and cannot be read again. Records never include the
hash. Revoke is the kill switch and takes effect on the agent's next request.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.contracts import KeyLimits, KeyScope
from app.core.runtime import key_store
from app.core.security import limiter, require_admin
from app.services.fixtures.demo_store import STORE_ID
from app.services.keys import KeyRecord

router = APIRouter(prefix="/api/keys", tags=["keys"], dependencies=[Depends(require_admin)])


class CreateKeyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: Annotated[str, Field(min_length=1, max_length=64)]
    scopes: Annotated[list[KeyScope], Field(min_length=1)]
    per_order_max_cents: Annotated[int, Field(ge=0)]
    per_day_budget_cents: Annotated[int, Field(ge=0)]
    requests_per_minute: Annotated[int, Field(ge=1, le=10_000)] = 60
    allowed_categories: list[str] = []
    expires_in_hours: Annotated[int, Field(ge=1, le=24 * 365)] | None = None


def _public(record: KeyRecord) -> dict:
    return {
        "key_id": record.key_id,
        "agent_id": record.agent_id,
        "store_id": record.store_id,
        "scopes": [s.value for s in record.scopes],
        "limits": record.limits.model_dump(mode="json"),
        "created_at": record.created_at.isoformat(),
        "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
    }


@router.post("", status_code=201)
@limiter.limit("30/minute")
def create_key(request: Request, body: CreateKeyBody) -> dict:
    expires = (
        datetime.now(UTC) + timedelta(hours=body.expires_in_hours)
        if body.expires_in_hours
        else None
    )
    issued = key_store.create_key(
        body.agent_id,
        STORE_ID,
        body.scopes,
        KeyLimits(
            per_order_max_cents=body.per_order_max_cents,
            per_day_budget_cents=body.per_day_budget_cents,
            requests_per_minute=body.requests_per_minute,
            allowed_categories=body.allowed_categories,
            expires_at=expires,
        ),
    )
    return {"raw_key": issued.raw_key, "shown_once": True, "key": _public(issued.record)}


@router.get("")
@limiter.limit("60/minute")
def list_keys(request: Request) -> dict:
    return {"keys": [_public(r) for r in key_store.list_keys()]}


@router.post("/{key_id}/revoke")
@limiter.limit("30/minute")
def revoke_key(request: Request, key_id: str) -> dict:
    try:
        return {"key": _public(key_store.revoke(key_id))}
    except KeyError:
        raise HTTPException(status_code=404, detail="KEY_NOT_FOUND") from None
