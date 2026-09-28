"""Centralized transport selection.

Maps ``SourceDefinition`` + current source health + cache freshness into
a concrete ``TransportPlan`` with an ordered list of transports to try.

Selection rules (deterministic, conservative):

1. If the source declares a documented API and policy permits it,
   DOCUMENTED_API is preferred.
2. Otherwise, if the page is static and policy permits, STATIC_HTTP.
3. Otherwise, if dynamic JS is required AND policy permits browser,
   BROWSER.
4. Otherwise, attempt CACHE if a usable entry exists.
5. Otherwise, return a no-fetch plan; the caller must surface a
   structured ``unsupported`` outcome.

The selector never escalates HTTP 403 into a browser attempt. HTTP 403
indicates an access/security restriction and must be reported as such.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Transport(StrEnum):
    DOCUMENTED_API = "DOCUMENTED_API"
    STATIC_HTTP = "STATIC_HTTP"
    BROWSER = "BROWSER"
    USER_BROWSER = "USER_BROWSER"
    CACHE = "CACHE"
    SEARCH_REFERENCE = "SEARCH_REFERENCE"
    NONE = "NONE"


@dataclass(frozen=True)
class TransportPlan:
    source_id: str
    primary: Transport
    fallback: tuple[Transport, ...] = ()
    max_attempts: int = 3
    browser_required: bool = False
    user_authorized_only: bool = False
    notes: str = ""


@dataclass(frozen=True)
class SourceDefinition:
    """Operator-declared description of a career source's capabilities."""

    source_id: str
    display_name: str
    domains: tuple[str, ...] = ()
    country: str = ""
    policy_status: str = "ALLOWED"
    has_documented_api: bool = False
    is_static: bool = True
    requires_javascript: bool = False
    detail_pages_supported: bool = True
    search_supported: bool = True
    pagination_type: str = "NONE"  # PAGE_NUMBER | NEXT_LINK | CURSOR | LOAD_MORE | INFINITE_SCROLL | API_CURSOR | NONE
    rate_limit_rpm: int = 30
    parser_version: str = "1.0"
    notes: str = ""


@dataclass(frozen=True)
class CacheState:
    fresh: bool
    last_fetched_at: str | None = None
    parser_version: str | None = None


@dataclass(frozen=True)
class HealthSnapshot:
    is_open: bool
    is_degraded: bool
    failure_streak: int = 0
    last_success_at: str | None = None
    last_failure_at: str | None = None


class TransportSelector:
    """Deterministic, side-effect-free transport planner.

    This module is the single source of truth for *which* transport to use.
    Adapters MUST consult this selector before attempting a fetch.
    """

    @staticmethod
    def plan(
        source: SourceDefinition,
        *,
        health: HealthSnapshot | None = None,
        cache: CacheState | None = None,
        requested_freshness: str = "any",  # "any" | "fresh" | "strict_fresh"
        policy_can_browser: bool = True,
        policy_can_http: bool = True,
        policy_can_api: bool = True,
        user_authorized: bool = False,
    ) -> TransportPlan:
        # Policy gate pre-empts everything when nothing is allowed.
        if not (policy_can_api or policy_can_http or policy_can_browser):
            return TransportPlan(
                source_id=source.source_id,
                primary=Transport.NONE,
                max_attempts=0,
                notes="no_transport_permitted_by_policy",
            )

        # Circuit breaker open + cache miss ⇒ no fetch.
        health = health or HealthSnapshot(
            is_open=False, is_degraded=False, failure_streak=0
        )
        if health.is_open:
            if cache is not None and cache.fresh:
                return TransportPlan(
                    source_id=source.source_id,
                    primary=Transport.CACHE,
                    max_attempts=1,
                    notes="circuit_open_using_cache",
                )
            return TransportPlan(
                source_id=source.source_id,
                primary=Transport.NONE,
                max_attempts=0,
                notes="circuit_open_no_cache",
            )

        # Strict freshness: ignore cache unless it's fresh.
        if (
            requested_freshness == "strict_fresh"
            and cache is not None
            and not cache.fresh
        ):
            usable_cache = False
        else:
            usable_cache = cache is not None and cache.fresh

        # 1) Documented API
        if source.has_documented_api and policy_can_api:
            fallback: list[Transport] = []
            if source.is_static and policy_can_http:
                fallback.append(Transport.STATIC_HTTP)
            if source.requires_javascript and policy_can_browser:
                fallback.append(Transport.BROWSER)
            if usable_cache:
                fallback.append(Transport.CACHE)
            return TransportPlan(
                source_id=source.source_id,
                primary=Transport.DOCUMENTED_API,
                fallback=tuple(fallback),
                max_attempts=1 + len(fallback),
                browser_required=False,
                notes="api_first",
            )

        # 2) Static HTTP
        if source.is_static and policy_can_http:
            fb: list[Transport] = []
            if source.has_documented_api and policy_can_api:
                fb.append(Transport.DOCUMENTED_API)
            if usable_cache:
                fb.append(Transport.CACHE)
            if not fb:
                fb.append(Transport.SEARCH_REFERENCE)
            return TransportPlan(
                source_id=source.source_id,
                primary=Transport.STATIC_HTTP,
                fallback=tuple(fb),
                max_attempts=1 + len(fb),
                browser_required=False,
                notes="static_http_first",
            )

        # 3) Browser (when dynamic and allowed)
        if source.requires_javascript and policy_can_browser:
            fb = []
            if usable_cache:
                fb.append(Transport.CACHE)
            if source.has_documented_api and policy_can_api:
                fb.append(Transport.DOCUMENTED_API)
            return TransportPlan(
                source_id=source.source_id,
                primary=Transport.BROWSER if user_authorized else Transport.BROWSER,
                fallback=tuple(fb),
                max_attempts=1 + len(fb),
                browser_required=True,
                user_authorized_only=not user_authorized,
                notes="browser_first",
            )

        # 4) Cache fallback
        if usable_cache:
            return TransportPlan(
                source_id=source.source_id,
                primary=Transport.CACHE,
                max_attempts=1,
                notes="cache_only",
            )

        # 5) Search reference (last-mile)
        return TransportPlan(
            source_id=source.source_id,
            primary=Transport.SEARCH_REFERENCE,
            max_attempts=1,
            notes="no_direct_fetch_possible_use_search_reference",
        )


