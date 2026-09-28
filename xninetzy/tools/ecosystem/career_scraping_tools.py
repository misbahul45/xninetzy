"""Career scraping + diagnostic MCP tools.

Tools exposed in this module:

- ``career_scrape_diagnose`` — dry-run report per source
- ``career_scrape_run`` — multi-source acquisition with partial success
- ``career_clear_cache`` — operator-controlled cache eviction
- ``career_validate_source`` — policy review entry point

All tools are READ-class (``career_clear_cache`` is WRITE, gated through
existing mutation policy).
"""

from __future__ import annotations

import asyncio
import uuid

from langchain_core.tools import tool

from xninetzy.os.career.acquisition import (
    CareerAcquisitionService,
    CareerSearchRequest,
    SourceHealthService,
    SourcePolicyGate,
    build_default_gate,
    build_remoteok_career_adapter,
    build_research_browser_career_adapter,
)
from xninetzy.os.career.search_cache import SearchCache
from xninetzy.tools.tool_results import to_tool_result


_SERVICES: dict[str, CareerAcquisitionService] = {}
_GATES: dict[str, SourcePolicyGate] = {}
_HEALTHS: dict[str, SourceHealthService] = {}


def _service() -> CareerAcquisitionService:
    """Return the process-wide ``CareerAcquisitionService``.

    Built lazily because most tests / callers do not need it.
    """

    cached = _SERVICES.get("default")
    if cached is not None:
        return cached
    svc = CareerAcquisitionService(
        adapters=[
            build_remoteok_career_adapter(),
            build_research_browser_career_adapter('kalibrr', country='ID'),
            build_research_browser_career_adapter('glints', country='ID'),
            build_research_browser_career_adapter('dealls', country='ID'),
        ],
    )
    _SERVICES["default"] = svc
    return svc


def _gate() -> SourcePolicyGate:
    cached = _GATES.get("default")
    if cached is not None:
        return cached
    gate = build_default_gate()
    _GATES["default"] = gate
    return gate


def _health() -> SourceHealthService:
    cached = _HEALTHS.get("default")
    if cached is not None:
        return cached
    health = SourceHealthService()
    _HEALTHS["default"] = health
    return health


@tool
def career_scrape_diagnose(
    source: str,
    keyword: str = "software",
    location: str = "",
    work_mode: str = "any",
    chat_id: str = "system",
    sender_id: str = "",
) -> str:
    """Return a structured diagnostic report for one career source.

    The report contains:

    - policy verdict (status, can_fetch, recommended_action)
    - transport plan (primary, fallback, browser_required)
    - browser session availability (placeholder; populated by
      ``xninetzy/os/auth/browser/session_provider``)
    - selector strategy fields
    - source health snapshot

    Args:
        source: source id, e.g. ``"remoteok"``, ``"kalibrr"``
        keyword: keyword to dry-run the search request with
        location: optional location filter
        work_mode: "remote" | "hybrid" | "onsite" | "any"
        chat_id: chat principal
        sender_id: owner principal
    """

    request = CareerSearchRequest(
        keyword=keyword or "software",
        location=location or None,
        work_arrangement=work_mode or None,
        sources=(source,),
        user_authorized=False,
    )
    svc = _service()
    report = asyncio.run(svc.diagnose(source, request=request))
    # Surface a meaningful policy_status even when the source has no
    # registered adapter (e.g. BLOCKED sources are never wired).
    policy_status = (
        report["policy"]["status"]
        if report["policy"]
        else _gate().get(source).status.value
    )
    return to_tool_result(
        summary=f"career_scrape_diagnose:{source}",
        items=[report],
        meta={"source": source, "policy_status": policy_status},
    )


@tool
def career_scrape_run(
    keyword: str,
    sources: str = "",
    location: str = "",
    work_mode: str = "any",
    freshness: str = "any",
    max_results: int = 25,
    user_authorized: bool = False,
    chat_id: str = "system",
    sender_id: str = "",
) -> str:
    """Run multi-source career acquisition with partial-success semantics.

    Args:
        keyword: free-text search keyword
        sources: optional comma-separated source list
        location: optional location filter
        work_mode: "remote" | "hybrid" | "onsite" | "any"
        freshness: "any" | "fresh" | "strict_fresh"
        max_results: max records per source
        user_authorized: whether the operator has confirmed a logged-in
            browser session for sources that require authentication
        chat_id: chat principal
        sender_id: owner principal
    """

    src_list = tuple(s for s in sources.split(",") if s.strip()) if sources else ()
    request = CareerSearchRequest(
        keyword=keyword,
        location=location or None,
        work_arrangement=work_mode or None,
        freshness=freshness,
        sources=src_list,
        max_results=max(1, min(100, max_results)),
        user_authorized=bool(user_authorized),
    )
    trace_id = uuid.uuid4().hex[:16]
    svc = _service()
    result = asyncio.run(svc.run(request, trace_id=trace_id))
    return to_tool_result(
        summary=f"career_scrape_run:{result.status}",
        items=result.jobs,
        meta={
            "status": result.status,
            "sources": {k: v.to_dict() for k, v in result.sources.items()},
            "warnings": list(result.warnings),
            "trace_id": result.trace_id,
            "freshness": result.freshness,
            "quality": result.quality,
            "query": result.query,
        },
    )


