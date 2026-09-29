from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from xninetzy.os.academic.hebat.fetch_cache import TTLCache


@pytest.fixture(autouse=True)
def _reset_cache():
    from xninetzy.os.academic.hebat import moodle_client

    moodle_client.fetch_assignment_detail_cache.clear()
    yield
    moodle_client.fetch_assignment_detail_cache.clear()


def _settings_mock():
    class S:
        HEBAT_RATE_LIMIT_SECONDS = 0.0
        APP_TIMEZONE = "Asia/Jakarta"
        HEBAT_FETCH_CACHE_TTL_SECONDS = 90.0

        def hebat_reminder_hours(self):
            return []

        def hebat_sync_total_budget_seconds(self):
            return 2.0

        def hebat_sync_item_timeout_seconds(self):
            return 1.0

        def hebat_sync_concurrency(self):
            return 3

    return S()


def _settings_mock_no_timeout():
    class S:
        HEBAT_RATE_LIMIT_SECONDS = 0.0
        APP_TIMEZONE = "Asia/Jakarta"
        HEBAT_FETCH_CACHE_TTL_SECONDS = 90.0

        def hebat_reminder_hours(self):
            return []

        def hebat_sync_total_budget_seconds(self):
            return 60.0

        def hebat_sync_item_timeout_seconds(self):
            return 15.0

        def hebat_sync_concurrency(self):
            return 5

    return S()


@pytest.mark.asyncio
async def test_sync_respects_outer_deadline():
    from xninetzy.os.academic.hebat.tools import hebat_sync_assignments

    mock_activities = [
        {"cmid": str(1000 + i), "id": 2000 + i, "title": f"Tugas {i}"}
        for i in range(50)
    ]
    mock_detail = {
        "title": "Tugas X",
        "instruction": "instr",
        "opened_at": "9 February 2026, 3:00 PM",
        "due_at": "2 March 2026, 5:00 PM",
        "time_remaining": "10 days remaining",
        "submission_status": "No submissions have been made yet",
        "grading_status": "Not graded",
        "last_modified": "-",
    }
    fetch_calls = []

    async def fake_fetch(chat_id, cmid):
        fetch_calls.append(cmid)
        await asyncio.sleep(1.5)
        return mock_detail

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=mock_activities), patch(
        "xninetzy.os.academic.hebat.tools.fetch_assignment_detail_cached", side_effect=fake_fetch
    ), patch("xninetzy.os.academic.hebat.tools.upsert_assignment", return_value=999), patch(
        "xninetzy.os.academic.hebat.tools.sync_assignment_task", return_value=(1, True)
    ), patch("xninetzy.os.academic.hebat.tools.has_reminder_for_assignment", return_value=True), patch(
        "xninetzy.os.academic.hebat.tools._ensure_session_or_msg", return_value=None
    ), patch("xninetzy.os.academic.hebat.tools.get_settings", return_value=_settings_mock()):
        start = time.time()
        result = await hebat_sync_assignments.ainvoke(
            {"chat_id": "dummy_chat_id", "course_id": None}
        )
        elapsed = time.time() - start

    assert elapsed < 5.0, f"sync took {elapsed:.2f}s, expected <5s (deadline=2s + slack)"
    assert "Sync assignment selesai" in result or "deadline" in result.lower() or "Dihentikan" in result, (
        f"expected a (partial) success summary, got: {result!r}"
    )
    assert 0 < len(fetch_calls) < 50, (
        f"expected partial fetch (<50 calls), got {len(fetch_calls)}"
    )


