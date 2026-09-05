from __future__ import annotations

from audit import audit_log
from payments.failure_handler import attempt_with_retry
from payments.razorpay_client import PaymentAttempt, RazorpayClient


def checkout_cart(
    session_id: str,
    amount_paise: int,
    simulate_decline: bool,
    client: RazorpayClient | None = None,
) -> PaymentAttempt:
    client = client or RazorpayClient()
    order = client.create_order(amount_paise, receipt=session_id)
    audit_log.write(
        session_id,
        actor="payments",
        action="create_order",
        input_data={"amount_paise": amount_paise, "amount_inr": amount_paise / 100},
        reason="Razorpay Orders API (test mode or mock if keys missing)",
        decision="created",
        outcome=order,
    )
    return attempt_with_retry(
        session_id=session_id,
        client=client,
        order=order,
        simulate_decline=simulate_decline,
    )
