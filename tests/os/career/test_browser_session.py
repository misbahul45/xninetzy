from __future__ import annotations

import pytest


@pytest.fixture
def sqlite_db(monkeypatch, tmp_path):
    from xninetzy.core.config import get_settings

    db = tmp_path / "browser.sqlite3"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    get_settings.cache_clear()
    from xninetzy.db.migrations import run_migrations
    from xninetzy.db.sqlite import init_db

    init_db()
    run_migrations()
    yield db
    get_settings.cache_clear()


def test_parse_form_extracts_input_fields():
    from xninetzy.os.career.browser_session import parse_form

    html = """
    <html><head><title>Apply Now</title></head><body>
      <form>
        <label for="full_name">Full Name</label>
        <input id="full_name" name="full_name" type="text" required>
        <input name="email" type="email">
        <textarea name="cover_letter"></textarea>
        <input name="resume" type="file">
        <input type="submit" name="submit">
      </form>
    </body></html>
    """
    title, fields = parse_form(html)
    assert title == "Apply Now"
    by_name = {f.name: f for f in fields}
    assert by_name["full_name"].safe_to_fill is True
    assert by_name["full_name"].required is True
    assert by_name["full_name"].label == "Full Name"
    assert by_name["email"].safe_to_fill is True
    assert by_name["cover_letter"].safe_to_fill is True
    assert by_name["resume"].safe_to_fill is False
    assert by_name["submit"].safe_to_fill is False


def test_parse_form_returns_empty_for_no_form():
    from xninetzy.os.career.browser_session import parse_form

    title, fields = parse_form("<html><body>No form here</body></html>")
    assert title == ""
    assert fields == []


def test_inspect_page_returns_safe_summary():
    from xninetzy.os.career.browser_session import FakeFormPage, inspect_page

    page = FakeFormPage(
        _url="https://kalibrr.com/c/jobs/123",
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
    result = inspect_page(page)
    assert result.url == "https://kalibrr.com/c/jobs/123"
    assert result.safe_count == 2
    assert result.blocked_count == 2
    safe_dict = result.to_safe_dict()
    assert "url" in safe_dict
    assert "fields" in safe_dict
    for f in safe_dict["fields"]:
        assert "current_value" in f
        assert f["current_value"] == ""


def test_fill_safe_fields_only_fills_safe_fields():
    from xninetzy.os.career.browser_session import FakeFormPage, fill_safe_fields

    page = FakeFormPage(
        _url="https://example.com/apply",
        _title="Apply",
        _html="""
        <form>
          <input name="full_name" type="text">
          <input name="email" type="email">
          <input name="password" type="password">
        </form>
        """,
    )
    result = fill_safe_fields(
        page,
        {
            "full_name": "Misbahul Muttaqin",
            "email": "user@example.com",
            "password": "secret123",
        },
    )
    filled_names = [f["name"] for f in result.filled]
    skipped_names = [s["name"] for s in result.skipped]
    assert "full_name" in filled_names
    assert "email" in filled_names
    assert "password" in skipped_names
    assert len(page.filled) == 2


def test_fill_safe_fields_never_submits():
    from xninetzy.os.career.browser_session import FakeFormPage, fill_safe_fields

    page = FakeFormPage(
        _url="https://example.com/apply",
        _title="Apply",
        _html='<form><input name="full_name" type="text"></form>',
    )
    fill_safe_fields(page, {"full_name": "Misbahul Muttaqin"})
    assert page.submitted is False


def test_fill_safe_fields_records_skip_reasons():
    from xninetzy.os.career.browser_session import FakeFormPage, fill_safe_fields

    page = FakeFormPage(
        _url="https://example.com/apply",
        _title="Apply",
        _html='<form><input name="password" type="password"></form>',
    )
    result = fill_safe_fields(page, {"password": "secret"})
    assert result.skipped[0]["reason"]


def test_session_store_open_and_close_lifecycle(sqlite_db):
    from xninetzy.os.career.browser_session import ApplicationSessionStore

    store = ApplicationSessionStore()
    record = store.open(
        application_key="owner-1::x",
        posting_id="x",
        sender_id="owner-1",
        posting_url="https://example.com/apply",
    )
    assert record.state == "open"
    assert store.get(record.session_id) is not None
    assert store.get_for("owner-1::x") == record
    assert store.close(record.session_id) is True
    assert store.get(record.session_id).state == "closed"


def test_session_store_refuses_duplicate_open_for_same_application(sqlite_db):
    from xninetzy.os.career.browser_session import ApplicationSessionStore

    store = ApplicationSessionStore()
    store.open(
        application_key="owner-1::x",
        posting_id="x",
        sender_id="owner-1",
        posting_url="https://example.com/apply",
    )
    import pytest

    with pytest.raises(ValueError):
        store.open(
            application_key="owner-1::x",
            posting_id="x",
            sender_id="owner-1",
            posting_url="https://example.com/apply",
        )


def test_session_store_attach_page_round_trip(sqlite_db):
    from xninetzy.os.career.browser_session import (
        ApplicationSessionStore,
        FakeFormPage,
    )

    store = ApplicationSessionStore()
    record = store.open(
        application_key="owner-2::y",
        posting_id="y",
        sender_id="owner-2",
        posting_url="https://example.com/y",
    )
    page = FakeFormPage(_url="https://example.com/y", _title="Apply", _html="")
    store.attach_page(record.session_id, page)
    assert store.get_page(record.session_id) is page


def test_session_store_safe_dict_excludes_cookies_and_tokens(sqlite_db):
    from xninetzy.os.career.browser_session import ApplicationSessionStore

    store = ApplicationSessionStore()
    record = store.open(
        application_key="owner-3::z",
        posting_id="z",
        sender_id="owner-3",
        posting_url="https://example.com/z",
    )
    safe = record.to_safe_dict()
    for key in safe:
        assert "cookie" not in key.lower()
        assert "token" not in key.lower()
        assert "password" not in key.lower()
        assert "secret" not in key.lower()
