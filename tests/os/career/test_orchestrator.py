from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def sqlite_db(monkeypatch, tmp_path):
    from xninetzy.core.config import get_settings

    db = tmp_path / "orch.sqlite3"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    get_settings.cache_clear()
    from xninetzy.db.migrations import run_migrations
    from xninetzy.db.sqlite import init_db

    init_db()
    run_migrations()
    yield db
    get_settings.cache_clear()


def test_request_returns_awaiting_confirmation_token(sqlite_db):
    from xninetzy.os.career.orchestrator import ApplicationOrchestrator

    orch = ApplicationOrchestrator()
    out = orch.request_status_change(
        posting_id="remoteok-1",
        sender_id="owner-1",
        target_status="applied",
    )
    assert out["status_flag"] == "awaiting_confirmation"
    assert out["application_key"] == "owner-1::remoteok-1"
    assert out["target_status"] == "applied"
    assert "expires_at" in out
    assert out["confirm_via"] == "career_confirm_application"


def test_confirm_with_valid_token_mutates_state(sqlite_db):
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_confirm_application,
        career_request_application_change,
    )

    raw_issue = career_request_application_change.func(
        posting_id="remoteok-2",
        target_status="applied",
        sender_id="owner-2",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    envelope = json.loads(raw_issue)
    summary = json.loads(envelope["summary"])
    assert summary["status_flag"] == "awaiting_confirmation"
    from xninetzy.db.sqlite import connect

    with connect() as conn:
        row = conn.execute(
            "SELECT token FROM career_confirmation_tokens WHERE application_key=?",
            ("owner-2::remoteok-2",),
        ).fetchone()
    full_token = row["token"]
    raw_confirm = career_confirm_application.func(
        token=full_token,
        sender_id="owner-2",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    confirm_payload = json.loads(json.loads(raw_confirm)["summary"])
    assert confirm_payload["status_flag"] == "submitted"
    assert confirm_payload["application"]["status"] == "applied"


def test_confirm_rejects_invalid_token(sqlite_db):
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_confirm_application,
    )

    raw = career_confirm_application.func(
        token="not-a-real-token",
        sender_id="owner-1",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "error"


def test_confirm_rejects_cross_sender_token(sqlite_db):
    from xninetzy.os.career.orchestrator import ApplicationOrchestrator

    orch = ApplicationOrchestrator()
    orch.request_status_change(
        posting_id="remoteok-3",
        sender_id="owner-A",
        target_status="applied",
    )
    from xninetzy.db.sqlite import connect

    with connect() as conn:
        row = conn.execute(
            "SELECT token FROM career_confirmation_tokens WHERE application_key=?",
            ("owner-A::remoteok-3",),
        ).fetchone()
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_confirm_application,
    )

    raw = career_confirm_application.func(
        token=row["token"],
        sender_id="owner-B",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "error"


def test_confirm_rejects_expired_token(sqlite_db):
    from xninetzy.os.career.orchestrator import ApplicationOrchestrator

    now = datetime.now(timezone.utc)
    past = now - timedelta(seconds=600)
    orch = ApplicationOrchestrator()
    issued = orch._tokens.issue(
        application_key="owner-old::x",
        posting_id="x",
        sender_id="owner-old",
        target_status="applied",
        now=past,
        ttl_seconds=60,
    )
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_confirm_application,
    )

    raw = career_confirm_application.func(
        token=issued.token,
        sender_id="owner-old",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "error"


def test_confirm_rejects_already_consumed_token(sqlite_db):
    from xninetzy.os.career.orchestrator import ApplicationOrchestrator

    orch = ApplicationOrchestrator()
    issued = orch._tokens.issue(
        application_key="owner-d::x",
        posting_id="x",
        sender_id="owner-d",
        target_status="applied",
    )
    orch._tokens.consume(token=issued.token, sender_id="owner-d")
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_confirm_application,
    )

    raw = career_confirm_application.func(
        token=issued.token,
        sender_id="owner-d",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "error"


def test_request_change_rejects_invalid_status(sqlite_db):
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_request_application_change,
    )

    raw = career_request_application_change.func(
        posting_id="x",
        target_status="invalid",
        sender_id="owner-1",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "error"


def test_issuing_new_token_for_same_app_status_invalidates_old_one(sqlite_db):
    from xninetzy.os.career.orchestrator import ApplicationOrchestrator

    orch = ApplicationOrchestrator()
    first = orch._tokens.issue(
        application_key="owner-r::x",
        posting_id="x",
        sender_id="owner-r",
        target_status="applied",
    )
    orch._tokens.issue(
        application_key="owner-r::x",
        posting_id="x",
        sender_id="owner-r",
        target_status="applied",
    )
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_confirm_application,
    )

    raw = career_confirm_application.func(
        token=first.token,
        sender_id="owner-r",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "error"


def test_record_outcome_updates_source_quality(sqlite_db):
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_record_application_outcome,
    )

    raw = career_record_application_outcome.func(
        posting_id="remoteok-q",
        source="remoteok",
        outcome="interview",
        sender_id="owner-q",
        reason="got call",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "ok"
    assert payload["source_quality"]["interviews_total"] == 1
    assert payload["source_quality"]["outcomes_total"] == 1
    assert payload["source_quality"]["quality_score"] > 0.5


def test_record_outcome_rejects_invalid_outcome(sqlite_db):
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_record_application_outcome,
    )

    raw = career_record_application_outcome.func(
        posting_id="x",
        source="remoteok",
        outcome="bogus",
        sender_id="owner-1",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "error"


def test_record_outcome_quality_penalizes_rejects(sqlite_db):
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_record_application_outcome,
    )

    for _ in range(5):
        career_record_application_outcome.func(
            posting_id="remoteok-x",
            source="remoteok",
            outcome="reject",
            sender_id="owner-x",
            plan_id="",
            step_id="",
            chat_id="system",
            idempotency_key="",
        )
    raw = career_record_application_outcome.func(
        posting_id="remoteok-x",
        source="remoteok",
        outcome="reject",
        sender_id="owner-x",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["source_quality"]["quality_score"] < 0.4
