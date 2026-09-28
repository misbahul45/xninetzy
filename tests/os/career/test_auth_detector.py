"""Test authentication state detector."""

from __future__ import annotations

import asyncio

from xninetzy.os.career.acquisition.auth_detector import (
    AuthState,
    AuthenticationDetector,
    build_default_detector,
)


class _StubPage:
    def __init__(self, *, url: str, present: set[str] | None = None) -> None:
        self._url = url
        self._present = present or set()

    def url(self) -> str:
        return self._url

    async def query_selector(self, selector: str):  # noqa: ARG002
        return _Node() if selector in self._present else None

    async def inner_text(self, selector: str) -> str:  # noqa: ARG002
        return ""


class _Node:
    async def inner_text(self) -> str:
        return ""


def test_signin_url_substring_triggers_auth_required() -> None:
    detector = AuthenticationDetector()
    detector.register_source(
        "x", signin_url_substrings=("/login",), authenticated_url_substrings=("/dashboard",)
    )
    page = _StubPage(url="https://example.com/login")
    verdict = asyncio.run(detector.detect("x", page))
    assert verdict.state == AuthState.AUTH_REQUIRED
    assert verdict.recommended_action == "REQUEST_USER_LOGIN"


def test_authenticated_dom_selector_triggers_authenticated() -> None:
    detector = AuthenticationDetector()
    detector.register_source(
        "x", authenticated_dom_selectors=(".avatar",), signin_dom_selectors=()
    )
    page = _StubPage(url="https://example.com/home", present={".avatar"})
    verdict = asyncio.run(detector.detect("x", page))
    assert verdict.state == AuthState.AUTHENTICATED


def test_no_signal_returns_unknown() -> None:
    detector = AuthenticationDetector()
    detector.register_source("x")
    page = _StubPage(url="https://example.com/something")
    verdict = asyncio.run(detector.detect("x", page))
    assert verdict.state == AuthState.UNKNOWN


def test_default_detector_seeds_kaggle_and_github() -> None:
    detector = build_default_detector()
    assert "kaggle" in detector._signin_url_substrings  # noqa: SLF001
    assert "github" in detector._authenticated_url_substrings  # noqa: SLF001
