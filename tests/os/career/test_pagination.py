"""Test pagination strategies."""

from __future__ import annotations

from xninetzy.os.career.acquisition.pagination import (
    CursorPagination,
    InfiniteScrollPagination,
    LoadMorePagination,
    NoPagination,
    PageNumberPagination,
)


def test_page_number_advances_until_empty() -> None:
    p = PageNumberPagination()
    state = p.initial_state()
    r1 = p.update(state, items_count=10, items_ids=[f"id-{i}" for i in range(10)])
    assert r1.should_continue is True
    assert state.page_index == 2
    r2 = p.update(state, items_count=0, items_ids=[])
    assert r2.should_continue is False
    assert state.termination_reason == "no_new_items"


def test_cursor_stops_when_next_cursor_missing() -> None:
    p = CursorPagination()
    state = p.initial_state()
    r = p.update(state, items_count=5, items_ids=["a", "b"], next_cursor=None)
    assert r.should_continue is False
    assert state.termination_reason == "no_next_cursor"


def test_cursor_detects_repeated_cursor() -> None:
    p = CursorPagination()
    state = p.initial_state()
    state.cursor = "abc"
    r = p.update(state, items_count=5, items_ids=["x"], next_cursor="abc")
    assert r.should_continue is False
    assert state.termination_reason == "repeated_cursor"


def test_no_pagination_marks_done_immediately() -> None:
    p = NoPagination()
    state = p.initial_state()
    assert state.done is True
    assert state.termination_reason == "no_pagination"


def test_infinite_scroll_records_termination() -> None:
    p = InfiniteScrollPagination(max_scrolls=2, poll_interval_ms=10)

    class _Page:
        async def evaluate(self, _script: str) -> int:  # noqa: ARG002
            return 0

        async def query_selector_all(self, _selector: str):  # noqa: ARG002
            return []

    import asyncio

    result = asyncio.run(
        p.run(_Page(), items_count_provider=lambda page: page.query_selector_all("x"))
    )
    assert result.state.done is True
    assert result.state.termination_reason in {
        "no_new_items_after_scrolls",
        "no_growth_after_scrolls",
        "max_scrolls_reached",
        "max_runtime_exceeded",
    }


def test_load_more_terminates_when_button_absent() -> None:
    p = LoadMorePagination(poll_interval_ms=10)

    class _Page:
        async def query_selector(self, _selector: str):  # noqa: ARG002
            return None

        async def query_selector_all(self, _selector: str):  # noqa: ARG002
            return []

    import asyncio

    result = asyncio.run(
        p.run(_Page(), items_count_provider=lambda page: page.query_selector_all("x"))
    )
    assert result.state.termination_reason == "no_button_found"
