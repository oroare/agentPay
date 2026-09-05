from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from db import get_conn, init_db


def write(
    session_id: str,
    actor: str,
    action: str,
    input_data: Any,
    reason: str,
    decision: str,
    outcome: Any,
) -> dict:
    init_db()
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "actor": actor,
        "action": action,
        "input": input_data,
        "reason": reason,
        "decision": decision,
        "outcome": outcome,
    }
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (ts, session_id, actor, action, input_json, reason, decision, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["ts"],
                session_id,
                actor,
                action,
                json.dumps(input_data, default=str),
                reason,
                decision,
                json.dumps(outcome, default=str),
            ),
        )
    return event


def events_for_session(session_id: str) -> list[dict]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT ts, session_id, actor, action, input_json, reason, decision, outcome
            FROM audit_events
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
    return [
        {
            "ts": row["ts"],
            "session_id": row["session_id"],
            "actor": row["actor"],
            "action": row["action"],
            "input": json.loads(row["input_json"]),
            "reason": row["reason"],
            "decision": row["decision"],
            "outcome": json.loads(row["outcome"]),
        }
        for row in rows
    ]
