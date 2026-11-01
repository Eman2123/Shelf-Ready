from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_ready import build_catalog_patch, format_price, product_to_jsonld
from app.services.fixtures.demo_store import PUBLISHED_PRODUCTS

client = TestClient(app)


def test_format_price_is_exact():
    assert format_price(2400) == "24.00"
    assert format_price(5) == "0.05"
    assert format_price(199) == "1.99"


def test_jsonld_tee_has_one_offer_per_variant_with_stock():
    ld = product_to_jsonld(PUBLISHED_PRODUCTS["prod_tee"])
    assert ld["@type"] == "Product" and ld["@context"] == "https://schema.org"
    offers = {o["sku"]: o for o in ld["offers"]}
    assert offers["TEE-BLU-M"]["price"] == "24.00"
    assert offers["TEE-BLU-M"]["availability"].endswith("InStock")
    assert offers["TEE-BLK-M"]["availability"].endswith("OutOfStock")


def test_jsonld_does_not_guess_stock_or_price():
    p = PUBLISHED_PRODUCTS["prod_tote"].model_copy(update={"stock": None, "price_cents": None})
    ld = product_to_jsonld(p)
    assert ld["offers"] == []
    p2 = PUBLISHED_PRODUCTS["prod_tote"].model_copy(update={"stock": None})
    offer = product_to_jsonld(p2)["offers"][0]
    assert "availability" not in offer and "inventoryLevel" not in offer


def test_catalog_patch_only_uses_real_fields():
    p = PUBLISHED_PRODUCTS["prod_tote"].model_copy(update={"category": None, "home_url": None})
    paths = [op["path"] for op in build_catalog_patch(p)]
    assert paths == ["/description", "/image_url"]


def test_manifest_route():
    r = client.get("/.well-known/agent-store.json")
    assert r.status_code == 200
    body = r.json()
    assert body["mcp"]["tools"] == ["search_products", "get_product", "get_policy", "create_order"]
    assert body["mcp"]["url"].endswith("/mcp")
    assert body["environment"] == "paypal-sandbox"


def test_jsonld_route_and_404():
    r = client.get("/agent-ready/products/prod_mug/jsonld")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/ld+json")
    assert r.json()["name"] == "Tidewell Enamel Mug"
    assert client.get("/agent-ready/products/nope/jsonld").status_code == 404
