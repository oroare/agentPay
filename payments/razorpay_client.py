from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET


@dataclass
class PaymentAttempt:
    ok: bool
    status: str
    order_id: str
    payment_id: str | None
    provider: str
    attempt: int
    detail: str


class RazorpayClient:
    def __init__(self) -> None:
        self.key_id = RAZORPAY_KEY_ID
        self.key_secret = RAZORPAY_KEY_SECRET
        self.live_sdk = None
        if self.key_id and self.key_secret:
            import razorpay

            self.live_sdk = razorpay.Client(auth=(self.key_id, self.key_secret))

    @property
    def provider(self) -> str:
        return "razorpay_test" if self.live_sdk else "razorpay_mock"

    def create_order(self, amount_paise: int, receipt: str) -> dict:
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt[:40],
            "payment_capture": 1,
        }
        if self.live_sdk:
            order = self.live_sdk.order.create(payload)
            return {
                "id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "status": order.get("status", "created"),
                "provider": "razorpay_test",
            }
        return {
            "id": f"order_mock_{uuid4().hex[:12]}",
            "amount": amount_paise,
            "currency": "INR",
            "status": "created",
            "provider": "razorpay_mock",
        }

    def collect_payment(self, order: dict, *, decline: bool, attempt: int) -> PaymentAttempt:
        """
        Checkout.js is not used in this demo. We create a real test-mode order when
        keys exist, then simulate capture/decline so the flow is demoable without a card UI.
        Razorpay decline cards (e.g. 4000000000000002) are the real-world equivalent.
        """
        if decline:
            return PaymentAttempt(
                ok=False,
                status="failed",
                order_id=order["id"],
                payment_id=None,
                provider=self.provider,
                attempt=attempt,
                detail="issuer_declined (simulated Razorpay test decline)",
            )
        return PaymentAttempt(
            ok=True,
            status="captured",
            order_id=order["id"],
            payment_id=f"pay_{uuid4().hex[:14]}",
            provider=self.provider,
            attempt=attempt,
            detail="payment captured in test mode",
        )
