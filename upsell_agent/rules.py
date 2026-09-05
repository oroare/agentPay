"""Rule-based frequently-bought-together. No ML."""

from __future__ import annotations

from cart import CartState
from merchant.catalog_schema import Product
from upsell_agent.offer_schema import UpsellOffer

CATEGORY_ADDONS: dict[str, list[str]] = {
    "shoes": ["socks", "shoe-care", "insoles", "laces"],
    "socks": ["shoe-care"],
}


def propose_upsell(cart: CartState, catalog: list[Product], max_upsell_inr: float) -> UpsellOffer | None:
    if not cart.items:
        return None
    in_cart = set(cart.product_ids)
    for item in cart.items:
        preferred_ids = [sku for sku in item.product.frequently_bought_with if sku not in in_cart]
        by_id = {product.id: product for product in catalog}
        for sku in preferred_ids:
            product = by_id.get(sku)
            if product and product.stock > 0 and product.price_inr <= max_upsell_inr:
                return UpsellOffer(
                    product_id=product.id,
                    name=product.name,
                    price_inr=product.price_inr,
                    reason=f"often bought with {item.product.name}",
                    rule="sku_affinity",
                )
        allowed = CATEGORY_ADDONS.get(item.product.category, [])
        matches = [
            product
            for product in catalog
            if product.category in allowed
            and product.id not in in_cart
            and product.stock > 0
            and product.price_inr <= max_upsell_inr
        ]
        matches.sort(key=lambda product: (_use_mismatch(product, item.product), product.price_inr))
        if matches:
            product = matches[0]
            return UpsellOffer(
                product_id=product.id,
                name=product.name,
                price_inr=product.price_inr,
                reason=f"{product.category} complement for {item.product.category}",
                rule="category_addon",
            )
    return None


def _use_mismatch(addon: Product, primary: Product) -> int:
    return 0 if addon.attributes.get("use") == primary.attributes.get("use") else 1
