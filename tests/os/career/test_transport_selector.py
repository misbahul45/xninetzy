"""Test transport selector plans."""

from __future__ import annotations

from xninetzy.os.career.acquisition.transport_selector import (
    CacheState,
    HealthSnapshot,
    SourceDefinition,
    Transport,
    TransportSelector,
)


def _api_source() -> SourceDefinition:
    return SourceDefinition(
        source_id="remoteok",
        display_name="RemoteOK",
        domains=("remoteok.com",),
        has_documented_api=True,
        is_static=True,
        pagination_type="API_CURSOR",
    )


def _dynamic_source() -> SourceDefinition:
    return SourceDefinition(
        source_id="dynamic",
        display_name="Dynamic",
        has_documented_api=False,
        is_static=False,
        requires_javascript=True,
        pagination_type="INFINITE_SCROLL",
    )


def test_api_source_prefers_documented_api() -> None:
    plan = TransportSelector.plan(_api_source(), policy_can_api=True)
    assert plan.primary == Transport.DOCUMENTED_API
    assert plan.browser_required is False


def test_api_source_falls_back_to_http_when_api_blocked_by_policy() -> None:
    plan = TransportSelector.plan(
        _api_source(),
        policy_can_api=False,
        policy_can_http=True,
        policy_can_browser=True,
    )
    assert plan.primary == Transport.STATIC_HTTP


def test_circuit_open_with_no_cache_returns_none() -> None:
    plan = TransportSelector.plan(
        _api_source(),
        health=HealthSnapshot(is_open=True, is_degraded=False),
        cache=CacheState(fresh=False),
    )
    assert plan.primary == Transport.NONE
    assert plan.max_attempts == 0


def test_circuit_open_with_fresh_cache_returns_cache() -> None:
    plan = TransportSelector.plan(
        _api_source(),
        health=HealthSnapshot(is_open=True, is_degraded=False),
        cache=CacheState(fresh=True),
    )
    assert plan.primary == Transport.CACHE


def test_dynamic_source_uses_browser_when_allowed() -> None:
    plan = TransportSelector.plan(
        _dynamic_source(),
        policy_can_api=True,
        policy_can_http=True,
        policy_can_browser=True,
    )
    assert plan.primary == Transport.BROWSER
    assert plan.browser_required is True


def test_strict_fresh_ignores_stale_cache() -> None:
    plan = TransportSelector.plan(
        _api_source(),
        cache=CacheState(fresh=False),
        requested_freshness="strict_fresh",
    )
    # Strict fresh + stale cache ⇒ primary is still API (since source has
    # documented API) but cache is not in fallback.
    assert plan.primary in {Transport.DOCUMENTED_API, Transport.STATIC_HTTP}
    assert Transport.CACHE not in plan.fallback


def test_no_transport_permitted_by_policy() -> None:
    plan = TransportSelector.plan(
        _api_source(),
        policy_can_api=False,
        policy_can_http=False,
        policy_can_browser=False,
    )
    assert plan.primary == Transport.NONE
