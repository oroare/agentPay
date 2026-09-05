from __future__ import annotations

from audit import audit_log
from payments.razorpay_client import PaymentAttempt, RazorpayClient


def attempt_with_retry(
    session_id: str,
    client: RazorpayClient,
    order: dict,
    simulate_decline: bool,
) -> PaymentAttempt:
    first = client.collect_payment(order, decline=simulate_decline, attempt=1)
    audit_log.write(
        session_id,
        actor="payments",
        action="collect_payment",
        input_data={"order_id": order["id"], "attempt": 1, "simulate_decline": simulate_decline},
        reason=first.detail,
        decision="captured" if first.ok else "declined",
        outcome=_attempt_payload(first),
    )
    if first.ok:
        return first

    audit_log.write(
        session_id,
        actor="payments",
        action="retry_payment",
        input_data={"order_id": order["id"], "attempt": 2},
        reason="one retry after issuer decline, same order, no extra spend",
        decision="retry",
        outcome={"max_retries": 1},
    )
    second = client.collect_payment(order, decline=simulate_decline, attempt=2)
    audit_log.write(
        session_id,
        actor="payments",
        action="collect_payment",
        input_data={"order_id": order["id"], "attempt": 2, "simulate_decline": simulate_decline},
        reason=second.detail,
        decision="captured" if second.ok else "declined",
        outcome=_attempt_payload(second),
    )
    if second.ok:
        return second

    audit_log.write(
        session_id,
        actor="payments",
        action="fail_clean",
        input_data={"order_id": order["id"]},
        reason="issuer declined twice; stopping without charging the buyer",
        decision="failed",
        outcome={
            "human_reason": "Payment was declined by the test issuer. Nothing was captured.",
            "next_step": "Ask the buyer for another method; cart was not charged.",
        },
    )
    return second


def _attempt_payload(attempt: PaymentAttempt) -> dict:
    return {
        "ok": attempt.ok,
        "status": attempt.status,
        "order_id": attempt.order_id,
        "payment_id": attempt.payment_id,
        "provider": attempt.provider,
        "attempt": attempt.attempt,
        "detail": attempt.detail,
    }
