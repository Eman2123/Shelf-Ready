"""Computed readiness score (PRD 4.1). No hard-coded numbers: every point comes from a check.

Product score = sum of the weights of the checks that pass (weights from SCORE_WEIGHTS, total 100).
Critical cap: a CRITICAL failure (ambiguous or missing price, or no agent checkout path) caps the
product at CRITICAL_CAP.
Store score = mean of product scores. If no product in the store has an agent checkout path, the
store is capped at STORE_NO_CHECKOUT_CAP.

The waterfall starts at 100 and lists every deduction with its evidence, so "why is this store
91?" has an answer per point.

Assumption, not in the PRD: STORE_NO_CHECKOUT_CAP uses the same value as CRITICAL_CAP. Confirm
before the Report calls it a fact.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.contracts import (
    SCORE_WEIGHTS,
    AuditResult,
    Dimension,
    Product,
    ScoreCheck,
    Severity,
)

from .rules import BENCHMARK_LINK, RULE_PACK_VERSION, RULES

CRITICAL_CAP = 60
STORE_NO_CHECKOUT_CAP = 60  # assumption, see module docstring

assert sum(SCORE_WEIGHTS.values()) == 100, "score weights must total 100"


@dataclass(frozen=True)
class WaterfallStep:
    label: str
    delta: int
    evidence: str


@dataclass(frozen=True)
class ProductAudit:
    result: AuditResult
    checks: tuple[ScoreCheck, ...]
    waterfall: tuple[WaterfallStep, ...]
    raw_score: int  # before the critical cap

    @property
    def score(self) -> int:
        return self.result.score


@dataclass(frozen=True)
class StoreAudit:
    run_id: str
    store_score: int
    products: tuple[ProductAudit, ...]
    store_cap_applied: bool
    notes: list[str] = field(default_factory=list)

    def explain(self) -> list[str]:
        lines = [f"Store score {self.store_score} (run {self.run_id})"]
        for pa in self.products:
            lines.append(f"  {pa.result.product_id}: {pa.score}")
            for step in pa.waterfall:
                sign = "+" if step.delta >= 0 else "-"
                lines.append(f"    {sign}{abs(step.delta)} {step.label}: {step.evidence}")
        lines.extend(self.notes)
        return lines


def audit_product(product: Product, run_id: str) -> ProductAudit:
    checks: list[ScoreCheck] = []
    issues = []
    evidence_by_check: dict[str, str] = {}
    for rule in RULES:
        outcome = rule.run(product)
        weight = SCORE_WEIGHTS[rule.dimension]
        checks.append(
            ScoreCheck(
                check_id=rule.check_id,
                dimension=rule.dimension,
                severity=rule.severity,
                task_link=None if outcome.passed else BENCHMARK_LINK.get(rule.dimension),
                evidence=outcome.evidence,
                passed=outcome.passed,
                points=weight if outcome.passed else 0,
                run_id=run_id,
            )
        )
        evidence_by_check[rule.check_id] = outcome.evidence
        if outcome.issue is not None:
            issues.append(outcome.issue)

    raw = sum(c.points for c in checks)
    critical_failed = [c for c in checks if c.severity is Severity.CRITICAL and not c.passed]
    score = min(raw, CRITICAL_CAP) if critical_failed else raw

    waterfall: list[WaterfallStep] = [WaterfallStep("start", 100, "readiness starts at 100")]
    for c in checks:
        if not c.passed:
            waterfall.append(
                WaterfallStep(c.dimension.value, -SCORE_WEIGHTS[c.dimension], c.evidence)
            )
    if score != raw:
        names = ", ".join(c.check_id for c in critical_failed)
        waterfall.append(
            WaterfallStep(
                "critical cap", score - raw, f"critical failure ({names}): max {CRITICAL_CAP}"
            )
        )
    assert waterfall[0].delta + sum(s.delta for s in waterfall[1:]) == score

    result = AuditResult(
        product_id=product.id,
        run_id=run_id,
        score=score,
        issues=issues,
        rule_pack_version=RULE_PACK_VERSION,
    )
    return ProductAudit(
        result=result, checks=tuple(checks), waterfall=tuple(waterfall), raw_score=raw
    )


def audit_store(products: Sequence[Product], run_id: str) -> StoreAudit:
    if not products:
        raise ValueError("cannot score an empty store")
    audits = tuple(audit_product(p, run_id) for p in products)
    mean = sum(a.score for a in audits) / len(audits)
    store_score = round(mean)
    has_checkout = any(
        c.passed for a in audits for c in a.checks if c.dimension is Dimension.CHECKOUT_PATH
    )
    cap_applied = not has_checkout
    notes: list[str] = []
    if cap_applied:
        store_score = min(store_score, STORE_NO_CHECKOUT_CAP)
        notes.append(f"store cap {STORE_NO_CHECKOUT_CAP}: no product has an agent checkout path")
    return StoreAudit(
        run_id=run_id,
        store_score=store_score,
        products=audits,
        store_cap_applied=cap_applied,
        notes=notes,
    )
