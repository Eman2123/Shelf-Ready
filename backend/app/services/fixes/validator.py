"""Provenance validator (PRD 4.2). Deterministic code, never a model.

A proposed value is accepted only if the evidence snippet is really in the source text AND the
value is supported by that snippet, either verbatim or through a fixed unit conversion.

Confidence comes from the method, not from the AI: verbatim match 1.0, deterministic unit
conversion 0.9. A value that fails the check is REJECTED with a reason; it is never silently
dropped and never applied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.contracts import FixMethod


class ValidationStatus(StrEnum):
    PASSED_EXACT = "PASSED_EXACT"
    PASSED_NORMALIZED = "PASSED_NORMALIZED"
    PASSED_SELLER_INPUT = "PASSED_SELLER_INPUT"
    REJECTED_NO_SUPPORT = "REJECTED_NO_SUPPORT"
    NEEDS_SELLER_INPUT = "NEEDS_SELLER_INPUT"


@dataclass(frozen=True)
class Verdict:
    status: ValidationStatus
    confidence: float  # 0 when rejected or waiting for the seller
    reason: str | None  # set for every REJECTED_* and NEEDS_* verdict


_EXACT_CONFIDENCE = 1.0
_NORMALIZED_CONFIDENCE = 0.9

# Deterministic unit conversions: (from_unit, to_unit) -> factor. Extend only with a test.
_CONVERSIONS: dict[tuple[str, str], float] = {
    ("in", "cm"): 2.54,
    ("inch", "cm"): 2.54,
    ("inches", "cm"): 2.54,
    ("lb", "kg"): 0.45359237,
    ("lbs", "kg"): 0.45359237,
    ("oz", "g"): 28.349523125,
}
_QUANTITY = re.compile(r"(\d+(?:\.\d+)?)\s*(in|inch|inches|lbs?|oz|cm|kg|g)\b", re.IGNORECASE)
_PUNCT_EDGES = re.compile(r"^[^\w]+|[^\w]+$")


def normalize_text(text: str) -> str:
    """Case, whitespace, curly quotes and edge punctuation do not count as a difference."""
    t = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    t = re.sub(r"\s+", " ", t).strip().lower()
    return _PUNCT_EDGES.sub("", t)


def snippet_in_source(source: str, snippet: str) -> bool:
    """True only for a non-empty snippet that appears verbatim (after normalisation) in source."""
    s = normalize_text(snippet)
    return bool(s) and s in normalize_text(source)


def _converted_match(proposed: str, snippet: str) -> bool:
    """Does the proposed number+unit equal a snippet number+unit after a known conversion?"""
    target = _QUANTITY.search(proposed)
    if target is None:
        return False
    t_value, t_unit = float(target.group(1)), target.group(2).lower()
    t_decimals = len(target.group(1).split(".")[1]) if "." in target.group(1) else 0
    tolerance = 0.5 * 10 ** (-t_decimals)
    for src in _QUANTITY.finditer(snippet):
        s_value, s_unit = float(src.group(1)), src.group(2).lower()
        for (frm, to), factor in _CONVERSIONS.items():
            if s_unit == frm and t_unit == to and abs(s_value * factor - t_value) <= tolerance:
                return True
    return False


def validate_value(
    source: str,
    proposed: Any,
    snippet: str,
    method: FixMethod,
) -> Verdict:
    """Decide whether one proposed value may be applied."""
    if method is FixMethod.SELLER_INPUT:
        if proposed is None or (isinstance(proposed, str) and not proposed.strip()):
            return Verdict(
                ValidationStatus.NEEDS_SELLER_INPUT, 0.0, "seller has not supplied a value"
            )
        return Verdict(ValidationStatus.PASSED_SELLER_INPUT, 1.0, None)

    if proposed is None:
        return Verdict(
            ValidationStatus.NEEDS_SELLER_INPUT,
            0.0,
            "the source does not state this; the seller must supply it",
        )

    if not snippet_in_source(source, snippet):
        return Verdict(
            ValidationStatus.REJECTED_NO_SUPPORT,
            0.0,
            f"Snippet '{snippet}' is not in the source text.",
        )

    text = str(proposed)
    if normalize_text(text) and normalize_text(text) in normalize_text(snippet):
        return Verdict(ValidationStatus.PASSED_EXACT, _EXACT_CONFIDENCE, None)
    if _converted_match(text, snippet):
        return Verdict(ValidationStatus.PASSED_NORMALIZED, _NORMALIZED_CONFIDENCE, None)
    return Verdict(
        ValidationStatus.REJECTED_NO_SUPPORT,
        0.0,
        f"Value '{text}' is not supported by the snippet '{snippet}'.",
    )
