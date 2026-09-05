from __future__ import annotations

from audit import audit_log
from buyer_agent.goal_parser import ParsedGoal, parse_goal
from buyer_agent.ranker import rank_products
from cart import CartItem, CartState
from gate.policy_gate import evaluate
from gate.rules import BudgetLimits, ProposedAction
from merchant.catalog_api import load_catalog


def shop(
    session_id: str,
    goal_text: str,
    limits: BudgetLimits,
    force_fallback_parser: bool = False,
) -> tuple[CartState, ParsedGoal, str]:
    parsed, parser_used = parse_goal(goal_text, force_fallback=force_fallback_parser)
    audit_log.write(
        session_id,
        actor="buyer_agent",
        action="parse_goal",
        input_data={"goal": goal_text, "parser": parser_used},
        reason="turn free text into structured filters",
        decision="parsed",
        outcome=parsed.model_dump(),
    )

    catalog = load_catalog()
    audit_log.write(
        session_id,
        actor="buyer_agent",
        action="search_catalog",
        input_data={"count": len(catalog.products), "filters": parsed.model_dump()},
        reason="load AI-readable merchant catalog",
        decision="ok",
        outcome={"merchant": catalog.merchant_id, "schema": catalog.schema_id},
    )

    ranked = rank_products(catalog.products, parsed)
    audit_log.write(
        session_id,
        actor="buyer_agent",
        action="rank_products",
        input_data={"candidates": len(ranked)},
        reason="deterministic score by keyword, attributes, and price",
        decision="ranked",
        outcome=[
            {"id": product.id, "name": product.name, "score": round(score, 2), "why": why}
            for product, score, why in ranked[:5]
        ],
    )

    cart = CartState()
    if not ranked:
        audit_log.write(
            session_id,
            actor="buyer_agent",
            action="select_item",
            input_data={"goal": parsed.model_dump()},
            reason="no in-stock catalog row survived filters",
            decision="empty",
            outcome={"items": []},
        )
        return cart, parsed, parser_used

    for product, score, why in ranked:
        decision = evaluate(
            ProposedAction(action="add_to_cart", cart=cart, product=product, is_upsell=False),
            limits,
        )
        audit_log.write(
            session_id,
            actor="policy_gate",
            action="add_to_cart",
            input_data={
                "product_id": product.id,
                "price_inr": product.price_inr,
                "cart_total_inr": cart.total_inr,
                "score": round(score, 2),
                "rank_why": why,
            },
            reason=decision.reason,
            decision="approve" if decision.approved else "reject",
            outcome=decision.as_dict(),
        )
        if decision.approved:
            cart.items.append(CartItem(product=product, is_upsell=False))
            audit_log.write(
                session_id,
                actor="buyer_agent",
                action="add_to_cart",
                input_data={"product_id": product.id},
                reason="top remaining ranked item passed the gate",
                decision="added",
                outcome=cart.snapshot(),
            )
            break

    return cart, parsed, parser_used
