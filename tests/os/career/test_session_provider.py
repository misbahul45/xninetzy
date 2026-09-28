"""Test BrowserSessionProvider (default impl, no real gateway required)."""

from __future__ import annotations

from xninetzy.os.auth.browser.session_provider import _DefaultProvider
from xninetzy.os.career.acquisition.auth_detector import AuthState


def _fresh() -> _DefaultProvider:
    """Return a fresh provider instance (not the cached singleton)."""

    return _DefaultProvider()


def test_default_provider_capabilities_shape() -> None:
    provider = _fresh()
    caps = provider.capabilities()
    assert "provider" in caps
    assert "list_sessions" in caps["capabilities"]


def test_list_sessions_empty_initially() -> None:
    provider = _fresh()
    assert provider.list_sessions() == []


def test_register_session_appears_in_list() -> None:
    provider = _fresh()
    info = provider.register_session(
        session_id="s1",
        origin="kaggle.com",
        user_authorized=True,
        auth_state=AuthState.AUTHENTICATED.value,
    )
    sessions = provider.list_sessions()
    assert any(s.session_id == "s1" for s in sessions)
    assert info.origin == "kaggle.com"


def test_get_session_for_origin() -> None:
    provider = _fresh()
    provider.register_session(session_id="a", origin="github.com")
    provider.register_session(session_id="b", origin="kaggle.com")
    assert provider.get_session("kaggle.com").session_id == "b"
    assert provider.get_session("unknown.com") is None


def test_session_status_for_registered_session() -> None:
    provider = _fresh()
    provider.register_session(session_id="x", origin="kaggle.com", tab_count=3)
    health = provider.session_status("x")
    assert health.tab_count == 3
    assert provider.session_status("missing") is None


def test_ensure_authenticated_returns_authenticated_when_cached() -> None:
    provider = _fresh()
    provider.register_session(
        session_id="authd",
        origin="kaggle.com",
        auth_state=AuthState.AUTHENTICATED.value,
    )
    verdict = provider.ensure_authenticated("authd", "kaggle.com")
    assert verdict.state == AuthState.AUTHENTICATED


def test_ensure_authenticated_returns_required_when_unknown() -> None:
    provider = _fresh()
    provider.register_session(
        session_id="u",
        origin="kaggle.com",
        auth_state=AuthState.UNKNOWN.value,
    )
    verdict = provider.ensure_authenticated("u", "kaggle.com")
    assert verdict.state == AuthState.AUTH_REQUIRED


def test_ensure_authenticated_unknown_session() -> None:
    provider = _fresh()
    verdict = provider.ensure_authenticated("never", "kaggle.com")
    assert verdict.state == AuthState.UNKNOWN


def test_disconnect_marks_session_unavailable() -> None:
    provider = _fresh()
    provider.register_session(session_id="d", origin="github.com")
    provider.disconnect("d")
    assert provider.get_session("github.com") is None  # connected=False filters out
