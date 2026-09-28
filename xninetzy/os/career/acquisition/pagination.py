"""Pagination strategy abstraction.

The brief mandates a generic, bounded pagination engine with multiple
modes and explicit termination guards.

Every strategy exposes:

- ``build_request(state, page_index)`` -> request descriptor
- ``update_state(state, response, items)`` -> new state + termination flag

Implementations:

- ``PageNumberPagination`` — classic ?page=N
- ``CursorPagination`` — opaque next cursor
- ``LoadMorePagination`` — click-and-wait for new items
- ``InfiniteScrollPagination`` — bounded scroll + content-stability detection
- ``NoPagination`` — single-page source
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Awaitable


class PaginationMode(StrEnum):
    PAGE_NUMBER = "PAGE_NUMBER"
    CURSOR = "CURSOR"
    LOAD_MORE = "LOAD_MORE"
    INFINITE_SCROLL = "INFINITE_SCROLL"
    API_CURSOR = "API_CURSOR"
    NONE = "NONE"


@dataclass
class PaginationState:
    page_index: int = 0
    cursor: str | None = None
    seen_ids: set[str] = field(default_factory=set)
    items_seen: int = 0
    consecutive_empty: int = 0
    done: bool = False
    termination_reason: str | None = None


@dataclass(frozen=True)
class PaginationResult:
    state: PaginationState
    should_continue: bool
    reason: str | None = None


class _PageLike(Any):
    url: Callable[[], str]


@dataclass
class PageNumberPagination:
    page_param: str = "page"
    base_page: int = 1

    def initial_state(self) -> PaginationState:
        return PaginationState(page_index=self.base_page)

    def build_query(self, state: PaginationState) -> dict[str, Any]:
        return {self.page_param: state.page_index}

    def update(
        self, state: PaginationState, items_count: int, items_ids: list[str]
    ) -> PaginationResult:
        new_ids = [i for i in items_ids if i not in state.seen_ids]
        state.seen_ids.update(items_ids)
        state.items_seen += items_count
        if items_count == 0 or not new_ids:
            state.done = True
            state.termination_reason = "no_new_items"
            return PaginationResult(state, False, state.termination_reason)
        state.page_index += 1
        return PaginationResult(state, True)


@dataclass
class CursorPagination:
    cursor_param: str = "cursor"
    cursor_path: str = "next_cursor"  # JSON path in response

    def initial_state(self) -> PaginationState:
        return PaginationState(cursor=None)

    def build_query(self, state: PaginationState) -> dict[str, Any]:
        if state.cursor is None:
            return {}
        return {self.cursor_param: state.cursor}

    def update(
        self,
        state: PaginationState,
        items_count: int,
        items_ids: list[str],
        next_cursor: str | None = None,
    ) -> PaginationResult:
        new_ids = [i for i in items_ids if i not in state.seen_ids]
        state.seen_ids.update(items_ids)
        state.items_seen += items_count
        if not next_cursor:
            state.done = True
            state.termination_reason = "no_next_cursor"
            return PaginationResult(state, False, state.termination_reason)
        if items_count == 0 or not new_ids:
            state.done = True
            state.termination_reason = "no_new_items"
            return PaginationResult(state, False, state.termination_reason)
        if next_cursor == state.cursor:
            state.done = True
            state.termination_reason = "repeated_cursor"
            return PaginationResult(state, False, state.termination_reason)
        state.cursor = next_cursor
        return PaginationResult(state, True)


@dataclass
class NoPagination:
    def initial_state(self) -> PaginationState:
        s = PaginationState()
        s.done = True
        s.termination_reason = "no_pagination"
        return s

    def build_query(self, state: PaginationState) -> dict[str, Any]:
        return {}

    def update(
        self, state: PaginationState, items_count: int, items_ids: list[str]
    ) -> PaginationResult:
        state.seen_ids.update(items_ids)
        state.items_seen += items_count
        return PaginationResult(state, False, "no_pagination")


@dataclass
class InfiniteScrollPagination:
    """Bounded infinite-scroll handler with content-stability detection.

    The handler scrolls the page in fixed steps, waiting for new items to
    appear. It terminates when any of:

    - N consecutive scrolls produce zero new items,
    - the document height stops changing,
    - ``max_scrolls`` is reached,
    - ``max_runtime_seconds`` is exceeded.
    """

    selector_to_count: str = "[data-job-id], .job-card, article"
    max_scrolls: int = 25
    max_runtime_seconds: float = 90.0
    scroll_step_px: int = 800
    poll_interval_ms: int = 400
    empty_scroll_tolerance: int = 3

    def initial_state(self) -> PaginationState:
        return PaginationState()

    def build_query(self, state: PaginationState) -> dict[str, Any]:
        return {}

    async def run(
        self,
        page: Any,
        items_count_provider: Callable[[Any], Awaitable[int]],
    ) -> PaginationResult:
        state = self.initial_state()
        start = time.monotonic()
        last_height = await self._height(page)
        last_count_raw = await items_count_provider(page)
        last_count = (
            len(last_count_raw) if isinstance(last_count_raw, list)
            else int(last_count_raw)
        )
        empty_streak = 0

        for scroll_idx in range(self.max_scrolls):
            elapsed = time.monotonic() - start
            if elapsed > self.max_runtime_seconds:
                state.done = True
                state.termination_reason = "max_runtime_exceeded"
                break
            await self._scroll(page)
            await asyncio.sleep(self.poll_interval_ms / 1000.0)
            count_raw = await items_count_provider(page)
            count = len(count_raw) if isinstance(count_raw, list) else int(count_raw)
            height = await self._height(page)
            if count > last_count:
                last_count = count
                empty_streak = 0
            else:
                empty_streak += 1
            state.items_seen = max(state.items_seen, count)
            if height == last_height and count == last_count:
                if empty_streak >= self.empty_scroll_tolerance:
                    state.done = True
                    state.termination_reason = "no_growth_after_scrolls"
                    break
            else:
                last_height = height
            if empty_streak >= self.empty_scroll_tolerance:
                state.done = True
                state.termination_reason = "no_new_items_after_scrolls"
                break
        else:
            state.done = True
            state.termination_reason = "max_scrolls_reached"
        return PaginationResult(state, False, state.termination_reason)

    async def update(
        self, state: PaginationState, items_count: int, items_ids: list[str]
    ) -> PaginationResult:
        # Infinite-scroll has its own run() loop; update is unused.
        return PaginationResult(state, False, "infinite_scroll_uses_run")

    async def _scroll(self, page: Any) -> None:
        try:
            await page.evaluate(f"window.scrollBy(0, {self.scroll_step_px})")
        except Exception:
            return

    async def _height(self, page: Any) -> int:
        try:
            return int(await page.evaluate("document.body.scrollHeight"))
        except Exception:
            return 0


@dataclass
class LoadMorePagination:
    """Click-and-wait pagination with bounded retries."""

    button_selectors: tuple[str, ...] = (
        "button.load-more",
        "a.load-more",
        "[data-action='load-more']",
        "button:has-text('Load more')",
    )
    max_clicks: int = 20
    poll_interval_ms: int = 500

    def initial_state(self) -> PaginationState:
        return PaginationState()

    def build_query(self, state: PaginationState) -> dict[str, Any]:
        return {}

    async def run(
        self,
        page: Any,
        items_count_provider: Callable[[Any], Awaitable[int]],
    ) -> PaginationResult:
        state = self.initial_state()
        baseline = await items_count_provider(page)
        for click_idx in range(self.max_clicks):
            clicked = False
            for sel in self.button_selectors:
                try:
                    el = await page.query_selector(sel)
                except Exception:
                    el = None
                if el is None:
                    continue
                try:
                    await el.click()
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                state.done = True
                state.termination_reason = "no_button_found"
                break
            await asyncio.sleep(self.poll_interval_ms / 1000.0)
            new_count = await items_count_provider(page)
            if new_count <= baseline:
                state.done = True
                state.termination_reason = "no_growth_after_click"
                break
            baseline = new_count
        else:
            state.done = True
            state.termination_reason = "max_clicks_reached"
        state.items_seen = baseline
        return PaginationResult(state, False, state.termination_reason)

    async def update(
        self, state: PaginationState, items_count: int, items_ids: list[str]
    ) -> PaginationResult:
        return PaginationResult(state, False, "load_more_uses_run")


def strategy_for(mode: str) -> Any:
    """Pick the canonical strategy implementation for a mode string."""

    if mode == PaginationMode.PAGE_NUMBER:
        return PageNumberPagination()
    if mode == PaginationMode.CURSOR or mode == PaginationMode.API_CURSOR:
        return CursorPagination()
    if mode == PaginationMode.INFINITE_SCROLL:
        return InfiniteScrollPagination()
    if mode == PaginationMode.LOAD_MORE:
        return LoadMorePagination()
    return NoPagination()
