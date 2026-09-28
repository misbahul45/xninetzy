"""Test selector strategy + extractor."""

from __future__ import annotations

import pytest

from xninetzy.os.career.acquisition.extraction import (
    SelectorCandidate,
    SelectorChain,
    SelectorExtractor,
    SelectorStrategy,
)


class _StubPage:
    def __init__(self, mapping: dict[str, str | None]) -> None:
        self.mapping = mapping

    async def query_selector(self, selector: str):  # noqa: ARG002
        return _Node(self.mapping.get(selector))

    async def query_selector_all(self, selector: str):  # noqa: ARG002
        return [_Node(self.mapping.get(selector))] if self.mapping.get(selector) else []


class _Node:
    def __init__(self, text: str | None) -> None:
        self.text = text

    async def inner_text(self) -> str:
        return self.text or ""


async def _resolver(selector: str, page: _StubPage):
    node = await page.query_selector(selector)
    if node is None:
        return None
    return await node.inner_text()


def test_strategy_requires_at_least_one_candidate() -> None:
    with pytest.raises(ValueError):
        SelectorChain(field_name="title", candidates=())


def test_first_candidate_wins_when_present() -> None:
    strategy = SelectorStrategy()
    strategy.add(
        SelectorChain(
            field_name="title",
            candidates=(
                SelectorCandidate(selector="[data-testid='job-title']"),
                SelectorCandidate(selector="h1"),
            ),
        )
    )
    page = _StubPage({"[data-testid='job-title']": "Engineer"})
    extractor = SelectorExtractor(strategy)
    import asyncio

    result = asyncio.run(extractor.extract("title", page, _resolver))
    assert result is not None
    assert result.value == "Engineer"
    assert result.fallback_used is False
    assert result.candidate_index == 0


def test_fallback_chain_records_fallback_used() -> None:
    strategy = SelectorStrategy()
    strategy.add(
        SelectorChain(
            field_name="company",
            candidates=(
                SelectorCandidate(selector="[data-testid='company']"),
                SelectorCandidate(selector=".company-name"),
            ),
        )
    )
    page = _StubPage({".company-name": "Acme"})
    extractor = SelectorExtractor(strategy)
    import asyncio

    result = asyncio.run(extractor.extract("company", page, _resolver))
    assert result is not None
    assert result.value == "Acme"
    assert result.fallback_used is True
    assert result.candidate_index == 1


def test_no_match_returns_none() -> None:
    strategy = SelectorStrategy()
    strategy.add(
        SelectorChain(
            field_name="title",
            candidates=(SelectorCandidate(selector="h1"),),
        )
    )
    page = _StubPage({})
    extractor = SelectorExtractor(strategy)
    import asyncio

    result = asyncio.run(extractor.extract("title", page, _resolver))
    assert result is None
