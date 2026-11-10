"""Hash-chained run events (PRD 4.4). Tamper-EVIDENT: an edit breaks the chain at that point."""

from app.contracts import GENESIS_HASH, hash_output
from app.services.receipt import RunLedger, verify_chain


def _ledger() -> tuple[RunLedger, dict]:
    ledger = RunLedger()
    outputs = {
        "src_1": {"snapshot": "abc"},
        "audit_1": {"score": 61},
        "order_1": {"status": "DENIED"},
    }
    ledger.append("src_1", "source_snapshot", [], outputs["src_1"])
    ledger.append("audit_1", "audit_run", ["src_1"], outputs["audit_1"])
    ledger.append("order_1", "policy_decision", ["audit_1"], outputs["order_1"])
    return ledger, outputs


def test_first_event_links_to_genesis_and_each_later_event_links_to_the_one_before():
    ledger, _ = _ledger()
    events = ledger.events
    assert events[0].prev_hash == GENESIS_HASH
    assert events[1].prev_hash == events[0].link_hash()
    assert events[2].prev_hash == events[1].link_hash()


def test_untouched_chain_verifies_including_output_hashes():
    ledger, outputs = _ledger()
    result = ledger.verify(outputs)
    assert result.ok and result.checked == 3 and result.broken_at is None


def test_empty_chain_is_valid():
    assert verify_chain([]).ok


def test_editing_an_output_is_detected_at_that_event():
    ledger, outputs = _ledger()
    outputs["audit_1"] = {"score": 95}  # someone edits the recorded result afterwards
    result = ledger.verify(outputs)
    assert not result.ok
    assert result.broken_at == "audit_1"
    assert "output" in result.reason


def test_editing_an_earlier_link_breaks_every_later_link():
    ledger, _ = _ledger()
    events = list(ledger.events)
    events[0] = events[0].model_copy(update={"output_hash": hash_output({"snapshot": "changed"})})
    result = verify_chain(events)
    assert not result.ok
    assert result.broken_at == "audit_1"


def test_reordering_or_removing_an_event_is_detected():
    ledger, _ = _ledger()
    events = list(ledger.events)
    del events[1]
    assert not verify_chain(events).ok


def test_duplicate_event_id_is_detected():
    ledger, _ = _ledger()
    events = list(ledger.events)
    events.append(events[0])
    result = verify_chain(events)
    assert not result.ok and "duplicate" in result.reason
