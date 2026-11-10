"""verify_receipt over the stored benchmark record: chain is intact and every output matches."""

from app.scripts.verify_receipt import main
from app.services.benchmark.runner import DATA_PATH, load_runs
from app.services.receipt import ledger_from_runs


def test_stored_benchmark_chain_is_intact():
    runs = load_runs(DATA_PATH)
    ledger, outputs = ledger_from_runs(runs)
    check = ledger.verify(outputs)
    assert check.ok
    assert check.checked == len(runs) == 72


def test_editing_one_stored_run_breaks_the_chain():
    runs = load_runs(DATA_PATH)
    ledger, outputs = ledger_from_runs(runs)
    first = runs[0].run.id
    outputs[first] = {**outputs[first], "steps": []}
    check = ledger.verify(outputs)
    assert not check.ok and check.broken_at == first


def test_script_exits_zero_on_the_stored_record():
    assert main() == 0
