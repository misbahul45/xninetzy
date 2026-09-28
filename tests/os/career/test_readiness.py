"""Test page readiness detector."""

from __future__ import annotations

import asyncio

from xninetzy.os.career.acquisition.readiness import (
    PageReadinessDetector,
    ReadinessCondition,
    ReadinessConditionType,
)


class _StubPage:
    def __init__(self, *, count: int, url: str = "https://x") -> None:
        self._count = count
        self._url = url

    def url(self) -> str:
        return self._url

    async def query_selector(self, selector: str):  # noqa: ARG002
        return _Node() if self._count > 0 else None

    async def query_selector_all(self, selector: str):  # noqa: ARG002
        return [_Node() for _ in range(self._count)]

    async def inner_text(self, selector: str) -> str:  # noqa: ARG002
        return "Engineer" if self._count > 0 else ""


class _Node:
    async def inner_text(self) -> str:
        return "Engineer"


def test_first_condition_matches_immediately() -> None:
    detector = PageReadinessDetector(timeout_ms=500, poll_interval_ms=50)
    page = _StubPage(count=3)
    cond = ReadinessCondition(
        type=ReadinessConditionType.SELECTOR_EXISTS, selector=".job-card"
    )
    result = asyncio.run(detector.wait_for_any(page, [cond]))
    assert result.ready is True
    assert result.condition_met == ReadinessConditionType.SELECTOR_EXISTS


def test_empty_page_reports_empty_result() -> None:
    detector = PageReadinessDetector(timeout_ms=300, poll_interval_ms=50)
    page = _StubPage(count=0)
    cond = ReadinessCondition(
        type=ReadinessConditionType.SELECTOR_EXISTS, selector=".job-card"
    )
    result = asyncio.run(
        detector.wait_for_any(page, [cond], item_selector=".job-card")
    )
    assert result.ready is False
    assert result.reason == "EMPTY_RESULT"


def test_no_conditions_returns_no_conditions_provided() -> None:
    detector = PageReadinessDetector()
    page = _StubPage(count=5)
    result = asyncio.run(detector.wait_for_any(page, []))
    assert result.ready is False
    assert result.reason == "no_conditions_provided"


def test_url_pattern_condition() -> None:
    detector = PageReadinessDetector(timeout_ms=200, poll_interval_ms=50)
    page = _StubPage(count=0, url="https://example.com/login")
    cond = ReadinessCondition(
        type=ReadinessConditionType.URL_PATTERN, pattern="/login"
    )
    result = asyncio.run(detector.wait_for_any(page, [cond]))
    assert result.ready is True
    assert result.condition_met == ReadinessConditionType.URL_PATTERN
