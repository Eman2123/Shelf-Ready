"""Audit engine (PRD 4.1, M3): reproducible, every check has id, evidence and a task link."""

from pathlib import Path

import pytest

from app.contracts import SCORE_WEIGHTS, Dimension
from app.services.audit import BENCHMARK_LINK, CRITICAL_CAP, audit_product, audit_store
from app.services.fixtures.demo_store import PUBLISHED_PRODUCTS
from app.services.importer.csv_import import import_csv

MESSY_CSV = Path(__file__).resolve().parents[1] / "data" / "demo" / "messy_catalog.csv"


def messy_products():
    return import_csv(MESSY_CSV.read_text(encoding="utf-8")).products


def ambiguous_tee():
    """Published tee with its exact price removed: the page only says "from $20" (critical)."""
    tee = PUBLISHED_PRODUCTS["prod_tee"]
    return tee.model_copy(
        update={
            "price_cents": None,
            "price_text": "from $20",
            "variants": [v.model_copy(update={"price_cents": None}) for v in tee.variants],
        }
    )


def test_weights_total_100_and_match_the_contract():
    assert sum(SCORE_WEIGHTS.values()) == 100


def test_published_demo_store_scores_high_and_only_the_injected_mug_loses_points():
    audit = audit_store(list(PUBLISHED_PRODUCTS.values()), run_id="run_pub")
    by_id = {p.result.product_id: p for p in audit.products}
    assert by_id["prod_mug"].score < 100  # injection-like text in the description
    assert by_id["prod_tee"].score == 100
    assert audit.store_score >= 90


def test_same_input_gives_the_same_score_every_time():
    product = PUBLISHED_PRODUCTS["prod_mug"]
    a = audit_product(product, run_id="run_x")
    b = audit_product(product, run_id="run_x")
    assert a.result == b.result
    assert a.checks == b.checks


def test_every_check_has_id_dimension_severity_evidence_and_run_id():
    audit = audit_product(messy_products()[0], run_id="run_messy")
    assert len(audit.checks) == len(SCORE_WEIGHTS)
    for check in audit.checks:
        assert check.check_id
        assert check.evidence
        assert check.run_id == "run_messy"


def test_failed_check_links_to_a_benchmark_task_and_passed_check_does_not():
    audit = audit_product(messy_products()[0], run_id="run_messy")
    for check in audit.checks:
        if check.passed:
            assert check.task_link is None
        elif check.dimension in BENCHMARK_LINK:
            assert check.task_link == BENCHMARK_LINK[check.dimension]
    price = next(c for c in audit.checks if c.dimension is Dimension.PRICE)
    assert not price.passed and price.task_link == "A2"


def test_critical_price_failure_caps_the_product_score():
    audit = audit_product(ambiguous_tee(), run_id="run_amb")
    assert audit.raw_score == 80  # only the price check (-20) fails
    assert audit.score == CRITICAL_CAP
    assert any(i.code.value == "PRICE_AMBIGUOUS" for i in audit.result.issues)


def test_waterfall_starts_at_100_and_reaches_the_score_with_evidence():
    audit = audit_product(ambiguous_tee(), run_id="run_amb")
    assert audit.waterfall[0].label == "start" and audit.waterfall[0].delta == 100
    assert sum(step.delta for step in audit.waterfall) == audit.score
    assert audit.waterfall[-1].label == "critical cap"
    for step in audit.waterfall[1:]:
        assert step.evidence


def test_every_failed_check_produces_one_issue_and_points_lost_add_up():
    audit = audit_product(messy_products()[0], run_id="run_messy")
    failed = [c for c in audit.checks if not c.passed]
    assert len(audit.result.issues) == len(failed)
    assert sum(i.points_lost for i in audit.result.issues) == 100 - audit.raw_score


def test_messy_store_scores_lower_than_the_published_store():
    published = audit_store(list(PUBLISHED_PRODUCTS.values()), run_id="run_pub").store_score
    messy = audit_store(messy_products(), run_id="run_messy").store_score
    assert messy < published


def test_store_with_no_agent_checkout_path_is_capped():
    products = [
        p.model_copy(update={"checkout_requires_human": True}) for p in PUBLISHED_PRODUCTS.values()
    ]
    audit = audit_store(products, run_id="run_nocheckout")
    assert audit.store_cap_applied
    assert audit.store_score <= 60
    assert any("checkout" in note for note in audit.notes)


def test_empty_store_is_refused():
    with pytest.raises(ValueError):
        audit_store([], run_id="run_empty")


def test_explain_lists_each_deduction_with_its_evidence():
    audit = audit_store([ambiguous_tee(), PUBLISHED_PRODUCTS["prod_mug"]], run_id="run_amb")
    text = "\n".join(audit.explain())
    assert f"Store score {audit.store_score}" in text
    assert "critical cap" in text
    assert "from $20" in text
