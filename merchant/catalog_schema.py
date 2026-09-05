from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductAttributes(BaseModel):
    model_config = {"extra": "allow"}

    breathable: bool | None = None
    waterproof: bool | None = None
    use: str | None = None
    color: str | None = None


class Product(BaseModel):
    id: str
    name: str
    category: str
    price_inr: float = Field(gt=0)
    currency: str = "INR"
    stock: int = Field(ge=0)
    description: str
    tags: list[str]
    attributes: dict[str, Any] = Field(default_factory=dict)
    frequently_bought_with: list[str] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def inr_only(cls, value: str) -> str:
        if value != "INR":
            raise ValueError("demo catalog is INR-only")
        return value

    @property
    def price_paise(self) -> int:
        return int(round(self.price_inr * 100))


class CatalogResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    merchant_id: str
    merchant_name: str
    currency: str
    schema_id: str = Field(default="agentic-commerce.catalog.v1", alias="schema")
    products: list[Product]
