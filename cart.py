from __future__ import annotations

from dataclasses import dataclass, field

from merchant.catalog_schema import Product


@dataclass
class CartItem:
    product: Product
    is_upsell: bool = False


@dataclass
class CartState:
    items: list[CartItem] = field(default_factory=list)

    @property
    def total_paise(self) -> int:
        return sum(item.product.price_paise for item in self.items)

    @property
    def total_inr(self) -> float:
        return round(self.total_paise / 100, 2)

    @property
    def upsell_count(self) -> int:
        return sum(1 for item in self.items if item.is_upsell)

    @property
    def product_ids(self) -> list[str]:
        return [item.product.id for item in self.items]

    def snapshot(self) -> dict:
        return {
            "items": [
                {
                    "id": item.product.id,
                    "name": item.product.name,
                    "price_inr": item.product.price_inr,
                    "is_upsell": item.is_upsell,
                }
                for item in self.items
            ],
            "total_inr": self.total_inr,
            "upsell_count": self.upsell_count,
        }
