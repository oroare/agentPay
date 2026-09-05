from __future__ import annotations

from cart import CartItem, CartState
from gate.policy_gate import evaluate
from gate.rules import BudgetLimits, ProposedAction
from merchant.catalog_api import get_product_by_id, load_catalog

LIMITS = BudgetLimits(max_total_spend_inr=3000, max_upsell_amount_inr=500, max_upsell_items=1)


def _product(sku: str):
    product = get_product_by_id(sku)
    assert product is not None
    return product


def test_catalog_is_well_formed():
    catalog = load_catalog()
    assert catalog.schema_id == "agentic-commerce.catalog.v1"
    assert 15 <= len(catalog.products) <= 40
    for product in catalog.products:
        assert product.price_inr > 0
        assert product.currency == "INR"


def test_approve_in_budget_add():
    cart = CartState()
    decision = evaluate(ProposedAction("add_to_cart", cart, _product("SHOE-001")), LIMITS)
    assert decision.approved
    assert decision.rule == "pass"


def test_reject_over_max_total_spend():
    cart = CartState(items=[CartItem(_product("SHOE-001"))])
    # SHOE-001 is 2499; SHOE-003 is 1799 → 4298 > 3000
    decision = evaluate(ProposedAction("add_to_cart", cart, _product("SHOE-003")), LIMITS)
    assert not decision.approved
    assert decision.rule == "max_total_spend"
    assert "over the cap" in decision.reason


def test_reject_upsell_over_cap():
    cart = CartState(items=[CartItem(_product("SHOE-003"))])
    # INSOLE-002 is 799 > 500 upsell cap
    decision = evaluate(
        ProposedAction("apply_upsell", cart, _product("INSOLE-002"), is_upsell=True),
        LIMITS,
    )
    assert not decision.approved
    assert decision.rule == "max_upsell_amount"


def test_reject_second_upsell():
    cart = CartState(
        items=[
            CartItem(_product("SHOE-001")),
            CartItem(_product("SOCK-002"), is_upsell=True),
        ]
    )
    decision = evaluate(
        ProposedAction("apply_upsell", cart, _product("LACE-001"), is_upsell=True),
        LIMITS,
    )
    assert not decision.approved
    assert decision.rule == "max_upsell_items"


def test_reject_out_of_stock(monkeypatch):
    product = _product("SHOE-001").model_copy(update={"stock": 0})
    decision = evaluate(ProposedAction("add_to_cart", CartState(), product), LIMITS)
    assert not decision.approved
    assert decision.rule == "in_stock"


def test_reject_empty_checkout():
    decision = evaluate(ProposedAction("checkout", CartState()), LIMITS)
    assert not decision.approved
    assert decision.rule == "non_empty_cart"