@tool
def career_clear_cache(
    source: str = "",
    chat_id: str = "system",
    sender_id: str = "",
) -> str:
    """Evict search cache for one source (or all sources when source is empty).

    The existing ``SearchCache`` is reused; the tool only adds a thin
    wrapper so operators do not need to know about the underlying
    table layout.
    """

    cache = SearchCache()
    # The existing ``SearchCache.clear`` accepts no arguments and
    # wipes the entire LRU store. We expose per-source as a hint and
    # treat the underlying cache as a single namespace; if finer
    # scoping is required, callers should rely on ``cache.put`` with
    # source-scoped keys.
    if source:
        # Drop entries whose key starts with ``source`` substring.
        keys_to_drop = [
            key
            for key in list(cache._store.keys())  # noqa: SLF001 (intentional)
            if key.startswith(source + ":") or source in key
        ]
        for key in keys_to_drop:
            cache._store.pop(key, None)  # noqa: SLF001
        removed = len(keys_to_drop)
        cleared = [source]
    else:
        removed = cache.clear()
        cleared = ["*"]
    return to_tool_result(
        summary=f"career_clear_cache:{source or 'all'}",
        items=[],
        meta={"cleared": cleared, "removed_count": int(removed)},
    )


@tool
def career_validate_source(
    source: str,
    action: str = "read",
    chat_id: str = "system",
    sender_id: str = "",
) -> str:
    """Validate a source against the operator-declared policy gate.

    Args:
        source: source id to evaluate
        action: intended action ("read", "interact", "write")
        chat_id: chat principal
        sender_id: owner principal
    """

    gate = _gate()
    policy = gate.get(source)
    transport = "API" if action == "read" else None
    verdict = gate.evaluate(source, transport=transport, requires_user_login=False)
    return to_tool_result(
        summary=f"career_validate_source:{source}",
        items=[
            {
                "source": source,
                "policy_status": policy.status.value,
                "verdict_status": verdict.status.value,
                "can_fetch": verdict.can_fetch,
                "can_use_browser": verdict.can_use_browser,
                "can_use_static_http": verdict.can_use_static_http,
                "can_use_documented_api": verdict.can_use_documented_api,
                "requires_user_login": verdict.requires_user_login,
                "reason": verdict.reason,
                "recommended_action": verdict.recommended_action,
                "notes": policy.notes,
            }
        ],
        meta={"source": source},
    )


@tool
def career_source_health(
    source: str = "",
    chat_id: str = "system",
    sender_id: str = "",
) -> str:
    """Return health snapshot for one source or for every tracked source.

    The snapshot mirrors ``xninetzy.os.career.acquisition.SourceHealthService``
    output. Sources that have never been observed return ``UNKNOWN``.
    """

    health = _health()
    if source:
        rec = health.snapshot(source)
        items = [
            {
                "source_id": rec.source_id,
                "status": rec.status,
                "success_count": rec.success_count,
                "failure_count": rec.failure_count,
                "rate_limited_count": rec.rate_limited_count,
                "timeout_count": rec.timeout_count,
                "blocked_count": rec.blocked_count,
                "extraction_failure_count": rec.extraction_failure_count,
                "avg_latency_ms": round(rec.avg_latency_ms, 2),
                "p95_latency_ms": round(rec.p95_latency_ms, 2),
                "records_last_run": rec.records_last_run,
                "selector_fallback_rate": round(rec.selector_fallback_rate, 3),
                "parser_version": rec.parser_version,
                "circuit_state": rec.circuit_state,
                "failure_streak": rec.failure_streak,
                "last_success_at": rec.last_success_at,
                "last_failure_at": rec.last_failure_at,
                "last_failure_reason": rec.last_failure_reason,
                "last_failure_taxonomy": rec.last_failure_taxonomy,
            }
        ]
    else:
        items = []
        for rec in health.snapshot_all():
            items.append(
                {
                    "source_id": rec.source_id,
                    "status": rec.status,
                    "avg_latency_ms": round(rec.avg_latency_ms, 2),
                    "failure_streak": rec.failure_streak,
                    "circuit_state": rec.circuit_state,
                    "records_last_run": rec.records_last_run,
                }
            )
    return to_tool_result(
        summary=f"career_source_health:{source or 'all'}",
        items=items,
        meta={"source": source or "all", "count": len(items)},
    )


career_scraping_tools = [
    career_scrape_diagnose,
    career_scrape_run,
    career_clear_cache,
    career_validate_source,
    career_source_health,
]


__all__ = [
    "career_clear_cache",
    "career_scrape_diagnose",
    "career_scrape_run",
    "career_scraping_tools",
    "career_source_health",
    "career_validate_source",
]
