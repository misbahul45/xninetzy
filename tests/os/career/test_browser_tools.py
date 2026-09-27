from __future__ import annotations

import json

import pytest


@pytest.fixture
def sqlite_db(monkeypatch, tmp_path):
    from xninetzy.core.config import get_settings

    db = tmp_path / "browser_mcp.sqlite3"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    get_settings.cache_clear()
    from xninetzy.db.migrations import run_migrations
    from xninetzy.db.sqlite import init_db

    init_db()
    run_migrations()
    from xninetzy.tools.ecosystem import career_browser_tools

    career_browser_tools._STORE.__init__()
    yield db
    career_browser_tools._STORE.__init__()
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


def test_career_open_application_creates_session_and_returns_form(sqlite_db):
    from xninetzy.tools.ecosystem.career_browser_tools import (
        career_open_application,
    )

    payload = _call(
        career_open_application,
        posting_id="remoteok-99",
        posting_url="https://example.com/apply/99",
    )
    assert payload["status_flag"] == "ok"
    assert payload["submission_not_performed"] is True
    assert payload["session"]["state"] == "open"
    assert payload["session"]["application_key"] == "owner-1::remoteok-99"
    assert "safe_count" in payload["form"]
    assert "blocked_count" in payload["form"]


def test_career_open_application_rejects_non_http_url(sqlite_db):
    from xninetzy.tools.ecosystem.career_browser_tools import (
        career_open_application,
    )

    payload = _call(
        career_open_application,
        posting_id="x",
        posting_url="javascript:alert(1)",
    )
    assert payload["status_flag"] == "error"


def test_career_open_application_refuses_duplicate_session(sqlite_db):
    from xninetzy.tools.ecosystem.career_browser_tools import (
        career_open_application,
    )

    _call(
        career_open_application,
        posting_id="remoteok-dup",
        posting_url="https://example.com/apply/dup",
    )
    second = _call(
        career_open_application,
        posting_id="remoteok-dup",
        posting_url="https://example.com/apply/dup",
    )
    assert second["status_flag"] == "error"


def test_career_open_application_returns_neutral_summary_with_no_credentials(sqlite_db):
    from xninetzy.tools.ecosystem.career_browser_tools import (
        career_open_application,
    )

    payload = _call(
        career_open_application,
        posting_id="x",
        posting_url="https://example.com/x",
    )
    raw = json.dumps(payload)
    for forbidden in ("cookie", "session_id_token", "bearer", "password", "secret"):
        assert forbidden not in raw.lower()


def test_career_fill_application_blocks_unsafe_fields(sqlite_db, monkeypatch):
    from xninetzy.tools.ecosystem import career_browser_tools
    from xninetzy.os.career.browser_session import FakeFormPage

    fake = FakeFormPage(
        _url="https://example.com/apply",
        _title="Apply",
        _html="""
        <form>
          <input name="full_name" type="text">
          <input name="email" type="email">
          <input name="password" type="password">
          <input type="submit" name="submit">
        </form>
        """,
    )
    open_payload = _call(
        career_browser_tools.career_open_application,
        posting_id="remoteok-fill",
        posting_url="https://example.com/apply",
    )
    session_id = open_payload["session"]["session_id"]
    career_browser_tools._STORE.attach_page(session_id, fake)
    fill_payload = _call(
        career_browser_tools.career_fill_application,
        session_id=session_id,
        fields_json=json.dumps(
            {
                "full_name": "Misbahul Muttaqin",
                "email": "user@example.com",
                "password": "secret123",
            }
        ),
    )
    assert fill_payload["status_flag"] == "ok"
    assert fill_payload["submission_not_performed"] is True
    filled_names = [f["name"] for f in fill_payload["summary"]["filled"]]
    skipped_names = [s["name"] for s in fill_payload["summary"]["skipped"]]
    assert "full_name" in filled_names
    assert "email" in filled_names
    assert "password" in skipped_names
    assert len(fake.filled) == 2
    assert fake.submitted is False


def test_career_fill_application_refuses_invalid_json(sqlite_db):
    from xninetzy.tools.ecosystem import career_browser_tools

    open_payload = _call(
        career_browser_tools.career_open_application,
        posting_id="x",
        posting_url="https://example.com/x",
    )
    session_id = open_payload["session"]["session_id"]
    fill_payload = _call(
        career_browser_tools.career_fill_application,
        session_id=session_id,
        fields_json="not-json",
    )
    assert fill_payload["status_flag"] == "error"


