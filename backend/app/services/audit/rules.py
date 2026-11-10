"""Audit rules (PRD 4.1, M3). One rule per scoring dimension, pure functions of a Product.

Every rule returns passed/failed, the exact evidence it looked at, and an Issue when it fails.
No rule calls a model: the same product always gets the same result.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.contracts import (
    SCORE_WEIGHTS,
    Dimension,
    FixType,
    Issue,
    IssueCode,
    Product,
    Severity,
)

# Benchmark task that measures this dimension (PRD 4.5). Only set on failure: ScoreCheck
# .task_link is None when the check passes.
BENCHMARK_LINK: dict[Dimension, str] = {
    Dimension.PRICE: "A2",
    Dimension.VARIANTS: "A3",
    Dimension.CHECKOUT_PATH: "A1",
    Dimension.STOCK: "B1",
    Dimension.SHIPPING: "B3",
    Dimension.DESCRIPTION: "B4",
}

# Phrases that look like instructions to an agent. Product text is data, so these are flagged
# and cost points; they never change a policy decision. Deterministic on purpose (no model).
_INJECTION_PATTERNS = re.compile(
    r"ignore (all |any |the )?(previous|prior|above) (instructions|rules)"
    r"|disregard (the )?(rules|policy|instructions)"
    r"|(you must|always) (buy|order|purchase)"
    r"|system prompt",
    re.IGNORECASE,
)
MIN_DESCRIPTION_CHARS = 20

# Version of the rule set that produced a result, stored on every AuditResult for reproducibility.
RULE_PACK_VERSION = "2026.10.0"


@dataclass(frozen=True)
class RuleResult:
    passed: bool
    evidence: str
    issue: Issue | None  # set only when passed is False


@dataclass(frozen=True)
class Rule:
    dimension: Dimension
    check_id: str
    severity: Severity  # severity if the check fails
    run: Callable[[Product], RuleResult]


def _fail(
    dim: Dimension,
    code: IssueCode,
    severity: Severity,
    field: str,
    message: str,
    why: str,
    fix_type: FixType,
    evidence: str,
) -> RuleResult:
    issue = Issue(
        code=code,
        severity=severity,
        field=field,
        message=message,
        why=why,
        fix_type=fix_type,
        points_lost=SCORE_WEIGHTS[dim],
    )
    return RuleResult(passed=False, evidence=evidence, issue=issue)


def _pass(evidence: str) -> RuleResult:
    return RuleResult(passed=True, evidence=evidence, issue=None)


# --- price ----------------------------------------------------------------------------------
def check_price(p: Product) -> RuleResult:
    unresolved = p.price_cents is None and (
        not p.variants or any(v.price_cents is None for v in p.variants)
    )
    if not unresolved:
        return _pass(
            f"price {p.price_cents} {p.currency}" if p.price_cents is not None else "variant prices"
        )
    evidence = p.price_text.strip() if p.price_text and p.price_text.strip() else "no price stated"
    if p.price_text and p.price_text.strip():
        return _fail(
            Dimension.PRICE,
            IssueCode.PRICE_AMBIGUOUS,
            Severity.CRITICAL,
            "price",
            f"Price is not exact: '{evidence}'",
            "An agent cannot buy the right variant at a known price, so it guesses or stops.",
            FixType.SELLER_INPUT,
            evidence,
        )
    return _fail(
        Dimension.PRICE,
        IssueCode.PRICE_MISSING,
        Severity.CRITICAL,
        "price",
        "No price stated",
        "An agent has no price to check its budget against.",
        FixType.SELLER_INPUT,
        evidence,
    )


# --- stock ----------------------------------------------------------------------------------
def check_stock(p: Product) -> RuleResult:
    if p.variants:
        missing = [v.sku or str(v.attributes) for v in p.variants if v.stock is None]
        if missing:
            return _fail(
                Dimension.STOCK,
                IssueCode.STOCK_MISSING,
                Severity.HIGH,
                "variants.stock",
                f"Stock not stated for {len(missing)} variant(s)",
                "Without stock an agent can buy something that is sold out.",
                FixType.SELLER_INPUT,
                "stock not stated: " + ", ".join(missing),
            )
        return _pass(f"stock stated for {len(p.variants)} variant(s)")
    if p.stock is None:
        return _fail(
            Dimension.STOCK,
            IssueCode.STOCK_MISSING,
            Severity.HIGH,
            "stock",
            "Stock not stated",
            "Without stock an agent can buy something that is sold out.",
            FixType.SELLER_INPUT,
            "stock not stated",
        )
    return _pass(f"stock {p.stock}")


# --- variants -------------------------------------------------------------------------------
def check_variants(p: Product) -> RuleResult:
    if not p.variants:
        return _pass("single item, no variants")
    bad = [v.sku or "(no sku)" for v in p.variants if not v.sku or not v.attributes]
    if bad:
        return _fail(
            Dimension.VARIANTS,
            IssueCode.VARIANTS_NOT_MACHINE_READABLE,
            Severity.HIGH,
            "variants",
            f"{len(bad)} variant(s) lack a sku or attributes",
            "An agent cannot tell which size or colour it is buying.",
            FixType.STRUCTURE,
            ", ".join(bad),
        )
    return _pass(f"{len(p.variants)} variant(s) with sku and attributes")


# --- shipping and returns -------------------------------------------------------------------
def check_shipping(p: Product) -> RuleResult:
    if p.shipping is None or not p.shipping.regions:
        return _fail(
            Dimension.SHIPPING,
            IssueCode.SHIPPING_MISSING,
            Severity.HIGH,
            "shipping.regions",
            "Shipping regions not stated",
            "An agent cannot know whether the store ships to the buyer's country.",
            FixType.SELLER_INPUT,
            "shipping regions not stated",
        )
    return _pass(f"ships to {', '.join(p.shipping.regions)}")


def check_returns(p: Product) -> RuleResult:
    if p.returns is None or p.returns.window_days is None:
        return _fail(
            Dimension.RETURNS,
            IssueCode.RETURNS_MISSING,
            Severity.MEDIUM,
            "returns.window_days",
            "Return window not stated",
            "An agent cannot show the buyer the return terms before buying.",
            FixType.SELLER_INPUT,
            "return window not stated",
        )
    return _pass(f"{p.returns.window_days}-day return window")


# --- description ----------------------------------------------------------------------------
def check_description(p: Product) -> RuleResult:
    text = p.description.strip()
    if len(text) < MIN_DESCRIPTION_CHARS:
        return _fail(
            Dimension.DESCRIPTION,
            IssueCode.DESCRIPTION_VAGUE,
            Severity.MEDIUM,
            "description",
            "Description is missing or too short to describe the item",
            "An agent cannot confirm what it is buying from the description.",
            FixType.AI_EXTRACT,
            text or "(empty)",
        )
    match = _INJECTION_PATTERNS.search(text)
    if match:
        # Reported under DESCRIPTION_VAGUE: the contract has no separate code yet (see README).
        return _fail(
            Dimension.DESCRIPTION,
            IssueCode.DESCRIPTION_VAGUE,
            Severity.MEDIUM,
            "description",
            "Description contains instruction-like text",
            "Text aimed at an agent is treated as data and never acted on; the seller should remove it.",
            FixType.SELLER_INPUT,
            match.group(0),
        )
    return _pass(f"{len(text)} characters, no instruction-like text")


# --- identifiers and images -----------------------------------------------------------------
def check_identifiers(p: Product) -> RuleResult:
    if not (p.sku or p.gtin):
        return _fail(
            Dimension.IDENTIFIERS,
            IssueCode.IDENTIFIER_MISSING,
            Severity.LOW,
            "sku",
            "No SKU or GTIN",
            "Without an identifier the agent cannot match the item across listings.",
            FixType.SELLER_INPUT,
            "no sku, no gtin",
        )
    return _pass(f"sku {p.sku or '-'}, gtin {p.gtin or '-'}")


def check_image_alt(p: Product) -> RuleResult:
    if not p.images:
        return _fail(
            Dimension.IMAGE_ALT,
            IssueCode.IMAGE_ALT_MISSING,
            Severity.LOW,
            "images",
            "No product images",
            "Without alt text an agent that cannot see images has nothing to match.",
            FixType.SELLER_INPUT,
            "no images",
        )
    no_alt = [img.url for img in p.images if not (img.alt and img.alt.strip())]
    if no_alt:
        return _fail(
            Dimension.IMAGE_ALT,
            IssueCode.IMAGE_ALT_MISSING,
            Severity.LOW,
            "images.alt",
            f"{len(no_alt)} image(s) without alt text",
            "Without alt text an agent that cannot see images has nothing to match.",
            FixType.AI_EXTRACT,
            ", ".join(no_alt),
        )
    return _pass(f"{len(p.images)} image(s), all with alt text")


# --- checkout path --------------------------------------------------------------------------
def check_checkout_path(p: Product) -> RuleResult:
    if p.checkout_requires_human:
        return _fail(
            Dimension.CHECKOUT_PATH,
            IssueCode.CHECKOUT_REQUIRES_HUMAN,
            Severity.CRITICAL,
            "checkout_requires_human",
            "Checkout needs a human step",
            "An agent cannot finish the purchase, so there is no agent purchase path.",
            FixType.SELLER_INPUT,
            "checkout_requires_human = true",
        )
    return _pass("agent checkout path has no human-only step")


RULES: tuple[Rule, ...] = (
    Rule(Dimension.PRICE, "price.exact", Severity.CRITICAL, check_price),
    Rule(Dimension.STOCK, "stock.stated", Severity.HIGH, check_stock),
    Rule(Dimension.VARIANTS, "variants.machine_readable", Severity.HIGH, check_variants),
    Rule(Dimension.SHIPPING, "shipping.regions", Severity.HIGH, check_shipping),
    Rule(Dimension.RETURNS, "returns.window", Severity.MEDIUM, check_returns),
    Rule(Dimension.DESCRIPTION, "description.clear", Severity.MEDIUM, check_description),
    Rule(Dimension.IDENTIFIERS, "identifiers.present", Severity.LOW, check_identifiers),
    Rule(Dimension.IMAGE_ALT, "images.alt", Severity.LOW, check_image_alt),
    Rule(Dimension.CHECKOUT_PATH, "checkout.no_human_step", Severity.CRITICAL, check_checkout_path),
)
