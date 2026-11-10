from fastapi.testclient import TestClient

from app.main import app


def test_demo_store_audit_route_returns_scores_with_run_id():
    client = TestClient(app)
    body = client.get("/api/audit/demo-store").json()
    assert body["run_id"] == "run_demo_audit"
    assert 0 <= body["store_score"] <= 100
    assert len(body["products"]) == 4
    for product in body["products"]:
        assert product["waterfall"][0]["label"] == "start"
        assert sum(s["delta"] for s in product["waterfall"]) == product["score"]
