from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4

from audit import audit_log
from audit.audit_viewer import format_timeline
from buyer_agent.agent import shop
from cart import CartState
from config import BUDGET_CONFIG_PATH
from db import get_conn, init_db
from gate.policy_gate import evaluate
from gate.rules import BudgetLimits, ProposedAction
from payments.order_flow import checkout_cart
from upsell_agent.agent import maybe_add_upsell


@dataclass
class SessionResult:
    session_id: str
    status: str
    goal: str
    parser: str
    parsed_goal: dict
    limits: dict
    cart: dict
    basket_without_upsell_inr: float
    basket_with_upsell_inr: float
    lift_inr: float
    lift_pct: float
    payment: dict | None
    receipt: dict
    timeline: list[dict]
    gate_one_liner: str = (
        "Hard rule: cart + any upsell must stay ≤ max_total_spend, and a single upsell "
        "must stay ≤ max_upsell_amount — enforced in code, never by the LLM."
    )


def default_limits() -> BudgetLimits:
    raw = json.loads(BUDGET_CONFIG_PATH.read_text(encoding="utf-8"))
    return BudgetLimits(
        max_total_spend_inr=float(raw["max_total_spend_inr"]),
        max_upsell_amount_inr=float(raw["max_upsell_amount_inr"]),
        max_upsell_items=int(raw.get("max_upsell_items", 1)),
    )


def run_session(
    goal: str,
    max_total_spend_inr: float | None = None,
    max_upsell_amount_inr: float | None = None,
    enable_upsell: bool = True,
    simulate_decline: bool = False,
    force_fallback_parser: bool = False,
    session_id: str | None = None,
) -> SessionResult:
    init_db()
    session_id = session_id or f"ses_{uuid4().hex[:10]}"
    base = default_limits()
    limits = BudgetLimits(
        max_total_spend_inr=max_total_spend_inr if max_total_spend_inr is not None else base.max_total_spend_inr,
        max_upsell_amount_inr=(
            max_upsell_amount_inr if max_upsell_amount_inr is not None else base.max_upsell_amount_inr
        ),
        max_upsell_items=base.max_upsell_items,
    )

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, goal, budget_json, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                session_id,
                goal,
                json.dumps(
                    {
                        "max_total_spend_inr": limits.max_total_spend_inr,
                        "max_upsell_amount_inr": limits.max_upsell_amount_inr,
                    }
                ),
                "running",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    audit_log.write(
        session_id,
        actor="human",
        action="start_session",
        input_data={
            "goal": goal,
            "max_total_spend_inr": limits.max_total_spend_inr,
            "max_upsell_amount_inr": limits.max_upsell_amount_inr,
            "enable_upsell": enable_upsell,
            "simulate_decline": simulate_decline,
        },
        reason="buyer stated a goal and a hard spend cap",
        decision="accepted",
        outcome={"session_id": session_id},
    )

    cart, parsed, parser = shop(session_id, goal, limits, force_fallback_parser=force_fallback_parser)
    primary_total = cart.total_inr

    if enable_upsell and cart.items:
        maybe_add_upsell(session_id, cart, limits)

    lift_inr = round(cart.total_inr - primary_total, 2)
    lift_pct = round((lift_inr / primary_total) * 100, 2) if primary_total else 0.0

    payment_payload = None
    status = "no_items"
    receipt: dict

    if not cart.items:
        audit_log.write(
            session_id,
            actor="orchestrator",
            action="abort",
            input_data={"goal": goal},
            reason="buyer agent could not place a gated item in the cart",
            decision="stop",
            outcome={"status": "no_items"},
        )
        receipt = {
            "status": "no_items",
            "message": "No item matched the goal inside the policy gate. Nothing charged.",
            "total_inr": 0,
        }
    else:
        checkout_decision = evaluate(ProposedAction(action="checkout", cart=cart), limits)
        audit_log.write(
            session_id,
            actor="policy_gate",
            action="checkout",
            input_data=cart.snapshot(),
            reason=checkout_decision.reason,
            decision="approve" if checkout_decision.approved else "reject",
            outcome=checkout_decision.as_dict(),
        )
        if not checkout_decision.approved:
            status = "blocked_by_gate"
            receipt = {
                "status": status,
                "message": checkout_decision.reason,
                "total_inr": cart.total_inr,
            }
        else:
            attempt = checkout_cart(session_id, cart.total_paise, simulate_decline=simulate_decline)
            payment_payload = asdict(attempt)
            if attempt.ok:
                status = "paid"
                receipt = {
                    "status": "paid",
                    "message": "Razorpay test-mode payment captured.",
                    "order_id": attempt.order_id,
                    "payment_id": attempt.payment_id,
                    "provider": attempt.provider,
                    "total_inr": cart.total_inr,
                    "items": cart.snapshot()["items"],
                }
            else:
                status = "payment_failed"
                receipt = {
                    "status": "payment_failed",
                    "message": "Payment declined twice. Cart was not charged.",
                    "order_id": attempt.order_id,
                    "provider": attempt.provider,
                    "total_inr": cart.total_inr,
                    "items": cart.snapshot()["items"],
                }

    audit_log.write(
        session_id,
        actor="orchestrator",
        action="finalize",
        input_data={"status": status},
        reason="session complete",
        decision=status,
        outcome=receipt,
    )

    _persist_cart(session_id, cart, status, receipt)
    result = SessionResult(
        session_id=session_id,
        status=status,
        goal=goal,
        parser=parser,
        parsed_goal=parsed.model_dump(),
        limits={
            "max_total_spend_inr": limits.max_total_spend_inr,
            "max_upsell_amount_inr": limits.max_upsell_amount_inr,
            "max_upsell_items": limits.max_upsell_items,
        },
        cart=cart.snapshot(),
        basket_without_upsell_inr=primary_total,
        basket_with_upsell_inr=cart.total_inr,
        lift_inr=lift_inr,
        lift_pct=lift_pct,
        payment=payment_payload,
        receipt=receipt,
        timeline=format_timeline(session_id),
    )
    return result


def _persist_cart(session_id: str, cart: CartState, status: str, receipt: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET status = ?, receipt_json = ? WHERE id = ?",
            (status, json.dumps(receipt), session_id),
        )
        for item in cart.items:
            conn.execute(
                """
                INSERT INTO cart_items (session_id, product_id, name, price_paise, is_upsell)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, item.product.id, item.product.name, item.product.price_paise, int(item.is_upsell)),
            )
