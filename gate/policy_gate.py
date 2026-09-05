"""Pure policy checks. No LLM. Money decisions live here only."""

from __future__ import annotations

from gate.gate_exceptions import PolicyRejected
from gate.rules import BudgetLimits, GateDecision, ProposedAction, inr


def evaluate(proposal: ProposedAction, limits: BudgetLimits) -> GateDecision:
    action = proposal.action
    cart = proposal.cart
    product = proposal.product

    if action not in {"add_to_cart", "apply_upsell", "checkout"}:
        return GateDecision(False, f"unknown action '{action}'", "allowed_actions", action)

    if action == "checkout":
        if not cart.items:
            return GateDecision(False, "cannot checkout an empty cart", "non_empty_cart", action)
        if cart.total_paise > limits.max_total_spend_paise:
            return GateDecision(
                False,
                f"cart total {inr(cart.total_paise)} exceeds max spend {inr(limits.max_total_spend_paise)}",
                "max_total_spend",
                action,
            )
        return GateDecision(True, "checkout within spend cap", "max_total_spend", action)

    if product is None:
        return GateDecision(False, "item required for cart mutation", "item_present", action)

    if product.price_paise <= 0:
        return GateDecision(False, "item price must be positive", "positive_price", action)

    if product.stock <= 0:
        return GateDecision(False, f"{product.id} is out of stock", "in_stock", action)

    if product.id in cart.product_ids:
        return GateDecision(False, f"{product.id} is already in the cart", "no_duplicate_sku", action)

    projected = cart.total_paise + product.price_paise
    if projected > limits.max_total_spend_paise:
        return GateDecision(
            False,
            (
                f"adding {product.id} at {inr(product.price_paise)} would make the cart "
                f"{inr(projected)}, over the cap {inr(limits.max_total_spend_paise)}"
            ),
            "max_total_spend",
            action,
        )

    if proposal.is_upsell or action == "apply_upsell":
        if cart.upsell_count >= limits.max_upsell_items:
            return GateDecision(
                False,
                f"at most {limits.max_upsell_items} upsell item(s) allowed",
                "max_upsell_items",
                action,
            )
        if product.price_paise > limits.max_upsell_amount_paise:
            return GateDecision(
                False,
                (
                    f"upsell {product.id} at {inr(product.price_paise)} exceeds "
                    f"upsell cap {inr(limits.max_upsell_amount_paise)}"
                ),
                "max_upsell_amount",
                action,
            )

    return GateDecision(True, "within budget, stock, and upsell limits", "pass", action)


def assert_allowed(proposal: ProposedAction, limits: BudgetLimits) -> GateDecision:
    decision = evaluate(proposal, limits)
    if not decision.approved:
        raise PolicyRejected(decision.reason, decision.rule, decision.action)
    return decision
