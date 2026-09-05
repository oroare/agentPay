from __future__ import annotations

from audit.audit_log import events_for_session


def format_timeline(session_id: str) -> list[dict]:
    events = events_for_session(session_id)
    timeline = []
    for index, event in enumerate(events, start=1):
        timeline.append(
            {
                "step": index,
                "time": event["ts"],
                "actor": event["actor"],
                "action": event["action"],
                "decision": event["decision"],
                "reason": event["reason"],
                "outcome": event["outcome"],
                "input": event["input"],
                "headline": f"{event['actor']} · {event['action']} → {event['decision']}",
            }
        )
    return timeline
