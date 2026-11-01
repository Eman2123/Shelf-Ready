"""Fix engine contracts. Hard rule (tested): no APPLIED value may exist without evidence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from .common import Contract, Id


class FixMethod(StrEnum):
    RULE = "RULE"
    AI_EXTRACT = "AI_EXTRACT"
    SELLER_INPUT = "SELLER_INPUT"


class FixStatus(StrEnum):
    PROPOSED = "PROPOSED"
    NEEDS_SELLER_INPUT = "NEEDS_SELLER_INPUT"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


class FixEvidence(Contract):
    """Provenance for one proposed value."""

    source_field: str
    # exact snippet from the source the value was derived from; empty for SELLER_INPUT
    source_snippet: str
    method: FixMethod
    confidence: Annotated[float, Field(ge=0, le=1)]


class FixRecord(Contract):
    id: Id
    product_id: Id
    field: str
    old_value: Any
    # None while status is NEEDS_SELLER_INPUT
    new_value: Any
    status: FixStatus
    evidence: FixEvidence | None
    # why a proposal was blocked (shown in the red lane), e.g. "snippet not found in source"
    rejection_reason: str | None = None

    @model_validator(mode="after")
    def _check_provenance(self) -> Self:
        if self.status is FixStatus.NEEDS_SELLER_INPUT and self.new_value is not None:
            raise ValueError("NEEDS_SELLER_INPUT must have new_value=None")
        if self.status in (FixStatus.APPROVED, FixStatus.APPLIED):
            if self.evidence is None:
                raise ValueError(f"{self.status} fix needs evidence")
            if (
                self.evidence.method is FixMethod.AI_EXTRACT
                and not self.evidence.source_snippet.strip()
            ):
                raise ValueError("AI_EXTRACT evidence needs a source snippet")
        if self.status is FixStatus.REJECTED and not self.rejection_reason:
            raise ValueError("REJECTED fix needs a rejection_reason")
        return self


class FixVersion(Contract):
    product_id: Id
    version: Annotated[int, Field(ge=1)]
    # full snapshot of the product values at this version
    values: dict[str, Any]
    author: Literal["agent", "seller", "system"]
    created_at: datetime
