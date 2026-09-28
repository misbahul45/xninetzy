"""Test career scraping MCP tools."""

from __future__ import annotations

import json

from xninetzy.tools.ecosystem.career_scraping_tools import (
    career_clear_cache,
    career_scrape_diagnose,
    career_source_health,
    career_validate_source,
)


def _unwrap(out: str) -> dict:
    return json.loads(out)


def test_career_scrape_diagnose_for_allowed_source() -> None:
    out = career_scrape_diagnose.func(source="remoteok", keyword="python")
    data = _unwrap(out)
    assert data["ok"] is True
    item = data["items"][0]
    assert item["policy"]["status"] == "ALLOWED"
    assert item["transport"]["primary"] == "DOCUMENTED_API"


def test_career_scrape_diagnose_for_blocked_source() -> None:
    out = career_scrape_diagnose.func(source="jobstreet_id", keyword="x")
    data = _unwrap(out)
    item = data["items"][0]
    assert item["policy"] is not None
    assert item["policy"]["status"] == "BLOCKED"
    assert item["policy"]["can_fetch"] is False
    assert data["meta"]["meta"]["policy_status"] == "BLOCKED"


def test_career_validate_source_blocked() -> None:
    out = career_validate_source.func(source="jobstreet_id")
    data = _unwrap(out)
    assert data["items"][0]["can_fetch"] is False
    assert data["items"][0]["recommended_action"] == "STOP_DO_NOT_SCRAPE"


def test_career_validate_source_allowed() -> None:
    out = career_validate_source.func(source="remoteok")
    data = _unwrap(out)
    assert data["items"][0]["can_fetch"] is True


def test_career_validate_source_unknown() -> None:
    out = career_validate_source.func(source="not_registered")
    data = _unwrap(out)
    item = data["items"][0]
    assert item["can_fetch"] is False
    assert "UNKNOWN" in item["verdict_status"]


def test_career_source_health_all_unknown_when_never_used() -> None:
    out = career_source_health.func(source="never_run")
    data = _unwrap(out)
    assert data["items"][0]["status"] == "UNKNOWN"


def test_career_clear_cache_all() -> None:
    out = career_clear_cache.func()
    data = _unwrap(out)
    assert data["ok"] is True
    assert data["meta"]["meta"]["cleared"] == ["*"]


def test_career_clear_cache_by_source() -> None:
    out = career_clear_cache.func(source="remoteok")
    data = _unwrap(out)
    assert data["ok"] is True
    assert data["meta"]["meta"]["cleared"] == ["remoteok"]
