from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


SAMPLE_ACTIVITY = {
    "course_id": "10974",
    "cmid": "1001",
    "type": "assign",
    "title": "Tugas 1",
    "section_title": "Pertemuan 1",
    "activity_url": "https://hebat.unair.ac.id/mod/assign/view.php?id=1001",
}


def _row(course_id: str, cmid: str, type_: str, title: str, section: str = "General") -> dict:
    return {
        "course_id": course_id,
        "cmid": cmid,
        "type": type_,
        "title": title,
        "section_title": section,
        "activity_url": f"https://hebat.unair.ac.id/mod/{type_}/view.php?id={cmid}",
    }


def test_returns_helpful_message_when_cache_entirely_empty():
    from xninetzy.os.academic.hebat.tools import hebat_list_course_activities

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=[]) as mock_list:
        result = hebat_list_course_activities.invoke({})

    mock_list.assert_called_once_with(None, None)
    assert "Belum ada activity" in result
    assert "sync_course_activities" in result


def test_returns_single_course_list_when_course_id_filtered():
    from xninetzy.os.academic.hebat.tools import hebat_list_course_activities

    rows = [
        _row("10974", "1001", "assign", "Tugas 1", "Pertemuan 1"),
        _row("10974", "1002", "assign", "Tugas 2", "Pertemuan 2"),
    ]

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=rows):
        result = hebat_list_course_activities.invoke({"course_id": "10974"})

    assert "Tugas 1" in result
    assert "Tugas 2" in result
    assert "10974" in result


def test_groups_by_course_when_no_course_id_filter():
    from xninetzy.os.academic.hebat.tools import hebat_list_course_activities

    rows = [
        _row("10974", "1001", "assign", "SII209 Task"),
        _row("10927", "2001", "resource", "SII208 Doc"),
    ]

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=rows):
        result = hebat_list_course_activities.invoke({})

    assert "10974" in result
    assert "10927" in result
    assert "SII209 Task" in result
    assert "SII208 Doc" in result
    sii209_pos = result.find("10974")
    sii208_pos = result.find("10927")
    assert sii209_pos != -1 and sii208_pos != -1


def test_filters_by_activity_type_passed_to_storage():
    from xninetzy.os.academic.hebat.tools import hebat_list_course_activities

    rows = [_row("10974", "1001", "assign", "Tugas", "P1")]

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=rows) as mock_list:
        hebat_list_course_activities.invoke({"course_id": "10974", "activity_type": "assign"})

    mock_list.assert_called_once_with("10974", "assign")


def test_search_matches_title_substring_case_insensitive():
    from xninetzy.os.academic.hebat.tools import hebat_list_course_activities

    rows = [
        _row("10974", "1001", "assign", "User Persona", "Pertemuan 7"),
        _row("10974", "1002", "assign", "Tugas Lain", "Pertemuan 1"),
    ]

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=rows):
        result_lower = hebat_list_course_activities.invoke(
            {"course_id": "10974", "search": "persona"}
        )
        result_upper = hebat_list_course_activities.invoke(
            {"course_id": "10974", "search": "PERSONA"}
        )

    assert "User Persona" in result_lower
    assert "Tugas Lain" not in result_lower
    assert "User Persona" in result_upper


def test_limit_clamps_negative_to_one():
    from xninetzy.os.academic.hebat.tools import hebat_list_course_activities

    rows = [_row("10974", str(1000 + i), "assign", f"T{i}") for i in range(5)]

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=rows):
        result = hebat_list_course_activities.invoke({"course_id": "10974", "limit": -5})

    assert result.count("(`assign`)") == 1


def test_limit_clamps_over_200_to_200():
    from xninetzy.os.academic.hebat.tools import hebat_list_course_activities

    rows = [_row("10974", str(1000 + i), "assign", f"T{i}") for i in range(300)]

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=rows):
        result = hebat_list_course_activities.invoke({"course_id": "10974", "limit": 999})

    assert result.count("(`assign`)") == 200


def test_suggests_running_sync_when_no_match():
    from xninetzy.os.academic.hebat.tools import hebat_list_course_activities

    rows = [_row("10974", "1001", "assign", "Tugas X")]

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=rows):
        result = hebat_list_course_activities.invoke(
            {"course_id": "10974", "search": "Nonexistent"}
        )

    assert "Tidak ditemukan" in result or "tidak ada" in result.lower()
    assert "sync_course_activities" in result


@pytest.mark.asyncio
async def test_round_trip_sync_then_list():
    from xninetzy.os.academic.hebat.models import ActivityType
    from xninetzy.os.academic.hebat.tools import (
        hebat_list_course_activities,
        hebat_sync_course_activities,
    )

    mock_activities = [
        {
            "cmid": "1001",
            "type": ActivityType.ASSIGN,
            "title": "Tugas A",
            "section_title": "Pertemuan 1",
            "activity_url": "https://hebat.unair.ac.id/mod/assign/view.php?id=1001",
        },
        {
            "cmid": "1002",
            "type": ActivityType.RESOURCE,
            "title": "Materi A",
            "section_title": "Pertemuan 1",
            "activity_url": "https://hebat.unair.ac.id/mod/resource/view.php?id=1002",
        },
    ]

    upserted: list = []

    def fake_upsert(act):
        upserted.append(act)
        return 1

    with (
        patch(
            "xninetzy.os.academic.hebat.tools.fetch_course_activities",
            new=AsyncMock(return_value=mock_activities),
        ),
        patch("xninetzy.os.academic.hebat.tools.upsert_activity", side_effect=fake_upsert),
        patch("xninetzy.os.academic.hebat.tools._ensure_session_or_msg", return_value=None),
    ):
        sync_result = await hebat_sync_course_activities.ainvoke(
            {"chat_id": "test_chat", "course_id": "10974"}
        )

    assert "Sync selesai" in sync_result
    assert len(upserted) == 2

    list_input = [
        {
            "course_id": act.course_id,
            "cmid": act.cmid,
            "type": act.type.value,
            "title": act.title,
            "section_title": act.section_title,
            "activity_url": act.activity_url,
        }
        for act in upserted
    ]

    with patch("xninetzy.os.academic.hebat.tools.list_activities", return_value=list_input):
        list_result = hebat_list_course_activities.invoke({"course_id": "10974"})

    assert "Tugas A" in list_result
    assert "Materi A" in list_result
