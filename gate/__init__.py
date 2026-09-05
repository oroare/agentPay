from __future__ import annotations


class PolicyRejected(Exception):
    def __init__(self, reason: str, rule: str, action: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.rule = rule
        self.action = action

    def as_dict(self) -> dict:
        return {
            "approved": False,
            "reason": self.reason,
            "rule": self.rule,
            "action": self.action,
        }
