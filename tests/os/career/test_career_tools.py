from __future__ import annotations

import json

import pytest

from xninetzy.core.config import get_settings
from xninetzy.db.migrations import run_migrations
from xninetzy.db.sqlite import init_db
from xninetzy.tools.ecosystem.career_tools import career_tools
from xninetzy.tools.registry import get_tool_groups


EXPECTED = {
    "career_search_jobs",
    "career_search_internships",
    "career_skill_gap",
    "career_market_skill_trend",
    "career_resume_tailor",
    "career_search_companies",
    "career_get_job",
    "career_extract_requirements",
    "career_company_research",
    "career_salary_analysis",
    "career_find_similar_jobs",
    "career_find_alternative_titles",
    "career_find_hidden_jobs",
    "career_monitor",
    "career_track_application",
    "career_list_applications",
    "career_get_application",
    "career_interview_prep",
    "career_resume_analysis",
}


def test_career_tools_list_complete() -> None:
    names = {t.name for t in career_tools}
    missing = EXPECTED - names
    assert not missing, f"missing from career_tools: {missing}"


def test_career_tool_group_complete() -> None:
    groups = get_tool_groups()
    career_group = set(groups.get("career", []))
    missing = EXPECTED - career_group
    assert not missing, f"missing from career group: {missing}"


def test_career_alternative_titles_expand() -> None:
    from xninetzy.tools.ecosystem.career_tools import _expand_title

    expansions = _expand_title("backend")
    assert "backend" in expansions
    assert any("backend engineer" in term for term in expansions)


def test_career_requirement_keywords() -> None:
    from xninetzy.tools.ecosystem.career_tools import _extract_requirements

    snippet = "We require 5 years of Python experience, knowledge of FastAPI, and Docker."
    keywords = _extract_requirements(snippet)
    assert "python" in keywords
    assert "docker" in keywords
    assert "experience" in keywords


def test_career_salary_parse() -> None:
    from xninetzy.tools.ecosystem.career_tools import _parse_salary

    parsed = _parse_salary("Salary: USD 120k")
    assert parsed is not None
    currency, _rate, amount = parsed
    assert currency == "usd"
    assert amount >= 1000


def test_career_salary_parse_no_match() -> None:
    from xninetzy.tools.ecosystem.career_tools import _parse_salary

    assert _parse_salary("competitive salary") is None


@pytest.fixture
def sqlite_db(monkeypatch, tmp_path):
    db_path = tmp_path / "career.sqlite3"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    init_db()
    run_migrations()
    yield db_path
    get_settings.cache_clear()


def _call_track(posting_id: str, status: str, sender_id: str = "owner-1", notes: str = "") -> dict:
    from xninetzy.tools.ecosystem.career_tools import career_track_application

    raw = career_track_application.func(
        posting_id=posting_id,
        status=status,
        notes=notes,
        sender_id=sender_id,
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    envelope = json.loads(raw)
    return json.loads(envelope["summary"])


def _call_list(sender_id: str = "", limit: int = 20) -> dict:
    from xninetzy.tools.ecosystem.career_tools import career_list_applications

    raw = career_list_applications.func(
        sender_id=sender_id,
        limit=limit,
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    envelope = json.loads(raw)
    return json.loads(envelope["summary"])


def _call_get(posting_id: str, sender_id: str = "") -> dict:
    from xninetzy.tools.ecosystem.career_tools import career_get_application

    raw = career_get_application.func(
        posting_id=posting_id,
        sender_id=sender_id,
        plan_id="",
        step_id="",
        chat_id="system",
        idempotency_key="",
    )
    envelope = json.loads(raw)
    return json.loads(envelope["summary"])


def test_career_track_application_persists_row(sqlite_db):
    from xninetzy.db.sqlite import connect

    payload = _call_track("remoteok-123", "applied", notes="via referral")
    assert payload["status_flag"] == "ok"
    assert payload["application"]["status"] == "applied"
    assert payload["application"]["posting_id"] == "remoteok-123"

    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM career_applications WHERE application_key=?",
            ("owner-1::remoteok-123",),
        ).fetchone()
    assert row is not None, "career_track_application must persist a row"
    assert row["status"] == "applied"
    assert row["sender_id"] == "owner-1"
    assert row["posting_id"] == "remoteok-123"
    assert row["notes"] == "via referral"
    history = json.loads(row["history_json"] or "[]")
    assert len(history) == 1
    assert history[0]["status"] == "applied"


def test_career_track_application_is_idempotent_per_sender_posting(sqlite_db):
    from xninetzy.db.sqlite import connect

    _call_track("remoteok-456", "drafted", sender_id="owner-2")
    _call_track("remoteok-456", "applied", sender_id="owner-2")
    _call_track("remoteok-456", "interviewed", sender_id="owner-2")

    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM career_applications WHERE sender_id=? AND posting_id=?",
            ("owner-2", "remoteok-456"),
        ).fetchall()
    assert len(rows) == 1, "must collapse to one row per (sender, posting)"
    assert rows[0]["status"] == "interviewed"
    history = json.loads(rows[0]["history_json"] or "[]")
    assert [h["status"] for h in history] == ["drafted", "applied", "interviewed"]


def test_career_track_application_rejects_invalid_status(sqlite_db):
    payload = _call_track("remoteok-789", "bogus")
    assert payload["status_flag"] == "error"
    assert "invalid status" in payload["error"]


def test_career_list_applications_returns_owner_history(sqlite_db):
    _call_track("remoteok-aaa", "drafted", sender_id="owner-3")
    _call_track("remoteok-bbb", "applied", sender_id="owner-3")
    _call_track("remoteok-ccc", "drafted", sender_id="owner-4")

    payload = _call_list(sender_id="owner-3", limit=10)
    assert payload["status_flag"] == "ok"
    posting_ids = sorted(item["posting_id"] for item in payload["applications"])
    assert posting_ids == ["remoteok-aaa", "remoteok-bbb"]


def test_career_get_application_returns_single_record(sqlite_db):
    _call_track("remoteok-zzz", "applied", sender_id="owner-5", notes="first call")
    _call_track("remoteok-zzz", "interviewed", sender_id="owner-5", notes="second call")

    payload = _call_get("remoteok-zzz", sender_id="owner-5")
    assert payload["status_flag"] == "ok"
    assert payload["application"]["posting_id"] == "remoteok-zzz"
    assert payload["application"]["status"] == "interviewed"
    assert len(payload["application"]["history"]) == 2
    assert payload["application"]["history"][-1]["status"] == "interviewed"
