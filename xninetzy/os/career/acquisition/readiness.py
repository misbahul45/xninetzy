"""Page readiness detection.

Real pages need more than ``wait_until=networkidle``. The
``PageReadinessDetector`` defines typed conditions a page can satisfy and
combines them with timeout + content-stability guarantees.

The detector is **stateless** — instances carry their configuration
(``timeout_ms``, ``poll_interval_ms``) but no per-page state.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Awaitable, Callable, Protocol


class ReadinessConditionType(StrEnum):
    SELECTOR_EXISTS = "selector_exists"
    SELECTOR_VISIBLE = "selector_visible"
    SELECTOR_COUNT_GE = "selector_count_ge"
    TEXT_PRESENT = "text_present"
    URL_PATTERN = "url_pattern"
    LOADING_GONE = "loading_gone"
    STABLE_ITEM_COUNT = "stable_item_count"


@dataclass(frozen=True)
class ReadinessCondition:
    type: ReadinessConditionType
    selector: str | None = None
    pattern: str | None = None
    text: str | None = None
    min_count: int = 1


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    condition_met: ReadinessConditionType | None
    elapsed_ms: float
    item_count: int | None = None
    reason: str | None = None


class _PageLike(Protocol):
    """Minimum page surface the detector depends on.

    Both real Playwright pages and the ``FakeFormPage`` test double
    satisfy this shape (with a few shim helpers in tests).
    """

    def url(self) -> str: ...

    async def query_selector(self, selector: str) -> object | None: ...

    async def query_selector_all(self, selector: str) -> list[object]: ...

    async def inner_text(self, selector: str) -> str: ...


class PageReadinessDetector:
    """Composes conditions and a polling loop into a single readiness check.

    The detector NEVER returns ``ready=True`` when no items exist. Empty
    results are reported as ``reason="EMPTY_RESULT"`` so callers can
    distinguish "page never loaded" from "page loaded with no rows".
    """

    def __init__(
        self,
        *,
        timeout_ms: int = 15_000,
        poll_interval_ms: int = 250,
        stable_ticks: int = 2,
    ) -> None:
        self._timeout_ms = max(250, timeout_ms)
        self._poll_interval_ms = max(50, poll_interval_ms)
        self._stable_ticks = max(1, stable_ticks)

    async def wait_for_any(
        self,
        page: _PageLike,
        conditions: list[ReadinessCondition],
        *,
        item_selector: str | None = None,
    ) -> ReadinessResult:
        """Return when ANY of the conditions is satisfied, or timeout.

        If ``item_selector`` is provided, the detector additionally
        requires ``item_count`` to stabilize across ``stable_ticks``
        consecutive polls before declaring the page ready. This prevents
        premature extraction on a partially-rendered list.
        """

        if not conditions:
            return ReadinessResult(
                ready=False,
                condition_met=None,
                elapsed_ms=0.0,
                reason="no_conditions_provided",
            )

        start = time.monotonic()
        deadline = start + (self._timeout_ms / 1000.0)
        last_count: int | None = None
        stable_streak = 0

        while time.monotonic() < deadline:
            for cond in conditions:
                met = await self._check(page, cond)
                if met:
                    if item_selector is not None:
                        count = await self._count(page, item_selector)
                        if count == 0:
                            await asyncio.sleep(
                                self._poll_interval_ms / 1000.0
                            )
                            continue
                        if last_count is not None and count == last_count:
                            stable_streak += 1
                        else:
                            stable_streak = 1
                            last_count = count
                        if stable_streak >= self._stable_ticks:
                            return ReadinessResult(
                                ready=True,
                                condition_met=cond.type,
                                elapsed_ms=(time.monotonic() - start) * 1000.0,
                                item_count=count,
                            )
                        await asyncio.sleep(self._poll_interval_ms / 1000.0)
                        continue
                    return ReadinessResult(
                        ready=True,
                        condition_met=cond.type,
                        elapsed_ms=(time.monotonic() - start) * 1000.0,
                    )
            await asyncio.sleep(self._poll_interval_ms / 1000.0)

        # Timeout path — report why.
        if item_selector is not None:
            try:
                count = await self._count(page, item_selector)
            except Exception:
                count = None
        else:
            count = None
        if count == 0:
            return ReadinessResult(
                ready=False,
                condition_met=None,
                elapsed_ms=(time.monotonic() - start) * 1000.0,
                item_count=0,
                reason="EMPTY_RESULT",
            )
        return ReadinessResult(
            ready=False,
            condition_met=None,
            elapsed_ms=(time.monotonic() - start) * 1000.0,
            item_count=count,
            reason="timeout",
        )

    @staticmethod
    async def _check(page: _PageLike, cond: ReadinessCondition) -> bool:
        try:
            if cond.type == ReadinessConditionType.SELECTOR_EXISTS:
                return await page.query_selector(cond.selector or "") is not None
            if cond.type == ReadinessConditionType.SELECTOR_VISIBLE:
                el = await page.query_selector(cond.selector or "")
                return el is not None  # visibility is best-effort here
            if cond.type == ReadinessConditionType.SELECTOR_COUNT_GE:
                nodes = await page.query_selector_all(cond.selector or "")
                return len(nodes) >= max(1, cond.min_count)
            if cond.type == ReadinessConditionType.TEXT_PRESENT:
                txt = await page.inner_text(cond.selector or "body")
                return cond.text is not None and cond.text in txt
            if cond.type == ReadinessConditionType.URL_PATTERN:
                return cond.pattern is not None and cond.pattern in page.url()
            if cond.type == ReadinessConditionType.LOADING_GONE:
                if cond.selector is None:
                    return True
                nodes = await page.query_selector_all(cond.selector)
                return len(nodes) == 0
            if cond.type == ReadinessConditionType.STABLE_ITEM_COUNT:
                return True  # handled by wait_for_any caller
            return False
        except Exception:
            return False

    @staticmethod
    async def _count(page: _PageLike, selector: str) -> int:
        try:
            nodes = await page.query_selector_all(selector)
        except Exception:
            return 0
        return len(nodes)


async_def = Callable[[], Awaitable[None]]
