"""Authentication state detection for browser-driven sources.

The brief mandates structured auth states (UNKNOWN / SIGNED_OUT /
AUTHENTICATING / AUTHENTICATED / SESSION_EXPIRED / AUTH_REQUIRED /
ACCESS_DENIED / CHALLENGE_REQUIRED) rather than free-form "logged in?".

The detector applies:

- explicit per-source override rules (URL substrings / DOM snippets),
- a default heuristic set based on common patterns,
- a hook for adapters to plug in source-specific logic via
  ``register_custom_detector``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Awaitable, Callable, Protocol


class AuthState(StrEnum):
    UNKNOWN = "UNKNOWN"
    SIGNED_OUT = "SIGNED_OUT"
    AUTHENTICATING = "AUTHENTICATING"
    AUTHENTICATED = "AUTHENTICATED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ACCESS_DENIED = "ACCESS_DENIED"
    CHALLENGE_REQUIRED = "CHALLENGE_REQUIRED"


class _AuthPage(Protocol):
    def url(self) -> str: ...

    async def inner_text(self, selector: str) -> str: ...

    async def query_selector(self, selector: str) -> object | None: ...


@dataclass(frozen=True)
class AuthVerdict:
    state: AuthState
    confidence: float
    detected_url: str
    evidence: str
    recommended_action: str

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "confidence": round(self.confidence, 3),
            "detected_url": self.detected_url,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
        }


class AuthenticationDetector:
    """Detects auth state from URL + page DOM with explicit overrides."""

    def __init__(self) -> None:
        self._signin_url_substrings: dict[str, tuple[str, ...]] = {}
        self._authenticated_url_substrings: dict[str, tuple[str, ...]] = {}
        self._signin_dom_selectors: dict[str, tuple[str, ...]] = {}
        self._authenticated_dom_selectors: dict[str, tuple[str, ...]] = {}
        self._custom_detectors: dict[
            str, Callable[[_AuthPage], Awaitable[AuthVerdict | None]]
        ] = {}

    # -------------------------------------------------------------- registration
    def register_source(
        self,
        source_id: str,
        *,
        signin_url_substrings: tuple[str, ...] = (),
        authenticated_url_substrings: tuple[str, ...] = (),
        signin_dom_selectors: tuple[str, ...] = (),
        authenticated_dom_selectors: tuple[str, ...] = (),
    ) -> None:
        self._signin_url_substrings[source_id] = signin_url_substrings
        self._authenticated_url_substrings[source_id] = (
            authenticated_url_substrings
        )
        self._signin_dom_selectors[source_id] = signin_dom_selectors
        self._authenticated_dom_selectors[source_id] = authenticated_dom_selectors

    def register_custom_detector(
        self,
        source_id: str,
        detector: Callable[[_AuthPage], Awaitable[AuthVerdict | None]],
    ) -> None:
        self._custom_detectors[source_id] = detector

    # ---------------------------------------------------------------- detect
    async def detect(
        self, source_id: str, page: _AuthPage
    ) -> AuthVerdict:
        url = page.url()
        custom = self._custom_detectors.get(source_id)
        if custom is not None:
            try:
                v = await custom(page)
                if v is not None:
                    return v
            except Exception:
                pass  # fall back to heuristics

        # URL-based detection
        for sub in self._authenticated_url_substrings.get(source_id, ()):
            if sub and sub in url:
                return AuthVerdict(
                    state=AuthState.AUTHENTICATED,
                    confidence=0.9,
                    detected_url=url,
                    evidence=f"url_contains:{sub}",
                    recommended_action="PROCEED",
                )
        for sub in self._signin_url_substrings.get(source_id, ()):
            if sub and sub in url:
                return AuthVerdict(
                    state=AuthState.AUTH_REQUIRED,
                    confidence=0.9,
                    detected_url=url,
                    evidence=f"url_contains:{sub}",
                    recommended_action="REQUEST_USER_LOGIN",
                )

        # DOM-based detection
        for sel in self._authenticated_dom_selectors.get(source_id, ()):
            try:
                el = await page.query_selector(sel)
            except Exception:
                el = None
            if el is not None:
                return AuthVerdict(
                    state=AuthState.AUTHENTICATED,
                    confidence=0.85,
                    detected_url=url,
                    evidence=f"dom_present:{sel}",
                    recommended_action="PROCEED",
                )
        for sel in self._signin_dom_selectors.get(source_id, ()):
            try:
                el = await page.query_selector(sel)
            except Exception:
                el = None
            if el is not None:
                return AuthVerdict(
                    state=AuthState.AUTH_REQUIRED,
                    confidence=0.85,
                    detected_url=url,
                    evidence=f"dom_present:{sel}",
                    recommended_action="REQUEST_USER_LOGIN",
                )

        return AuthVerdict(
            state=AuthState.UNKNOWN,
            confidence=0.3,
            detected_url=url,
            evidence="no_signal",
            recommended_action="INSPECT",
        )


# Default registrations for sources where the URL/DOM heuristic is reliable.
def build_default_detector() -> AuthenticationDetector:
    detector = AuthenticationDetector()
    detector.register_source(
        "kaggle",
        signin_url_substrings=("/account/login", "auth.kaggle.com"),
        authenticated_url_substrings=("/datasets", "/competitions", "/code"),
        signin_dom_selectors=("form[data-testid='login-form']",),
        authenticated_dom_selectors=("[data-testid='user-avatar']",),
    )
    detector.register_source(
        "github",
        signin_url_substrings=("/login", "/session"),
        authenticated_url_substrings=("/", "/settings"),
        signin_dom_selectors=("form[action='/session']",),
        authenticated_dom_selectors=("img.avatar", "[data-octo-click='repo']"),
    )
    return detector
