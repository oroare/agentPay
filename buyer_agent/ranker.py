"""Deterministic ranking. No LLM. Scores are reproducible for a given catalog + goal."""

from __future__ import annotations

from merchant.catalog_schema import Product

from buyer_agent.goal_parser import ParsedGoal


def rank_products(products: list[Product], goal: ParsedGoal) -> list[tuple[Product, float, str]]:
    scored: list[tuple[Product, float, str]] = []
    for product in products:
        if product.stock <= 0:
            continue
        if goal.max_price_inr is not None and product.price_inr > goal.max_price_inr:
            continue
        if goal.category and product.category != goal.category:
            continue
        if not _attributes_ok(product, goal):
            continue
        score, why = _score(product, goal)
        scored.append((product, score, why))
    scored.sort(key=lambda row: (-row[1], row[0].price_inr, row[0].id))
    return scored


def _attributes_ok(product: Product, goal: ParsedGoal) -> bool:
    for attr in goal.must_have_attributes:
        value = product.attributes.get(attr)
        if value is True:
            continue
        if attr in product.tags:
            continue
        return False
    return True


def _score(product: Product, goal: ParsedGoal) -> tuple[float, str]:
    haystack = " ".join(
        [product.name, product.description, product.category, *product.tags, *map(str, product.attributes.values())]
    ).lower()
    hits = [kw for kw in goal.keywords if kw in haystack]
    keyword_score = min(len(hits) * 12, 48)
    attr_score = 20 * len(goal.must_have_attributes)
    price_score = 0.0
    if goal.max_price_inr:
        # Prefer items that use the budget without hugging the ceiling blindly.
        ratio = product.price_inr / goal.max_price_inr
        price_score = 25 * (1 - abs(0.75 - ratio))
    in_stock_bonus = min(product.stock, 10)
    total = keyword_score + attr_score + price_score + in_stock_bonus
    why = (
        f"keywords={hits or ['(none)']}; attrs={goal.must_have_attributes or ['(none)']}; "
        f"price={product.price_inr}; score={total:.1f}"
    )
    return total, why