# Convenience transport registry used by the operator dashboard.
DEFAULT_SOURCE_DEFINITIONS: tuple[SourceDefinition, ...] = (
    SourceDefinition(
        source_id="remoteok",
        display_name="RemoteOK",
        domains=("remoteok.com",),
        country="GLOBAL",
        policy_status="ALLOWED",
        has_documented_api=True,
        is_static=True,
        requires_javascript=False,
        detail_pages_supported=False,
        pagination_type="API_CURSOR",
        rate_limit_rpm=10,
        parser_version="1.0",
        notes="Public JSON API at /api",
    ),
    SourceDefinition(
        source_id="arbeitnow",
        display_name="Arbeitnow",
        domains=("arbeitnow.com",),
        country="GLOBAL",
        policy_status="ALLOWED",
        has_documented_api=True,
        is_static=True,
        requires_javascript=False,
        detail_pages_supported=False,
        pagination_type="PAGE_NUMBER",
        rate_limit_rpm=10,
        parser_version="1.0",
        notes="Public JSON API at /api/job-board-api",
    ),
    SourceDefinition(
        source_id="kalibrr",
        display_name="Kalibrr",
        domains=("kalibrr.com",),
        country="ID",
        policy_status="API_ONLY",
        has_documented_api=True,
        is_static=False,
        requires_javascript=True,
        pagination_type="PAGE_NUMBER",
        rate_limit_rpm=5,
        parser_version="1.0",
        notes="API partner key required; browser scraping disallowed.",
    ),
    SourceDefinition(
        source_id="glints",
        display_name="Glints",
        domains=("glints.com",),
        country="ID",
        policy_status="API_ONLY",
        has_documented_api=True,
        is_static=False,
        requires_javascript=True,
        pagination_type="PAGE_NUMBER",
        rate_limit_rpm=5,
        parser_version="1.0",
        notes="TalentSearch API key required; browser scraping disallowed.",
    ),
    SourceDefinition(
        source_id="dealls",
        display_name="Dealls",
        domains=("dealls.com",),
        country="ID",
        policy_status="API_ONLY",
        has_documented_api=True,
        is_static=False,
        requires_javascript=True,
        pagination_type="PAGE_NUMBER",
        rate_limit_rpm=5,
        parser_version="1.0",
        notes="Official API only; no browser scraping.",
    ),
    SourceDefinition(
        source_id="jobstreet_id",
        display_name="Jobstreet Indonesia",
        domains=("jobstreet.co.id",),
        country="ID",
        policy_status="BLOCKED",
        has_documented_api=False,
        is_static=False,
        requires_javascript=True,
        pagination_type="PAGE_NUMBER",
        rate_limit_rpm=0,
        parser_version="1.0",
        notes="Blocked by SEEK/Jobstreet ToS.",
    ),
)


def default_definitions() -> dict[str, SourceDefinition]:
    return {s.source_id: s for s in DEFAULT_SOURCE_DEFINITIONS}


__all__ = [
    "CacheState",
    "DEFAULT_SOURCE_DEFINITIONS",
    "HealthSnapshot",
    "SourceDefinition",
    "Transport",
    "TransportPlan",
    "TransportSelector",
    "default_definitions",
]
