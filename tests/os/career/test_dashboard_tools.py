from __future__ import annotations

import json

import pytest


@pytest.fixture
def sqlite_db(monkeypatch, tmp_path):
    from xninetzy.core.config import get_settings

    db = tmp_path / "dashboard.sqlite3"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    get_settings.cache_clear()
    from xninetzy.db.migrations import run_migrations
    from xninetzy.db.sqlite import init_db

    init_db()
    run_migrations()
    yield db
    get_settings.cache_clear()


def _call(func, **kwargs):
    raw = func.func(
        plan_id="",
        step_id="",
        chat_id="system",
        sender_id=kwargs.pop("sender_id", "owner-1"),
        idempotency_key="",
        **kwargs,
    )
    return json.loads(json.loads(raw)["summary"])


def test_career_observability_dashboard_returns_snapshot(sqlite_db):
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_observability_dashboard,
    )

    payload = _call(career_observability_dashboard)
    assert payload["status_flag"] == "ok"
    assert "snapshot_at" in payload
    assert "adapters" in payload
    assert "search_cache" in payload
    assert "source_quality" in payload
    assert "outcomes" in payload
    assert "application_state_distribution" in payload
    assert "browser_sessions" in payload
    assert "active_confirmation_tokens" in payload
    assert "observability" in payload


def test_dashboard_search_cache_section_includes_keys(sqlite_db):
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_observability_dashboard,
    )
    from xninetzy.os.career.dashboard import cache as dashboard_cache_factory

    dashboard_cache = dashboard_cache_factory()
    dashboard_cache.put(key="a", adapter_id="remoteok", value={"v": 1})
    dashboard_cache.put(key="b", adapter_id="kalibrr", value={"v": 2})
    payload = _call(career_observability_dashboard)
    assert payload["search_cache"]["size"] == 2
    assert payload["search_cache"]["by_adapter"]["remoteok"]["count"] == 1
    assert payload["search_cache"]["by_adapter"]["kalibrr"]["count"] == 1


def test_dashboard_reports_empty_source_quality_when_no_outcomes(sqlite_db):
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_observability_dashboard,
    )

    payload = _call(career_observability_dashboard)
    assert payload["source_quality"] == []


def test_dashboard_includes_compliance_drift_when_unacknowledged(sqlite_db):
    from xninetzy.os.career.compliance import ComplianceClass, declare
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_observability_dashboard,
    )

    declare(
        "fixture_drift_source",
        tos_url="https://x/tos",
        declared_class=ComplianceClass.READ,
        risk_acknowledged=False,
    )
    payload = _call(career_observability_dashboard)
    assert payload["adapters"]["compliance"]["status"] == "drift"


def test_dashboard_observation_counts_is_dict(sqlite_db):
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_observability_dashboard,
    )

    payload = _call(career_observability_dashboard)
    assert isinstance(payload["observability"], dict)


def test_recovery_list_returns_apps_stuck_past_threshold(sqlite_db):
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_recover_stuck_applications,
    )

    report = _call(
        career_recover_stuck_applications,
        stuck_after_days=7,
        mark_as="report",
    )
    assert report["status_flag"] == "ok"
    assert report["stuck_count"] == 0
    assert report["marked_as"] == "report"
    assert report["owner_action_performed"] is False


def test_recovery_requires_sender_for_mutation(sqlite_db):
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_recover_stuck_applications,
    )

    report = _call(
        career_recover_stuck_applications,
        stuck_after_days=7,
        mark_as="withdrawn",
        sender_id="",
    )
    assert report["status_flag"] == "error"


def test_recovery_rejects_invalid_mark_as(sqlite_db):
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_recover_stuck_applications,
    )

    report = _call(
        career_recover_stuck_applications,
        stuck_after_days=7,
        mark_as="bogus",
        sender_id="owner-1",
    )
    assert report["status_flag"] == "error"


def test_recovery_marks_stuck_apps_as_withdrawn(sqlite_db):
    from xninetzy.tools.ecosystem.career_dashboard_tools import (
        career_recover_stuck_applications,
    )
    from xninetzy.tools.ecosystem.career_orchestrator_tools import (
        career_confirm_application,
        career_request_application_change,
    )
    from xninetzy.core.config import get_settings
    from xninetzy.db.sqlite import connect
    from datetime import datetime, timedelta, timezone

    get_settings.cache_clear()

    raw = career_request_application_change.func(
        posting_id="stuck-1",
        target_status="applied",
        sender_id="owner-1",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status_flag"] == "awaiting_confirmation"
    with connect() as conn:
        token_row = conn.execute(
            "SELECT token FROM career_confirmation_tokens WHERE application_key=?",
            ("owner-1::stuck-1",),
        ).fetchone()
    career_confirm_application.func(
        token=token_row["token"],
        sender_id="owner-1",
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    past = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    with connect() as conn:
        conn.execute(
            "UPDATE career_applications SET updated_at=? WHERE application_key=?",
            (past, "owner-1::stuck-1"),
        )
    report = _call(
        career_recover_stuck_applications,
        stuck_after_days=7,
        mark_as="withdrawn",
        sender_id="owner-1",
    )
    assert report["status_flag"] == "ok"
    assert report["owner_action_performed"] is True
    assert len(report["acknowledged"]) == 1
    assert report["acknowledged"][0]["new_status"] == "withdrawn"
