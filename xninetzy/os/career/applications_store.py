from __future__ import annotations

import json
from datetime import datetime

from xninetzy.db.sqlite import connect, init_db


VALID_STATUSES = frozenset(
    {
        "drafted",
        "applied",
        "phone_screen",
        "interviewed",
        "offer",
        "rejected",
        "withdrawn",
    }
)
TERMINAL_STATUSES = frozenset({"offer", "rejected", "withdrawn"})


class ApplicationStore:
    def record(
        self,
        *,
        application_key: str,
        posting_id: str,
        sender_id: str,
        status: str,
        notes: str,
        now: datetime,
    ) -> dict:
        init_db()
        if status not in VALID_STATUSES:
            raise ValueError(
                f"invalid status; expected one of {sorted(VALID_STATUSES)}"
            )
        now_iso = now.isoformat()
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT id, history_json FROM career_applications WHERE application_key=?",
                (application_key,),
            ).fetchone()
            if existing is None:
                cursor = conn.execute(
                    """
                    INSERT INTO career_applications
                      (application_key, posting_id, sender_id, status, notes,
                       history_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, '[]', ?, ?)
                    """,
                    (
                        application_key,
                        posting_id,
                        sender_id or "",
                        status,
                        notes,
                        now_iso,
                        now_iso,
                    ),
                )
                application_id = cursor.lastrowid
                history: list[dict] = []
            else:
                application_id = existing["id"]
                history = json.loads(existing["history_json"] or "[]")
            history.append(
                {"status": status, "updated_at": now_iso, "notes": notes}
            )
            conn.execute(
                """
                UPDATE career_applications
                   SET status=?, notes=?, history_json=?, updated_at=?
                 WHERE id=?
                """,
                (
                    status,
                    notes,
                    json.dumps(history, ensure_ascii=False),
                    now_iso,
                    application_id,
                ),
            )
            row = conn.execute(
                "SELECT * FROM career_applications WHERE id=?",
                (application_id,),
            ).fetchone()
        return _row_to_dict(row)

    def get(self, sender_id: str, posting_id: str) -> dict | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM career_applications WHERE application_key=?",
                (_application_key(sender_id, posting_id),),
            ).fetchone()
        return _row_to_dict(row) if row else None

    def list_by_sender(self, sender_id: str, limit: int = 20) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM career_applications
                 WHERE sender_id=?
                 ORDER BY updated_at DESC
                 LIMIT ?
                """,
                (sender_id, max(1, limit)),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]


def _application_key(sender_id: str, posting_id: str) -> str:
    return f"{sender_id or ''}::{posting_id}"


def _row_to_dict(row) -> dict:
    data = dict(row)
    try:
        data["history"] = json.loads(data.get("history_json") or "[]")
    except (TypeError, ValueError):
        data["history"] = []
    return data