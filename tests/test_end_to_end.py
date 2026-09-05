from __future__ import annotations

from orchestrator.run_session import run_session


GOALS = [
    "breathable running shoes under 3000",
    "casual canvas sneakers under 2000",
    "merino hiking socks under 500",
    "waterproof rain boots under 5000",
    "hiking shoes under 3000",
]


def test_scripted_buyer_goals():
    summaries = []
    for goal in GOALS:
        result = run_session(
            goal=goal,
            max_total_spend_inr=3000 if "5000" not in goal else 5000,
            max_upsell_amount_inr=500,
            enable_upsell=True,
            simulate_decline=False,
            force_fallback_parser=True,
        )
        summaries.append(
            {
                "goal": goal,
                "status": result.status,
                "without": result.basket_without_upsell_inr,
                "with": result.basket_with_upsell_inr,
                "lift": result.lift_inr,
            }
        )
        assert result.timeline
        assert result.parser.startswith("deterministic")
        if result.status == "paid":
            assert result.payment and result.payment["ok"]
            assert result.receipt["order_id"]

    paid = [row for row in summaries if row["status"] == "paid"]
    assert len(paid) >= 3
    lifted = [row for row in paid if row["lift"] > 0]
    assert lifted, "at least one paid cart should show upsell lift"


def test_upsell_off_vs_on_lift():
    goal = "breathable running shoes under 3000"
    off = run_session(goal, 3000, 500, enable_upsell=False, force_fallback_parser=True)
    on = run_session(goal, 3000, 500, enable_upsell=True, force_fallback_parser=True)
    assert off.status == "paid"
    assert on.status == "paid"
    assert on.basket_with_upsell_inr >= off.basket_without_upsell_inr
    assert on.lift_inr >= 0


def test_gate_reject_appears_in_audit_when_budget_tiny():
    result = run_session(
        "breathable running shoes under 3000",
        max_total_spend_inr=100,
        max_upsell_amount_inr=50,
        enable_upsell=False,
        force_fallback_parser=True,
    )
    rejects = [event for event in result.timeline if event["decision"] == "reject"]
    assert rejects
    assert any(
        (event.get("outcome") or {}).get("rule") == "max_total_spend" or "cap" in event["reason"]
        for event in rejects
    )
    assert result.status == "no_items"
