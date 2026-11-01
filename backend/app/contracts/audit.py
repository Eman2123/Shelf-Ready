"""Audit contracts: issues, the per-check ScoreCheck and the score weights (total 100)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from .common import Contract, Id


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IssueCode(StrEnum):
    """Stable issue codes. Add new codes at the end; never rename an existing one."""

    PRICE_AMBIGUOUS = "PRICE_AMBIGUOUS"
    PRICE_MISSING = "PRICE_MISSING"
    STOCK_MISSING = "STOCK_MISSING"
    VARIANTS_NOT_MACHINE_READABLE = "VARIANTS_NOT_MACHINE_READABLE"
    SHIPPING_MISSING = "SHIPPING_MISSING"
    RETURNS_MISSING = "RETURNS_MISSING"
    DESCRIPTION_VAGUE = "DESCRIPTION_VAGUE"
    IDENTIFIER_MISSING = "IDENTIFIER_MISSING"
    IMAGE_ALT_MISSING = "IMAGE_ALT_MISSING"
    CHECKOUT_REQUIRES_HUMAN = "CHECKOUT_REQUIRES_HUMAN"


class FixType(StrEnum):
    """How a fix can be produced. SELLER_INPUT means the data is not in the source."""

    RULE_FILL = "RULE_FILL"
    AI_EXTRACT = "AI_EXTRACT"
    SELLER_INPUT = "SELLER_INPUT"
    STRUCTURE = "STRUCTURE"


class Dimension(StrEnum):
    PRICE = "price"
    STOCK = "stock"
    VARIANTS = "variants"
    SHIPPING = "shipping"
    RETURNS = "returns"
    DESCRIPTION = "description"
    IDENTIFIERS = "identifiers"
    IMAGE_ALT = "image_alt"
    CHECKOUT_PATH = "checkout_path"


# Score weights from the PRD (total 100). The audit engine must use these.
SCORE_WEIGHTS: dict[Dimension, int] = {
    Dimension.PRICE: 20,
    Dimension.STOCK: 15,
    Dimension.VARIANTS: 15,
    Dimension.SHIPPING: 15,
    Dimension.RETURNS: 10,
    Dimension.DESCRIPTION: 10,
    Dimension.IDENTIFIERS: 5,
    Dimension.IMAGE_ALT: 5,
    Dimension.CHECKOUT_PATH: 5,
}


class Issue(Contract):
    code: IssueCode
    severity: Severity
    field: str
    message: str
    # plain-language reason shown in the UI ("explain why")
    why: str
    fix_type: FixType
    # points lost in the readiness score because of this issue
    points_lost: Annotated[int, Field(ge=0)]


class ScoreCheck(Contract):
    """One scored check. Every check has an id, severity, evidence and a link to a fix task."""

    check_id: Id
    dimension: Dimension
    severity: Severity
    # id of the fix task that resolves this check (None when it passed)
    task_link: str | None
    # the exact value or text the check looked at
    evidence: str
    passed: bool
    points: Annotated[int, Field(ge=0)]
    run_id: Id


class AuditResult(Contract):
    product_id: Id
    run_id: Id
    score: Annotated[int, Field(ge=0, le=100)]
    issues: list[Issue]
    # version of the rule pack that produced this result, for reproducibility
    rule_pack_version: str
