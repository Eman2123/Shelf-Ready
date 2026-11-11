from app.contracts import FixStatus
from app.services.fixtures import red_rejection as rr


def test_green_snippet_is_in_source():
    assert rr.GREEN.status is FixStatus.APPLIED
    assert rr.snippet_supported(rr.SOURCE_TEXT, rr.GREEN.evidence.source_snippet)


def test_red_proposal_is_not_supported_so_it_is_rejected():
    assert not rr.snippet_supported(rr.SOURCE_TEXT, rr.RED_PROPOSAL.evidence.source_snippet)
    assert rr.RED.status is FixStatus.REJECTED
    assert "not in the source" in rr.RED.rejection_reason


def test_yellow_needs_the_seller_and_has_no_value():
    assert rr.YELLOW.status is FixStatus.NEEDS_SELLER_INPUT
    assert rr.YELLOW.new_value is None


def test_no_applied_fix_lacks_support():
    for fix in rr.ALL:
        if fix.status is FixStatus.APPLIED:
            assert rr.snippet_supported(rr.SOURCE_TEXT, fix.evidence.source_snippet)


def test_empty_or_whitespace_snippet_is_never_supported():
    assert not rr.snippet_supported(rr.SOURCE_TEXT, "")
    assert not rr.snippet_supported(rr.SOURCE_TEXT, "   ")
