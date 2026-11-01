"""Fixture for the demo's red rejection (PRD 4.2): the AI proposes a value that is not in the source.

Three lanes on the Fix review screen, one fixture each:
  green  - value is quoted from the source (APPLIED, snippet highlighted)
  red    - AI proposed "100% organic cotton"; the source never says it (REJECTED)
  yellow - the data is not in the source at all, the seller must supply it (NEEDS_SELLER_INPUT)

`snippet_supported` is the minimal rule the fixture needs. The real provenance validator lives
in `services/fixes` (owner: A) and must give the same verdicts on these three records.
"""

from __future__ import annotations

import re

from app.contracts import FixEvidence, FixMethod, FixRecord, FixStatus

PRODUCT_ID = "prod_tee"
SOURCE_FIELD = "description"
SOURCE_TEXT = (
    "Soft tee, great for everyday. Comes in lots of colors and sizes! "
    "Call us to confirm your size. Machine wash cold."
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def snippet_supported(source: str, snippet: str) -> bool:
    """True only if the snippet is a non-empty exact (case/space-insensitive) quote of the source."""
    s = _norm(snippet)
    return bool(s) and s in _norm(source)


GREEN = FixRecord(
    id="fix_green_care",
    product_id=PRODUCT_ID,
    field="care_instructions",
    old_value=None,
    new_value="Machine wash cold",
    status=FixStatus.APPLIED,
    evidence=FixEvidence(
        source_field=SOURCE_FIELD,
        source_snippet="Machine wash cold.",
        method=FixMethod.AI_EXTRACT,
        confidence=0.97,
    ),
)

# Built unvalidated on purpose: this is what the AI *proposed*, before the validator runs.
RED_PROPOSAL = FixRecord(
    id="fix_red_material",
    product_id=PRODUCT_ID,
    field="material",
    old_value=None,
    new_value="100% organic cotton",
    status=FixStatus.PROPOSED,
    evidence=FixEvidence(
        source_field=SOURCE_FIELD,
        source_snippet="100% organic cotton",
        method=FixMethod.AI_EXTRACT,
        confidence=0.91,
    ),
)

RED = RED_PROPOSAL.model_copy(
    update={
        "status": FixStatus.REJECTED,
        "rejection_reason": "Snippet '100% organic cotton' is not in the source text.",
    }
)

YELLOW = FixRecord(
    id="fix_yellow_sizes",
    product_id=PRODUCT_ID,
    field="variants",
    old_value=[],
    new_value=None,
    status=FixStatus.NEEDS_SELLER_INPUT,
    evidence=None,
)

ALL = [GREEN, RED, YELLOW]
