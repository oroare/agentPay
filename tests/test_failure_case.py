from __future__ import annotations

from payments.failure_handler import attempt_with_retry
from payments.razorpay_client import RazorpayClient
from orchestrator.run_session import run_session


def test_decline_retries_once_then_clean_fail():
    client = RazorpayClient()
    order = client.create_order(249900, receipt="fail-demo")
    result = attempt_with_retry("ses_fail", client, order, simulate_decline=True)
    assert result.ok is False
    assert result.attempt == 2
    assert result.status == "failed"


def test_session_payment_failed_does_not_mark_paid():
    result = run_session(
        "breathable running shoes under 3000",
        max_total_spend_inr=3000,
        max_upsell_amount_inr=500,
        enable_upsell=True,
        simulate_decline=True,
        force_fallback_parser=True,
    )
    assert result.status == "payment_failed"
    assert result.receipt["status"] == "payment_failed"
    assert "not charged" in result.receipt["message"].lower() or "declined" in result.receipt["message"].lower()
    decisions = [event["decision"] for event in result.timeline]
    assert decisions.count("declined") == 2
    assert "retry" in decisions
    assert "failed" in decisions
