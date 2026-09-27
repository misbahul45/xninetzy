from __future__ import annotations

import json

from langchain_core.tools import tool

from xninetzy.db.migrations import run_migrations
from xninetzy.db.sqlite import init_db
from xninetzy.os.career.orchestrator import ApplicationOrchestrator
from xninetzy.os.career.dashboard import (
    build_dashboard,
    recovery_snapshot,
)
from xninetzy.tools.tool_results import to_tool_result


_ORCHESTRATOR = ApplicationOrchestrator()


def _emit_checkpoint(plan_id: str, step_id: str, status: str, payload: dict) -> None:
    init_db()
    run_migrations()
    from datetime import datetime, timezone

    from xninetzy.db.sqlite import connect

    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO observability_events
              (event_kind, severity, source, subject, payload_json, occurred_at)
            VALUES ('harness_checkpoint', 'info', 'career_dashboard', ?, ?, ?)
            """,
            (
                f"{plan_id}:{step_id}",
                json.dumps({"status": status, **payload}, ensure_ascii=False),
                now,
            ),
        )


@tool
def career_observability_dashboard(
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Live operational snapshot for the career intelligence subsystem.

    Aggregates: registered adapters, compliance audit, search cache hit/miss/evict,
    source quality scores (from outcome feedback loop), per-state application
    distribution, browser session counts, active confirmation tokens, observability
    event counters, and totals.

    Args:
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    snapshot = build_dashboard()
    if plan_id:
        _emit_checkpoint(plan_id, step_id or "career_observability_dashboard", "ok", {"size": snapshot["search_cache"]["size"]})
    return to_tool_result(json.dumps(snapshot, ensure_ascii=False, default=str))


@tool
def career_recover_stuck_applications(
    stuck_after_days: int = 7,
    mark_as: str = "withdrawn",
    sender_id: str = "",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    idempotency_key: str = "",
) -> str:
    """Owner-gated recovery: list (or mark) applications stuck in non-terminal state.

    An application is "stuck" if it has been in drafted/applied/phone_screen/interviewed
    for more than `stuck_after_days` without progress. This tool either:
    - Reports them (if mark_as="report")
    - Marks them all as `mark_as` (e.g. "withdrawn") — requires explicit owner action.

    Args:
        stuck_after_days: Threshold for stuck detection.
        mark_as: report | withdrawn | rejected.
        sender_id: Owner principal.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        idempotency_key: Optional idempotency key.
    """
    init_db()
    run_migrations()
    stuck = recovery_snapshot(stuck_after_days=stuck_after_days)
    out: dict = {
        "status_flag": "ok",
        "stuck_after_days": stuck_after_days,
        "stuck_count": len(stuck),
        "stuck_applications": stuck,
        "marked_as": mark_as,
        "owner_action_performed": False,
    }
    if mark_as not in {"report", "withdrawn", "rejected"}:
        out["status_flag"] = "error"
        out["error"] = "invalid mark_as; expected one of report/withdrawn/rejected"
        if plan_id:
            _emit_checkpoint(
                plan_id, step_id or "career_recover_stuck_applications", "bad_input", {"count": len(stuck)}
            )
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    if not sender_id:
        out["status_flag"] = "error"
        out["error"] = "sender_id is required to mutate state"
        if plan_id:
            _emit_checkpoint(
                plan_id, step_id or "career_recover_stuck_applications", "no_sender", {"count": len(stuck)}
            )
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    if mark_as == "report":
        if plan_id:
            _emit_checkpoint(
                plan_id, step_id or "career_recover_stuck_applications", "reported", {"count": len(stuck)}
            )
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    from datetime import datetime, timezone


    now_iso = datetime.now(timezone.utc).isoformat()
    acknowledged: list[dict] = []
    for stuck_record in stuck:
        owner_recorded_at = stuck_record["updated_at"]
        key = stuck_record["application_key"]
        try:
            _ORCHESTRATOR._applications.record(
                application_key=key,
                posting_id=key.split("::", 1)[1] if "::" in key else key,
                sender_id=sender_id,
                status=mark_as,
                notes=f"recovery: stuck > {stuck_after_days}d (last updated {owner_recorded_at})",
                now=datetime.now(timezone.utc),
            )
        except ValueError:
            continue
        acknowledged.append(
            {"application_key": key, "previous_status": stuck_record["status"], "new_status": mark_as, "recorded_at": now_iso}
        )
    out["owner_action_performed"] = True
    out["acknowledged"] = acknowledged
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_recover_stuck_applications",
            "marked",
            {"count": len(acknowledged), "as": mark_as},
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


career_dashboard_tools = [
    career_observability_dashboard,
    career_recover_stuck_applications,
]


__all__ = [
    "career_dashboard_tools",
    "career_observability_dashboard",
    "career_recover_stuck_applications",
]
