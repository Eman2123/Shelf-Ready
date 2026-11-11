"""Fix engine and provenance validator (PRD 4.2). No applied value may lack source or seller input."""

from datetime import UTC, datetime

import pytest

from app.contracts import FixEvidence, FixMethod, FixRecord, FixStatus
from app.services.fixes import FixHistory, ValidationStatus, propose_fix, validate_value
from app.services.fixtures import red_rejection as rr

T0 = datetime(2026, 11, 10, tzinfo=UTC)


def _propose(proposed, snippet, method=FixMethod.AI_EXTRACT, source=rr.SOURCE_TEXT):
    return propose_fix(
        fix_id="fix_t",
        product_id=rr.PRODUCT_ID,
        field_name="material",
        old_value=None,
        proposed=proposed,
        source_field=rr.SOURCE_FIELD,
        source_text=source,
        snippet=snippet,
        method=method,
    )


def test_fixture_green_is_approved_with_exact_match_confidence():
    fix = _propose("Machine wash cold", "Machine wash cold.")
    assert fix.status is FixStatus.APPROVED
    assert fix.evidence.confidence == 1.0


def test_fixture_red_proposal_is_rejected_with_the_expected_reason():
    fix = _propose("100% organic cotton", "100% organic cotton")
    assert fix.status is FixStatus.REJECTED
    assert fix.new_value is None
    assert "not in the source" in fix.rejection_reason


def test_fixture_yellow_without_a_source_value_needs_the_seller():
    fix = _propose(None, "")
    assert fix.status is FixStatus.NEEDS_SELLER_INPUT
    assert fix.new_value is None and fix.evidence is None


def test_validator_agrees_with_the_fixture_verdicts():
    assert validate_value(
        rr.SOURCE_TEXT, "Machine wash cold", "Machine wash cold.", FixMethod.AI_EXTRACT
    ).status is (ValidationStatus.PASSED_EXACT)
    assert validate_value(
        rr.SOURCE_TEXT, "100% organic cotton", "100% organic cotton", FixMethod.AI_EXTRACT
    ).status is (ValidationStatus.REJECTED_NO_SUPPORT)


def test_snippet_that_is_in_source_but_value_is_not_still_rejected():
    verdict = validate_value(
        rr.SOURCE_TEXT, "100% silk", "Machine wash cold.", FixMethod.AI_EXTRACT
    )
    assert verdict.status is ValidationStatus.REJECTED_NO_SUPPORT
    assert "not supported" in verdict.reason


def test_unit_conversion_is_normalized_with_lower_confidence():
    source = "Length 2 in, fits most laptop sleeves."
    verdict = validate_value(source, "5.1 cm", "2 in", FixMethod.RULE)
    assert verdict.status is ValidationStatus.PASSED_NORMALIZED
    assert verdict.confidence == 0.9


def test_wrong_conversion_is_rejected():
    source = "Length 2 in, fits most laptop sleeves."
    verdict = validate_value(source, "5.5 cm", "2 in", FixMethod.RULE)
    assert verdict.status is ValidationStatus.REJECTED_NO_SUPPORT


def test_empty_or_whitespace_snippet_is_never_supported():
    assert validate_value(rr.SOURCE_TEXT, "Machine wash cold", "", FixMethod.AI_EXTRACT).status is (
        ValidationStatus.REJECTED_NO_SUPPORT
    )
    assert validate_value(
        rr.SOURCE_TEXT, "Machine wash cold", "   ", FixMethod.AI_EXTRACT
    ).status is (ValidationStatus.REJECTED_NO_SUPPORT)


def test_seller_input_is_accepted_without_a_source_snippet():
    fix = propose_fix(
        fix_id="fix_seller",
        product_id=rr.PRODUCT_ID,
        field_name="variants",
        old_value=[],
        proposed=["S", "M", "L"],
        source_field="variants",
        source_text="",
        snippet="",
        method=FixMethod.SELLER_INPUT,
    )
    assert fix.status is FixStatus.APPROVED
    assert fix.evidence.confidence == 1.0


def test_only_approved_fixes_can_be_applied_and_each_apply_versions_the_product():
    history = FixHistory(clock=lambda: T0)
    history.start(rr.PRODUCT_ID, {"material": None, "care": None})
    approved = _propose("Machine wash cold", "Machine wash cold.")
    applied = history.apply_fix(rr.PRODUCT_ID, approved)
    assert applied.version == 2
    assert history.current(rr.PRODUCT_ID).values["material"] == "Machine wash cold"


def test_a_rejected_fix_cannot_be_applied():
    history = FixHistory(clock=lambda: T0)
    history.start(rr.PRODUCT_ID, {"material": None})
    rejected = _propose("100% organic cotton", "100% organic cotton")
    with pytest.raises(ValueError, match="only APPROVED"):
        history.apply_fix(rr.PRODUCT_ID, rejected)


def test_a_fix_without_evidence_cannot_be_applied_even_if_forced():
    history = FixHistory(clock=lambda: T0)
    history.start(rr.PRODUCT_ID, {"material": None})
    forged = FixRecord.model_construct(
        id="fix_forged",
        product_id=rr.PRODUCT_ID,
        field="material",
        old_value=None,
        new_value="100% organic cotton",
        status=FixStatus.APPROVED,
        evidence=FixEvidence(
            source_field="description",
            source_snippet="",
            method=FixMethod.AI_EXTRACT,
            confidence=1.0,
        ),
        rejection_reason=None,
    )
    with pytest.raises(ValueError, match="no source snippet"):
        history.apply_fix(rr.PRODUCT_ID, forged)


def test_rollback_restores_previous_values_as_a_new_logged_version():
    history = FixHistory(clock=lambda: T0)
    history.start(rr.PRODUCT_ID, {"material": None})
    history.apply_fix(rr.PRODUCT_ID, _propose("Machine wash cold", "Machine wash cold."))
    restored = history.rollback(rr.PRODUCT_ID)
    assert restored.version == 3
    assert restored.values["material"] is None
    assert [v.version for v in history.versions[rr.PRODUCT_ID]] == [1, 2, 3]
    assert [e.event for e in history.log] == ["APPLY", "ROLLBACK"]


def test_rollback_needs_an_earlier_version():
    history = FixHistory(clock=lambda: T0)
    history.start(rr.PRODUCT_ID, {"material": None})
    with pytest.raises(ValueError, match="no earlier version"):
        history.rollback(rr.PRODUCT_ID)
