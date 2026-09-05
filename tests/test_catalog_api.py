from __future__ import annotations

from fastapi.testclient import TestClient

from merchant.catalog_schema import CatalogResponse, Product
from server import app

client = TestClient(app)


def test_catalog_endpoint_matches_schema():
    response = client.get("/catalog")
    assert response.status_code == 200
    payload = CatalogResponse.model_validate(response.json())
    assert payload.currency == "INR"
    assert payload.products
    for product in payload.products:
        assert product.id
        assert product.price_inr > 0
        assert isinstance(product.tags, list)


def test_product_endpoint_and_404():
    listed = client.get("/catalog").json()["products"][0]["id"]
    ok = client.get(f"/product/{listed}")
    assert ok.status_code == 200
    Product.model_validate(ok.json())
    missing = client.get("/product/NOPE")
    assert missing.status_code == 404


def test_capabilities_declare_gated_actions():
    response = client.get("/capabilities")
    names = {item["name"] for item in response.json()["allowed_actions"]}
    assert {"add_to_cart", "checkout", "search_catalog"} <= names
    assert response.json()["policy"]["money_decisions"] == "policy_gate_only"
