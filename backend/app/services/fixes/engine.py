"""Fix records, versions and rollback (PRD 4.2, M4).

Flow: propose_fix() runs the validator and returns a FixRecord (APPROVED, REJECTED or
NEEDS_SELLER_INPUT). apply_fix() only accepts an APPROVED record with evidence, writes a new
FixVersion and returns the record as APPLIED. rollback() restores the previous version's values
as a new version, so the history is never rewritten.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from app.contracts import (
    FixEvidence,
    FixMethod,
    FixRecord,
    FixStatus,
    FixVersion,
)

from .validator import ValidationStatus, validate_value


def propose_fix(
    *,
    fix_id: str,
    product_id: str,
    field_name: str,
    old_value: Any,
    proposed: Any,
    source_field: str,
    source_text: str,
    snippet: str,
    method: FixMethod,
) -> FixRecord:
    """Validate one proposal. The result is never APPLIED: applying is a separate, explicit step."""
    verdict = validate_value(source_text, proposed, snippet, method)
    evidence = FixEvidence(
        source_field=source_field,
        source_snippet=snippet if method is not FixMethod.SELLER_INPUT else "",
        method=method,
        confidence=verdict.confidence,
    )
    if verdict.status is ValidationStatus.NEEDS_SELLER_INPUT:
        return FixRecord(
            id=fix_id,
            product_id=product_id,
            field=field_name,
            old_value=old_value,
            new_value=None,
            status=FixStatus.NEEDS_SELLER_INPUT,
            evidence=None,
        )
    if verdict.status is ValidationStatus.REJECTED_NO_SUPPORT:
        return FixRecord(
            id=fix_id,
            product_id=product_id,
            field=field_name,
            old_value=old_value,
            new_value=None,
            status=FixStatus.REJECTED,
            evidence=evidence,
            rejection_reason=verdict.reason,
        )
    return FixRecord(
        id=fix_id,
        product_id=product_id,
        field=field_name,
        old_value=old_value,
        new_value=proposed,
        status=FixStatus.APPROVED,
        evidence=evidence,
    )


@dataclass(frozen=True)
class FixLogEntry:
    event: str  # APPLY | ROLLBACK
    product_id: str
    version: int
    detail: str
    at: datetime


@dataclass
class FixHistory:
    """Versions and an append-only log per product. Applies are versioned; rollback is logged."""

    clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    versions: dict[str, list[FixVersion]] = field(default_factory=dict)
    log: list[FixLogEntry] = field(default_factory=list)

    def start(self, product_id: str, values: dict[str, Any]) -> FixVersion:
        """Version 1: the product as it was imported, before any fix."""
        if product_id in self.versions:
            raise ValueError(f"{product_id} already has a version history")
        v = FixVersion(
            product_id=product_id,
            version=1,
            values=dict(values),
            author="system",
            created_at=self.clock(),
        )
        self.versions[product_id] = [v]
        return v

    def current(self, product_id: str) -> FixVersion:
        return self.versions[product_id][-1]

    def apply_fix(
        self, product_id: str, fix: FixRecord, author: Literal["agent", "seller"] = "agent"
    ) -> FixVersion:
        """Write a new version with the fix applied. Refuses anything without evidence."""
        if fix.status is not FixStatus.APPROVED or fix.evidence is None:
            raise ValueError(f"fix {fix.id} is {fix.status}; only APPROVED fixes can be applied")
        needs_snippet = fix.evidence.method is not FixMethod.SELLER_INPUT
        if needs_snippet and not fix.evidence.source_snippet.strip():
            raise ValueError(f"fix {fix.id} has no source snippet")
        current = self.current(product_id)
        values = {**current.values, fix.field: fix.new_value}
        new = FixVersion(
            product_id=product_id,
            version=current.version + 1,
            values=values,
            author=author,
            created_at=self.clock(),
        )
        self.versions[product_id].append(new)
        self.log.append(
            FixLogEntry(
                "APPLY",
                product_id,
                new.version,
                f"{fix.field} via {fix.evidence.method.value}",
                new.created_at,
            )
        )
        return new

    def rollback(self, product_id: str) -> FixVersion:
        """Restore the previous version's values as a new version. Nothing is deleted."""
        history = self.versions[product_id]
        if len(history) < 2:
            raise ValueError(f"{product_id} has no earlier version to roll back to")
        previous = history[-2]
        current = history[-1]
        restored = FixVersion(
            product_id=product_id,
            version=current.version + 1,
            values=dict(previous.values),
            author="system",
            created_at=self.clock(),
        )
        history.append(restored)
        self.log.append(
            FixLogEntry(
                "ROLLBACK",
                product_id,
                restored.version,
                f"restored values of version {previous.version}",
                restored.created_at,
            )
        )
        return restored
