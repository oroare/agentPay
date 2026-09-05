from __future__ import annotations

from pydantic import BaseModel, Field


class UpsellOffer(BaseModel):
    product_id: str
    name: str
    price_inr: float = Field(gt=0)
    reason: str
    rule: str
    bounded: bool = True
