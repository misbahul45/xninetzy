from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

from xninetzy.db.migrations import run_migrations
from xninetzy.db.sqlite import init_db
from xninetzy.os.auth.browser.gateway import BrowserGatewayUnavailable
from xninetzy.os.career.browser_session import (
    ApplicationSessionStore,
    FakeFormPage,
    fill_safe_fields,
    inspect_page,
)
from xninetzy.tools.tool_results import to_tool_result


_STORE = ApplicationSessionStore()


def _ensure_db() -> None:
    init_db()
    run_migrations()


def _emit_checkpoint(plan_id: str, step_id: str, status: str, payload: dict[str, Any]) -> None:
    _ensure_db()
    from xninetzy.db.sqlite import connect

    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO observability_events
              (event_kind, severity, source, subject, payload_json, occurred_at)
            VALUES ('harness_checkpoint', 'info', 'career_browser', ?, ?, ?)
            """,
            (
                f"{plan_id}:{step_id}",
                json.dumps({"status": status, **payload}, ensure_ascii=False),
                now,
            ),
        )


def _gateway_open(posting_url: str, sender_id: str) -> tuple[Any, Any, Any]:
    from xninetzy.os.auth.browser.gateway import (
        launch_local_browser,
    )

    session_id = f"career-browser-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{sender_id[:8]}"
    payload = launch_local_browser(
        session_id=session_id,
        owner=sender_id or "career-browser",
        headless=True,
    )
    return payload, session_id


def _safe_to_dict_for_page(page: FakeFormPage) -> dict[str, Any]:
    inspected = inspect_page(page)
    return inspected.to_safe_dict()


@tool
def career_open_application(
    posting_id: str,
    posting_url: str,
    sender_id: str = "",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    idempotency_key: str = "",
) -> str:
    """Open an isolated browser session for an application and return the safe form structure.

    The session is bound to (sender_id, posting_id). Submission is NEVER performed
    by this tool — the owner must explicitly run career_fill_application to populate
    fields, and any submission requires a separate confirmation token.

    Args:
        posting_id: Posting identifier.
        posting_url: Public URL of the application form.
        sender_id: Owner principal.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        idempotency_key: Optional idempotency key.
    """
    _ensure_db()
    if not posting_url.startswith(("http://", "https://")):
        out = {"status_flag": "error", "error": "posting_url must be http(s)"}
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_open_application", "invalid_url", {})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    application_key = f"{sender_id or ''}::{posting_id}"
    try:
        record = _STORE.open(
            application_key=application_key,
            posting_id=posting_id,
            sender_id=sender_id,
            posting_url=posting_url,
        )
    except ValueError as exc:
        out = {"status_flag": "error", "error": str(exc)}
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_open_application", "duplicate", {})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    html = "<html><body>no live page available</body></html>"
    page = FakeFormPage(_url=posting_url, _title="(pending)", _html=html)
    try:
        from xninetzy.os.research.sources.browser_session import make_session

        async def _open() -> str:
            session = make_session()
            return await session.get_html(posting_url)

        try:
            import asyncio

            live_html = asyncio.run(_open())
            page = FakeFormPage(_url=posting_url, _title="(live)", _html=live_html)
        except (BrowserGatewayUnavailable, Exception):
            pass
    except Exception:
        pass
    _STORE.attach_page(record.session_id, page)
    inspected = inspect_page(page)
    out = {
        "status_flag": "ok",
        "session": record.to_safe_dict(),
        "form": inspected.to_safe_dict(),
        "submission_not_performed": True,
    }
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_open_application",
            "ok",
            {
                "session_id": record.session_id[:8] + "...",
                "safe_count": inspected.safe_count,
                "blocked_count": inspected.blocked_count,
            },
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


@tool
def career_inspect_application(
    session_id: str,
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Re-inspect the current page state of an open application session.

    Returns form fields, current URL, and counts — NEVER returns cookies, tokens,
    or values typed into unsafe fields.

    Args:
        session_id: Session id returned by career_open_application.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    _ensure_db()
    record = _STORE.get(session_id)
    if record is None:
        out = {"status_flag": "not_found", "session_id": session_id}
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_inspect_application", "not_found", {})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    if record.state == "closed":
        out = {"status_flag": "closed", "session": record.to_safe_dict()}
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    page = _STORE.get_page(session_id)
    if page is None:
        out = {
            "status_flag": "error",
            "error": "no page attached to session (test-only path)",
            "session": record.to_safe_dict(),
        }
        if plan_id:
            _emit_checkpoint(
                plan_id, step_id or "career_inspect_application", "no_page", {}
            )
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    _STORE.inspect(session_id)
    inspected = inspect_page(page)
    out = {
        "status_flag": "ok",
        "session": record.to_safe_dict(),
        "form": inspected.to_safe_dict(),
    }
    if plan_id:
        _emit_checkpoint(plan_id, step_id or "career_inspect_application", "ok", {})
    return to_tool_result(json.dumps(out, ensure_ascii=False))


@tool
def career_fill_application(
    session_id: str,
    fields_json: str = "{}",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Fill ONLY safe fields in an open application session. NEVER submits.

    The tool classifies every field via the safe-field filter and refuses to type into
    password / submit / hidden / file / consent fields. Returned summary NEVER echoes the
    typed value for unsafe fields.

    Args:
        session_id: Session id returned by career_open_application.
        fields_json: JSON object mapping field name → value (string).
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    _ensure_db()
    record = _STORE.get(session_id)
    if record is None:
        out = {"status_flag": "not_found", "session_id": session_id}
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_fill_application", "not_found", {})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    if record.state != "open":
        out = {"status_flag": "closed", "session": record.to_safe_dict()}
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    if record.sender_id and sender_id and record.sender_id != sender_id:
        out = {"status_flag": "error", "error": "sender mismatch"}
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_fill_application", "sender_mismatch", {})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    try:
        values = json.loads(fields_json)
        if not isinstance(values, dict):
            raise ValueError("fields_json must decode to an object")
    except (json.JSONDecodeError, ValueError) as exc:
        out = {"status_flag": "error", "error": f"invalid fields_json: {exc}"}
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_fill_application", "bad_input", {})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    page = _STORE.get_page(session_id)
    if page is None:
        out = {"status_flag": "error", "error": "no page attached to session"}
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_fill_application", "no_page", {})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    result = fill_safe_fields(page, {str(k): str(v) for k, v in values.items()})
    out = {
        "status_flag": "ok",
        "session_id": session_id,
        "summary": result.to_safe_dict(),
        "submission_not_performed": True,
    }
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_fill_application",
            "ok",
            {"filled": len(result.filled), "skipped": len(result.skipped)},
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


@tool
def career_close_application(
    session_id: str,
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Close an application browser session and release its resources.

    Args:
        session_id: Session id returned by career_open_application.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    _ensure_db()
    record = _STORE.get(session_id)
    if record is None:
        out = {"status_flag": "not_found", "session_id": session_id}
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    if record.sender_id and sender_id and record.sender_id != sender_id:
        out = {"status_flag": "error", "error": "sender mismatch"}
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    closed = _STORE.close(session_id)
    out = {
        "status_flag": "closed" if closed else "noop",
        "session": record.to_safe_dict(),
    }
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_close_application",
            "closed" if closed else "noop",
            {},
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


career_browser_tools = [
    career_open_application,
    career_inspect_application,
    career_fill_application,
    career_close_application,
]


__all__ = [
    "career_browser_tools",
    "career_close_application",
    "career_fill_application",
    "career_inspect_application",
    "career_open_application",
]
