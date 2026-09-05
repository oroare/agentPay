from __future__ import annotations

from audit import audit_log
from cart import CartItem, CartState
from gate.policy_gate import evaluate
from gate.rules import BudgetLimits, ProposedAction
from merchant.catalog_api import get_product_by_id, load_catalog
from upsell_agent.offer_schema import UpsellOffer
from upsell_agent.rules import propose_upsell


def maybe_add_upsell(session_id: str, cart: CartState, limits: BudgetLimits) -> UpsellOffer | None:
    catalog = load_catalog()
    offer = propose_upsell(cart, catalog.products, limits.max_upsell_amount_inr)
    if offer is None:
        audit_log.write(
            session_id,
            actor="upsell_agent",
            action="propose_upsell",
            input_data=cart.snapshot(),
            reason="no in-budget complement found",
            decision="skip",
            outcome=None,
        )
        return None

    product = get_product_by_id(offer.product_id)
    audit_log.write(
        session_id,
        actor="upsell_agent",
        action="propose_upsell",
        input_data=offer.model_dump(),
        reason=offer.reason,
        decision="proposed",
        outcome={"rule": offer.rule},
    )
    decision = evaluate(
        ProposedAction(action="apply_upsell", cart=cart, product=product, is_upsell=True),
        limits,
    )
    audit_log.write(
        session_id,
        actor="policy_gate",
        action="apply_upsell",
        input_data={"product_id": offer.product_id, "price_inr": offer.price_inr},
        reason=decision.reason,
        decision="approve" if decision.approved else "reject",
        outcome=decision.as_dict(),
    )
    if decision.approved and product is not None:
        cart.items.append(CartItem(product=product, is_upsell=True))
        audit_log.write(
            session_id,
            actor="upsell_agent",
            action="apply_upsell",
            input_data={"product_id": product.id},
            reason="bounded upsell passed the gate",
            decision="added",
            outcome=cart.snapshot(),
        )
        return offer
    return offer
