from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from xninetzy.db.migrations import run_migrations
from xninetzy.db.sqlite import connect, init_db
from xninetzy.os.career.applications_store import VALID_STATUSES
from xninetzy.os.career.orchestrator import ApplicationOrchestrator
from xninetzy.tools.tool_results import to_tool_result


_ORCHESTRATOR = ApplicationOrchestrator()


def _ensure_db() -> None:
    init_db()
    run_migrations()


def _emit_checkpoint(plan_id: str, step_id: str, status: str, payload: dict[str, Any]) -> None:
    _ensure_db()
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO observability_events
              (event_kind, severity, source, subject, payload_json, occurred_at)
            VALUES ('harness_checkpoint', 'info', 'career_orchestrator', ?, ?, ?)
            """,
            (
                f"{plan_id}:{step_id}",
                json.dumps({"status": status, **payload}, ensure_ascii=False),
                now,
            ),
        )


@tool
def career_request_application_change(
    posting_id: str,
    target_status: str,
    sender_id: str = "",
    notes: str = "",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    idempotency_key: str = "",
) -> str:
    """Issue a single-use confirmation token for an application status change.

    The owner must then call career_confirm_application with the token. Without the
    confirm step, no state mutation occurs. Token TTL is 5 minutes, app-bound, single-use.

    Args:
        posting_id: Posting identifier.
        target_status: drafted | applied | phone_screen | interviewed | offer | rejected | withdrawn.
        sender_id: Owner principal.
        notes: Optional context to persist with the change.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        idempotency_key: Optional idempotency key.
    """
    if target_status not in VALID_STATUSES:
        out = {
            "status_flag": "error",
            "error": f"invalid status; expected one of {sorted(VALID_STATUSES)}",
        }
        if plan_id:
            _emit_checkpoint(
                plan_id,
                step_id or "career_request_application_change",
                "invalid",
                {"target_status": target_status},
            )
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    result = _ORCHESTRATOR.request_status_change(
        posting_id=posting_id,
        sender_id=sender_id,
        target_status=target_status,
        notes=notes,
    )
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_request_application_change",
            "awaiting_confirmation",
            {"target_status": target_status, "application_key": result["application_key"]},
        )
    return to_tool_result(json.dumps(result, ensure_ascii=False))


@tool
def career_confirm_application(
    token: str,
    sender_id: str = "",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    idempotency_key: str = "",
) -> str:
    """Consume a confirmation token and apply the status change.

    The token must have been issued by career_request_application_change, must be unexpired,
    must be unconsumed, and must belong to the calling sender. Otherwise no mutation occurs.

    Args:
        token: Single-use confirmation token.
        sender_id: Owner principal.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        idempotency_key: Optional idempotency key.
    """
    result = _ORCHESTRATOR.confirm_status_change(token=token, sender_id=sender_id)
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_confirm_application",
            result["status_flag"],
            {"posting_id": (result.get("application") or {}).get("posting_id")},
        )
    return to_tool_result(json.dumps(result, ensure_ascii=False))


@tool
def career_record_application_outcome(
    posting_id: str,
    source: str,
    outcome: str,
    sender_id: str = "",
    reason: str = "",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    idempotency_key: str = "",
) -> str:
    """Record an application outcome (interview, offer, reject) and update source quality.

    Outcomes feed a closed loop: future searches weight sources by observed interview/offer rates.
    Valid outcomes: interview, offer, reject, withdrawn, no_response.

    Args:
        posting_id: Posting identifier.
        source: Originating adapter id (e.g. 'remoteok', 'arbeitnow', 'kalibrr').
        outcome: interview | offer | reject | withdrawn | no_response.
        sender_id: Owner principal.
        reason: Optional free-text reason.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        idempotency_key: Optional idempotency key.
    """
    _ensure_db()
    valid_outcomes = {"interview", "offer", "reject", "withdrawn", "no_response"}
    if outcome not in valid_outcomes:
        out = {
            "status_flag": "error",
            "error": f"invalid outcome; expected one of {sorted(valid_outcomes)}",
        }
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).isoformat()
    application_key = f"{sender_id or ''}::{posting_id}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO career_outcomes
              (application_key, posting_id, source, outcome, reason, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (application_key, posting_id, source, outcome, reason, now_iso),
        )
        row = conn.execute(
            "SELECT * FROM career_source_quality WHERE source=?", (source,)
        ).fetchone()
        postings_total = (row["postings_total"] if row else 0) + 1
        outcomes_total = (row["outcomes_total"] if row else 0) + 1
        interviews_total = (row["interviews_total"] if row else 0) + (1 if outcome == "interview" else 0)
        offers_total = (row["offers_total"] if row else 0) + (1 if outcome == "offer" else 0)
        rejects_total = (row["rejects_total"] if row else 0) + (1 if outcome == "reject" else 0)
        if row is None:
            interview_rate = interviews_total / max(1, outcomes_total)
            offer_rate = offers_total / max(1, outcomes_total)
            reject_rate = rejects_total / max(1, outcomes_total)
            initial_quality = max(
                0.05,
                min(
                    0.95,
                    0.4 + 0.6 * (interview_rate + offer_rate) - 0.4 * reject_rate,
                ),
            )
            conn.execute(
                """
                INSERT INTO career_source_quality
                  (source, postings_total, outcomes_total, interviews_total,
                   offers_total, rejects_total, quality_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    postings_total,
                    outcomes_total,
                    interviews_total,
                    offers_total,
                    rejects_total,
                    initial_quality,
                    now_iso,
                ),
            )
        else:
            interview_rate = interviews_total / max(1, outcomes_total)
            offer_rate = offers_total / max(1, outcomes_total)
            reject_rate = rejects_total / max(1, outcomes_total)
            quality_score = max(
                0.05,
                min(
                    0.95,
                    0.4 + 0.6 * (interview_rate + offer_rate) - 0.4 * reject_rate,
                ),
            )
            conn.execute(
                """
                UPDATE career_source_quality
                   SET postings_total=?, outcomes_total=?, interviews_total=?,
                       offers_total=?, rejects_total=?, quality_score=?, updated_at=?
                 WHERE source=?
                """,
                (
                    postings_total,
                    outcomes_total,
                    interviews_total,
                    offers_total,
                    rejects_total,
                    quality_score,
                    now_iso,
                    source,
                ),
            )
    with connect() as conn:
        updated = conn.execute(
            "SELECT * FROM career_source_quality WHERE source=?", (source,)
        ).fetchone()
    out = {
        "status_flag": "ok",
        "outcome_recorded": outcome,
        "source_quality": dict(updated),
    }
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_record_application_outcome",
            "ok",
            {"outcome": outcome, "source": source, "quality": updated["quality_score"]},
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


career_orchestrator_tools = [
    career_request_application_change,
    career_confirm_application,
    career_record_application_outcome,
]


__all__ = [
    "career_confirm_application",
    "career_orchestrator_tools",
    "career_record_application_outcome",
    "career_request_application_change",
]