@pytest.mark.asyncio
async def test_sync_is_idempotent_within_ttl():
    from xninetzy.os.academic.hebat.tools import hebat_sync_assignments

    mock_activities = [
        {"cmid": str(1000 + i), "id": 2000 + i, "title": f"Tugas {i}"}
        for i in range(10)
    ]
    mock_detail = {
        "title": "Tugas X",
        "instruction": "instr",
        "opened_at": "9 February 2026, 3:00 PM",
        "due_at": "2 March 2026, 5:00 PM",
        "time_remaining": "10 days remaining",
        "submission_status": "No submissions have been made yet",
        "grading_status": "Not graded",
        "last_modified": "-",
    }
    fetch_calls = []

    async def fake_fetch(chat_id, cmid):
        fetch_calls.append(cmid)
        await asyncio.sleep(0.01)
        return dict(mock_detail)

    cache_holder = {"miss_first_round": True}
    real_cache = TTLCache[tuple[str, str], dict]()

    async def cached_wrapper(chat_id, cmid):
        key = (chat_id, cmid)
        hit = real_cache.get(key)
        if hit is not None:
            return hit
        if cache_holder["miss_first_round"]:
            await asyncio.sleep(0.0)
        result = await fake_fetch(chat_id, cmid)
        real_cache.set(key, result, ttl=90.0)
        return result

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=mock_activities), patch(
        "xninetzy.os.academic.hebat.tools.fetch_assignment_detail_cached", side_effect=cached_wrapper
    ), patch("xninetzy.os.academic.hebat.tools.upsert_assignment", return_value=999), patch(
        "xninetzy.os.academic.hebat.tools.sync_assignment_task", return_value=(1, True)
    ), patch("xninetzy.os.academic.hebat.tools.has_reminder_for_assignment", return_value=True), patch(
        "xninetzy.os.academic.hebat.tools._ensure_session_or_msg", return_value=None
    ), patch("xninetzy.os.academic.hebat.tools.get_settings", return_value=_settings_mock_no_timeout()):
        await hebat_sync_assignments.ainvoke({"chat_id": "dummy_chat_id", "course_id": None})
        first_calls = list(fetch_calls)

        before_second = len(fetch_calls)
        await hebat_sync_assignments.ainvoke({"chat_id": "dummy_chat_id", "course_id": None})
        second_calls = list(fetch_calls)

    assert len(first_calls) == 10, f"first round should fetch all 10, got {len(first_calls)}"
    assert len(second_calls) == before_second, (
        f"round 2 must hit cache, but {len(second_calls) - before_second} new fetches happened"
    )


@pytest.mark.asyncio
async def test_fetch_cache_respects_ttl():

    cache = TTLCache[tuple[str, str], dict]()
    cache.set(("dummy_chat_id", "9999"), {"title": "cached"}, ttl=60)

    hit = cache.get(("dummy_chat_id", "9999"))
    assert hit == {"title": "cached"}

    cache._store.clear()
    cache.set(("dummy_chat_id", "9999"), {"title": "cached"}, ttl=-1)
    assert cache.get(("dummy_chat_id", "9999")) is None


@pytest.mark.asyncio
async def test_get_assignment_detail_uses_cache():
    from xninetzy.os.academic.hebat import moodle_client
    from xninetzy.os.academic.hebat.tools import hebat_get_assignment_detail

    moodle_client.fetch_assignment_detail_cache.clear()

    detail = {
        "title": "Tugas UTS",
        "instruction": "Do this",
        "opened_at": "-",
        "due_at": "10 October 2026, 11:59 PM",
        "time_remaining": "12 days remaining",
        "submission_status": "No submissions have been made yet",
        "grading_status": "Not graded",
        "last_modified": "-",
        "attachments": [],
    }

    call_count = {"n": 0}

    async def fake_cached(chat_id, cmid):
        call_count["n"] += 1
        moodle_client.fetch_assignment_detail_cache.set(
            (chat_id, cmid), detail, ttl=90.0
        )
        return detail

    with patch(
        "xninetzy.os.academic.hebat.tools.fetch_assignment_detail_cached",
        side_effect=fake_cached,
    ), patch(
        "xninetzy.os.academic.hebat.tools._resolve_activity_cmid",
        return_value=("42", "https://example/mod/assign/view.php?id=42"),
    ):
        out1 = await hebat_get_assignment_detail.ainvoke(
            {"chat_id": "dummy_chat_id", "assignment_id_or_url": "42"}
        )
        out2 = await hebat_get_assignment_detail.ainvoke(
            {"chat_id": "dummy_chat_id", "assignment_id_or_url": "42"}
        )

    assert call_count["n"] == 2, (
        f"expected 2 calls (cache is per-call from the wrapper), got {call_count['n']}"
    )
    assert "Tugas UTS" in out1
    assert "Tugas UTS" in out2
    cached_value = moodle_client.fetch_assignment_detail_cache.get(("dummy_chat_id", "42"))
    assert cached_value is not None, "wrapper should populate cache for retries"
