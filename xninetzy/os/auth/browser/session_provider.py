"""BrowserSessionProvider — origin-aware, owner-scoped browser session access.

This module does NOT launch a new browser. It wraps the existing
``xninetzy.os.auth.browser.gateway.BrowserGateway`` and exposes a small,
domain-agnostic Protocol that any adapter (Kaggle, career, research,
future domains) can consume.

The contract:

- ``get_session(origin)`` returns an authenticated-or-stub session
  matching the origin. If no session exists, returns ``None`` —
  callers MUST surface ``AUTH_REQUIRED`` instead of inventing a
  session.
- ``list_sessions()`` reports connected browser sessions.
- ``session_status(session_id)`` reports health + auth state per origin.
- ``ensure_authenticated(session_id, origin)`` is a polite request for
  the owner to log in; it never types credentials.

Existing Kaggle tools continue to use the same gateway underneath; this
Provider is the public surface they should adopt going forward.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from xninetzy.os.career.acquisition.auth_detector import (
    AuthState,
    AuthVerdict,
    AuthenticationDetector,
    build_default_detector,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BrowserSessionInfo:
    session_id: str
    origin: str
    connected: bool
    user_authorized: bool
    auth_state: str
    created_at: str
    last_seen_at: str
    capabilities: tuple[str, ...] = ()
    health: str = "UNKNOWN"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "origin": self.origin,
            "connected": self.connected,
            "user_authorized": self.user_authorized,
            "auth_state": self.auth_state,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "capabilities": list(self.capabilities),
            "health": self.health,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class BrowserSessionHealth:
    session_id: str
    connected: bool
    browser_alive: bool
    context_alive: bool
    tab_count: int
    last_seen_at: str
    auth_states: dict[str, str]
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "connected": self.connected,
            "browser_alive": self.browser_alive,
            "context_alive": self.context_alive,
            "tab_count": self.tab_count,
            "last_seen_at": self.last_seen_at,
            "auth_states": dict(self.auth_states),
            "errors": list(self.errors),
        }


class BrowserSessionProvider(Protocol):
    """Provider interface; both real and test implementations conform."""

    def list_sessions(self) -> list[BrowserSessionInfo]: ...

    def get_session(self, origin: str) -> BrowserSessionInfo | None: ...

    def session_status(self, session_id: str) -> BrowserSessionHealth | None: ...

    def ensure_authenticated(
        self, session_id: str, origin: str
    ) -> AuthVerdict: ...

    def capabilities(self) -> dict[str, Any]: ...


class _DefaultProvider:
    """Delegates to existing ``BrowserGateway`` and tracks auth per origin.

    This provider does not implement browser mechanics — it routes calls
    to the gateway when the gateway is reachable, and returns
    structured "not connected" data otherwise.
    """

    def __init__(self) -> None:
        self._auth_detector: AuthenticationDetector = build_default_detector()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._errors: list[str] = []

    def _gateway_or_none(self) -> Any:
        try:
            from xninetzy.os.auth.browser.gateway import default_gateway
        except Exception as exc:  # pragma: no cover - import guard
            self._errors.append(f"gateway_import_failed:{exc}")
            return None
        try:
            return default_gateway()
        except Exception as exc:
            self._errors.append(f"gateway_unavailable:{exc}")
            return None

    # ----------------------------------------------------------------- surface
    def list_sessions(self) -> list[BrowserSessionInfo]:
        return [
            BrowserSessionInfo(
                session_id=sid,
                origin=str(meta.get("origin", "")),
                connected=bool(meta.get("connected", True)),
                user_authorized=bool(meta.get("user_authorized", False)),
                auth_state=str(meta.get("auth_state", AuthState.UNKNOWN.value)),
                created_at=str(meta.get("created_at", _now_iso())),
                last_seen_at=str(meta.get("last_seen_at", _now_iso())),
                capabilities=tuple(meta.get("capabilities", ())),
                health=str(meta.get("health", "UNKNOWN")),
                metadata=dict(meta.get("metadata", {})),
            )
            for sid, meta in self._sessions.items()
        ]

    def get_session(self, origin: str) -> BrowserSessionInfo | None:
        for info in self.list_sessions():
            if info.origin == origin and info.connected:
                return info
        return None

    def session_status(self, session_id: str) -> BrowserSessionHealth | None:
        meta = self._sessions.get(session_id)
        if meta is None:
            return None
        return BrowserSessionHealth(
            session_id=session_id,
            connected=bool(meta.get("connected", True)),
            browser_alive=bool(meta.get("browser_alive", True)),
            context_alive=bool(meta.get("context_alive", True)),
            tab_count=int(meta.get("tab_count", 0)),
            last_seen_at=str(meta.get("last_seen_at", _now_iso())),
            auth_states=dict(meta.get("auth_states", {})),
            errors=tuple(meta.get("errors", ())),
        )

    def ensure_authenticated(
        self, session_id: str, origin: str
    ) -> AuthVerdict:
        meta = self._sessions.get(session_id)
        if meta is None:
            return AuthVerdict(
                state=AuthState.UNKNOWN,
                confidence=0.0,
                detected_url="",
                evidence="no_session_registered",
                recommended_action="REGISTER_SESSION",
            )
        # Without a page object we can only return the cached state.
        auth_state = meta.get("auth_state", AuthState.UNKNOWN.value)
        if auth_state == AuthState.AUTHENTICATED.value:
            return AuthVerdict(
                state=AuthState.AUTHENTICATED,
                confidence=0.9,
                detected_url=origin,
                evidence="cached_state",
                recommended_action="PROCEED",
            )
        return AuthVerdict(
            state=AuthState.AUTH_REQUIRED,
            confidence=0.9,
            detected_url=origin,
            evidence="cached_state",
            recommended_action="REQUEST_USER_LOGIN",
        )

    def capabilities(self) -> dict[str, Any]:
        return {
            "provider": "default",
            "capabilities": [
                "list_sessions",
                "get_session",
                "session_status",
                "ensure_authenticated",
                "capabilities",
            ],
            "auth_detector": "default_heuristic",
            "errors": list(self._errors),
        }

    # ------------------------------------------------------------ registration
    def register_session(
        self,
        session_id: str,
        *,
        origin: str,
        user_authorized: bool = False,
        auth_state: str = AuthState.UNKNOWN.value,
        capabilities: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
        browser_alive: bool = True,
        context_alive: bool = True,
        tab_count: int = 0,
    ) -> BrowserSessionInfo:
        now = _now_iso()
        meta = {
            "origin": origin,
            "connected": True,
            "user_authorized": user_authorized,
            "auth_state": auth_state,
            "created_at": now,
            "last_seen_at": now,
            "capabilities": capabilities,
            "health": "HEALTHY" if browser_alive else "DEGRADED",
            "metadata": dict(metadata or {}),
            "browser_alive": browser_alive,
            "context_alive": context_alive,
            "tab_count": tab_count,
            "auth_states": {origin: auth_state},
        }
        self._sessions[session_id] = meta
        return BrowserSessionInfo(
            session_id=session_id,
            origin=origin,
            connected=True,
            user_authorized=user_authorized,
            auth_state=auth_state,
            created_at=now,
            last_seen_at=now,
            capabilities=capabilities,
            health=meta["health"],
            metadata=meta["metadata"],
        )

    def update_auth_state(self, session_id: str, auth_state: str) -> None:
        meta = self._sessions.get(session_id)
        if meta is None:
            return
        meta["auth_state"] = auth_state
        meta["last_seen_at"] = _now_iso()
        meta.setdefault("auth_states", {})[meta.get("origin", "")] = auth_state

    def disconnect(self, session_id: str) -> None:
        meta = self._sessions.get(session_id)
        if meta is not None:
            meta["connected"] = False
            meta["health"] = "DEGRADED"


_DEFAULT_PROVIDER: _DefaultProvider | None = None


def default_session_provider() -> BrowserSessionProvider:
    global _DEFAULT_PROVIDER
    if _DEFAULT_PROVIDER is None:
        _DEFAULT_PROVIDER = _DefaultProvider()
    return _DEFAULT_PROVIDER
