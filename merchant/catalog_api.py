from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import CAPABILITIES_PATH, CATALOG_PATH
from merchant.catalog_schema import CatalogResponse, Product

router = APIRouter()


def load_catalog() -> CatalogResponse:
    raw = json.loads(Path(CATALOG_PATH).read_text(encoding="utf-8"))
    return CatalogResponse.model_validate(raw)


def get_product_by_id(product_id: str) -> Product | None:
    catalog = load_catalog()
    for product in catalog.products:
        if product.id == product_id:
            return product
    return None


@router.get("/catalog", response_model=CatalogResponse)
def get_catalog() -> CatalogResponse:
    return load_catalog()


@router.get("/product/{product_id}", response_model=Product)
def get_product(product_id: str) -> Product:
    product = get_product_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@router.get("/capabilities")
def get_capabilities() -> dict:
    return json.loads(Path(CAPABILITIES_PATH).read_text(encoding="utf-8"))
