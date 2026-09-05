from __future__ import annotations

from dataclasses import dataclass

from cart import CartState
from merchant.catalog_schema import Product


@dataclass(frozen=True)
class BudgetLimits:
    max_total_spend_inr: float
    max_upsell_amount_inr: float
    max_upsell_items: int = 1

    @property
    def max_total_spend_paise(self) -> int:
        return int(round(self.max_total_spend_inr * 100))

    @property
    def max_upsell_amount_paise(self) -> int:
        return int(round(self.max_upsell_amount_inr * 100))


@dataclass(frozen=True)
class ProposedAction:
    action: str
    cart: CartState
    product: Product | None = None
    is_upsell: bool = False
    amount_paise: int | None = None


@dataclass(frozen=True)
class GateDecision:
    approved: bool
    reason: str
    rule: str
    action: str

    def as_dict(self) -> dict:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "rule": self.rule,
            "action": self.action,
        }


def inr(paise: int) -> str:
    return f"₹{paise / 100:.2f}"