def test_career_fill_application_refuses_cross_sender(sqlite_db):
    from xninetzy.tools.ecosystem import career_browser_tools

    open_payload = _call(
        career_browser_tools.career_open_application,
        posting_id="x",
        posting_url="https://example.com/x",
        sender_id="owner-A",
    )
    session_id = open_payload["session"]["session_id"]
    fill_payload = _call(
        career_browser_tools.career_fill_application,
        session_id=session_id,
        fields_json="{}",
        sender_id="owner-B",
    )
    assert fill_payload["status_flag"] == "error"


def test_career_inspect_application_returns_form_for_open_session(sqlite_db):
    from xninetzy.tools.ecosystem import career_browser_tools
    from xninetzy.os.career.browser_session import FakeFormPage

    open_payload = _call(
        career_browser_tools.career_open_application,
        posting_id="x",
        posting_url="https://example.com/x",
    )
    session_id = open_payload["session"]["session_id"]
    career_browser_tools._STORE.attach_page(
        session_id,
        FakeFormPage(
            _url="https://example.com/x",
            _title="Apply Now",
            _html='<html><head><title>Apply Now</title></head><body><form><input name="full_name" type="text"></form></body></html>',
        ),
    )
    inspect_payload = _call(
        career_browser_tools.career_inspect_application,
        session_id=session_id,
    )
    assert inspect_payload["status_flag"] == "ok"
    assert inspect_payload["form"]["title"] == "Apply Now"


def test_career_inspect_application_returns_not_found_for_unknown_session(sqlite_db):
    from xninetzy.tools.ecosystem import career_browser_tools

    payload = _call(
        career_browser_tools.career_inspect_application,
        session_id="does-not-exist",
    )
    assert payload["status_flag"] == "not_found"


def test_career_close_application_marks_state_closed(sqlite_db):
    from xninetzy.tools.ecosystem import career_browser_tools

    open_payload = _call(
        career_browser_tools.career_open_application,
        posting_id="x",
        posting_url="https://example.com/x",
    )
    session_id = open_payload["session"]["session_id"]
    close_payload = _call(
        career_browser_tools.career_close_application,
        session_id=session_id,
    )
    assert close_payload["status_flag"] == "closed"
    fill_payload = _call(
        career_browser_tools.career_fill_application,
        session_id=session_id,
        fields_json="{}",
    )
    assert fill_payload["status_flag"] == "closed"


def test_career_close_application_refuses_cross_sender(sqlite_db):
    from xninetzy.tools.ecosystem import career_browser_tools

    open_payload = _call(
        career_browser_tools.career_open_application,
        posting_id="x",
        posting_url="https://example.com/x",
        sender_id="owner-A",
    )
    session_id = open_payload["session"]["session_id"]
    close_payload = _call(
        career_browser_tools.career_close_application,
        session_id=session_id,
        sender_id="owner-B",
    )
    assert close_payload["status_flag"] == "error"


def test_full_open_inspect_fill_close_flow(sqlite_db):
    from xninetzy.tools.ecosystem import career_browser_tools
    from xninetzy.os.career.browser_session import FakeFormPage

    open_payload = _call(
        career_browser_tools.career_open_application,
        posting_id="end-to-end",
        posting_url="https://example.com/end-to-end",
    )
    session_id = open_payload["session"]["session_id"]
    career_browser_tools._STORE.attach_page(
        session_id,
        FakeFormPage(
            _url="https://example.com/end-to-end",
            _title="Apply",
            _html="""
            <form>
              <input name="full_name" type="text">
              <input name="email" type="email">
              <input name="phone" type="tel">
              <textarea name="cover_letter"></textarea>
              <input name="password" type="password">
              <input type="submit" name="submit">
            </form>
            """,
        ),
    )
    inspect_payload = _call(
        career_browser_tools.career_inspect_application,
        session_id=session_id,
    )
    assert inspect_payload["form"]["safe_count"] == 4
    assert inspect_payload["form"]["blocked_count"] == 2
    fill_payload = _call(
        career_browser_tools.career_fill_application,
        session_id=session_id,
        fields_json=json.dumps(
            {
                "full_name": "Misbahul Muttaqin",
                "email": "user@example.com",
                "phone": "+62 856-4920-4151",
                "cover_letter": "Hi, I'm interested...",
                "password": "secret",
            }
        ),
    )
    assert len(fill_payload["summary"]["filled"]) == 4
    assert len(fill_payload["summary"]["skipped"]) == 1
    assert fill_payload["summary"]["skipped"][0]["name"] == "password"
    close_payload = _call(
        career_browser_tools.career_close_application,
        session_id=session_id,
    )
    assert close_payload["status_flag"] == "closed"
