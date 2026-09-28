# Career Web Acquisition + Scraping Resilience — Audit

**Date:** 2026-09-28
**Scope:** Existing reuse, gaps, integration points
**Audience:** Xninetzy operators extending career acquisition + browser gateway

---

## 1. Executive Summary

Xninetzy sudah memiliki sebagian besar infrastruktur yang diminta oleh
brief misi. Audit ini memetakan apa yang **sudah ada**, apa yang **kurang**,
dan ke mana komponen baru harus di-attach.

Reuse is the strategy. We do not duplicate `SourceAdapter`, `RateLimiter`,
`CircuitBreakerGuard`, `retry_async`, `BrowserGateway`, atau `SourceRegistry`.

What is **missing** (and what this phase will add):

| Missing component | Status |
|---|---|
| Explicit `SourcePolicy` + policy gate | NEW |
| Centralized `TransportSelector` | NEW |
| `PageReadinessDetector` (richer than `wait_selector`) | NEW |
| `SelectorStrategy` with ordered fallback candidates | NEW |
| `PaginationStrategy` abstraction (PageNumber/Cursor/LoadMore/InfiniteScroll) | NEW |
| `SourceHealthService` with structured metrics | NEW |
| `ExtractionQualityEvaluator` | NEW |
| `FailureTaxonomy` enum + classifier | NEW |
| `career_scrape_diagnose` MCP tool | NEW |
| `career_scrape_run` MCP tool | NEW |
| `career_clear_cache` MCP tool | NEW |
| `career_validate_source` MCP tool | NEW |
| `BrowserSessionProvider` extracted from Kaggle | REFACTOR (already partly in `os/career/browser_session.py`) |
| `AuthenticationDetector` | NEW |
| Origin-aware session routing | NEW |

---

## 2. Repository Map (existing)

### 2.1 Source registry + adapters

```
xninetzy/os/research/sources/
├── base.py              # SourceAdapter ABC, SourceCategory, SourceRecord, RateLimit, RetryPolicy, CircuitBreaker
├── rate_limit.py        # RateLimiter, CircuitBreakerGuard, retry_async
├── registry.py          # SOURCE_REGISTRY, register_adapter, get_adapter, build_rate_limiter, build_breaker
├── query_match.py       # matches_query (already implemented)
├── browser_session.py   # GatewayBrowserSession (wraps existing browser gateway)
├── browser_scraper.py   # Generic scraper that delegates to gateway session
├── arbeitnow.py         # ArbeitNow API adapter
├── arxiv.py             # arXiv API
├── bps.py, dbpedia.py, dblp.py, ...  # 30+ research sources
├── remoteok.py          # RemoteOK JSON API (job board) — REFERENCE FOR CAREER API
├── kalibrr.py           # Kalibrr (Indonesia)
├── glints.py            # Glints (Indonesia)
├── dealls.py            # Dealls (Indonesia)
├── jobstreet_id.py      # Jobstreet Indonesia
├── kaggle.py            # Kaggle — REFERENCE FOR BROWSER SESSION
```

**Reuse:** `SourceAdapter`, `RateLimiter`, `CircuitBreakerGuard`, `retry_async`,
`SourceRecord`, `SOURCE_REGISTRY`.

**Note:** The existing adapters follow `search()` + `fetch()` + `health()`.
The career mission requires `fetch_listing_page` + `parse_listing_page` +
`fetch_job_detail` + `parse_job_detail`. We will **extend** `SourceAdapter`
with optional `CareerSourceAdapter` subclass that adds listing/detail stages.
Existing adapters do not break.

### 2.2 Career domain (already mature)

```
xninetzy/os/career/
├── browser_session.py   # CareerBrowserSession + FakeFormPage (safe-fields protocol)
├── compliance.py        # Source policy compliance checks
├── dashboard.py         # Owner dashboard data
├── orchestrator.py      # ApplicationConfirmationToken lifecycle
├── safe_fields.py       # FormField classifier + partition_by_safety
├── search_cache.py      # Per-query cache
├── applications_store.py# SQLite-backed application tracking
xninetzy/domains/career/
├── services/
│   ├── country_normalizer.py
│   ├── job_quality_scorer.py
│   ├── package_generator.py   # CV + cover letter generator
│   ├── ranker.py
├── intent/intent_router.py
├── profile/{builder.py, profile.py}
├── eval/{harness.py, metrics.py, loader.py, schema.py}
```

**Reuse:** `JobQualityScorer`, `CountryNormalizer`, `Ranker`,
`SearchCache`, `Compliance`.

### 2.3 Browser gateway (Kaggle-grade)

```
xninetzy/os/auth/browser/gateway.py    # BrowserGateway, BrowserGatewayUnavailable,
                                        # default_gateway, launch_local_browser,
                                        # close_local_browser
xninetzy/os/auth/
├── oauth/         # OAuth flow abstractions
├── policies/      # Action policy + risk classification
├── providers/     # Provider registry
├── secrets/       # Secret storage (encrypted at rest)
├── sessions/      # Session lifecycle
├── tools/         # Browser/auth MCP tools
```

**Reuse:** `BrowserGateway`, `default_gateway()`, `launch_local_browser`,
`close_local_browser`. NO new browser daemon. NO new Playwright runtime.

### 2.4 MCP tools (canonical registry)

```
xninetzy/tools/ecosystem/
├── career_tools.py              # 17 career_* tools (search, get_job, etc.)
├── career_application_tools.py  # Apply / track / outcome
├── career_browser_tools.py      # Browser-mediated job interactions
├── career_dashboard_tools.py
├── career_ops_tools.py          # Source health, observability
├── career_orchestrator_tools.py # Multi-source orchestration
├── career_profile_tools.py      # CV profile + GitHub sync
```

**Reuse:** All `career_*` tools already registered. We add new tools via
`career_scrape_diagnose`, `career_scrape_run`, `career_clear_cache`,
`career_validate_source`.

### 2.5 Tests (existing career surface)

```
tests/os/career/
├── test_browser_session.py    # FakeFormPage + safe-fields
├── test_browser_tools.py
├── test_career_tools.py
├── test_compliance.py
├── test_dashboard_tools.py
├── test_eval_harness.py
├── test_intent_router.py
├── test_orchestrator.py
├── test_package_generator.py
├── test_phase2_services.py
├── test_profile.py
├── test_ranker.py
├── test_safe_fields.py
├── test_search_cache.py
```

**Reuse:** `FakeFormPage` as deterministic test fixture for new browser tests.

---

## 3. Gap Analysis

### 3.1 SourcePolicy (missing)

Current `compliance.py` does runtime checks per-source but does not
declare an explicit `SourcePolicy` schema with policy states.

**Add:** `xninetzy/os/career/acquisition/policy.py`
with `SourcePolicy`, `PolicyStatus` enum, and a gate that returns
`POLICY_BLOCKED` / `AUTH_REQUIRED` / `ALLOWED` before any fetch.

### 3.2 TransportSelector (missing)

Current `BrowserGateway` already abstracts browser vs HTTP-less transport,
but no central selector that maps `SourceDefinition + request` →
`TransportPlan`.

**Add:** `xninetzy/os/career/acquisition/transport_selector.py`

### 3.3 PageReadinessDetector (missing)

Current `GatewayBrowserSession.get_html(wait_selector=...)` supports only
a single selector. Real pages need:
- selector exists
- selector count >= N
- text appears
- URL matches
- loading indicator disappears
- stable item count across N ticks

**Add:** `xninetzy/os/career/acquisition/readiness.py`

### 3.4 SelectorStrategy (missing)

Each field currently relies on one hard-coded selector. Brief mandates
ordered fallback list with telemetry.

**Add:** `xninetzy/os/career/acquisition/extraction.py` with
`SelectorChain` + `SelectorStrategy`.

### 3.5 PaginationStrategy (missing)

Each adapter today fetches a single page. We need generic
PageNumber / Cursor / LoadMore / InfiniteScroll strategies.

**Add:** `xninetzy/os/career/acquisition/pagination.py`

### 3.6 SourceHealthService (missing)

`career_ops_tools.py` exposes some health data but not the full per-source
metrics (success_rate, p95_latency, selector_fallback_rate, circuit_state).

**Add:** `xninetzy/os/career/acquisition/health.py`

### 3.7 FailureTaxonomy (missing)

Errors today are scattered `Exception` types. Need enum-based taxonomy.

**Add:** `xninetzy/os/career/acquisition/failures.py`

### 3.8 Diagnostic tools (missing)

`career_scrape_diagnose`, `career_scrape_run`, `career_clear_cache`,
`career_validate_source` — not present.

**Add:** `xninetzy/tools/ecosystem/career_scraping_tools.py`

### 3.9 BrowserSessionProvider (refactor target)

Already partly implemented in `xninetzy/os/career/browser_session.py` and
`xninetzy/os/research/sources/browser_session.py`. The two should converge
on a single `BrowserSessionProvider` Protocol that:

- `get_session(origin: str) -> BrowserSession | None`
- `list_sessions() -> list[BrowserSession]`
- `session_status(session_id)`
- `ensure_authenticated(session_id, origin) -> AuthState`

**Add:** `xninetzy/os/auth/browser/session_provider.py` with Protocol
+ adapters that delegate to existing `BrowserGateway`.

### 3.10 AuthenticationDetector (missing)

No structured auth-state detection (UNKNOWN / SIGNED_OUT / AUTHENTICATING /
AUTHENTICATED / SESSION_EXPIRED / AUTH_REQUIRED / ACCESS_DENIED).

**Add:** `xninetzy/os/career/acquisition/auth_detector.py` with heuristic
rules + per-source override hook.

---

## 4. Integration Points

New code attaches to existing surfaces:

```
xninetzy/os/career/
├── acquisition/                       # NEW directory
│   ├── __init__.py
│   ├── policy.py                      # SourcePolicy + gate
│   ├── transport_selector.py          # TransportPlan
│   ├── readiness.py                   # PageReadinessDetector
│   ├── extraction.py                  # SelectorStrategy + SelectorChain
│   ├── pagination.py                  # PaginationStrategy
│   ├── health.py                      # SourceHealthService
│   ├── failures.py                    # FailureTaxonomy
│   ├── quality.py                     # ExtractionQualityEvaluator
│   └── service.py                     # CareerAcquisitionService
├── compliance.py                      # REUSE
├── search_cache.py                    # REUSE
└── browser_session.py                 # EXTEND (delegates to session_provider)

xninetzy/os/auth/browser/
├── session_provider.py                # NEW — Protocol + default impl
└── gateway.py                         # REUSE

xninetzy/tools/ecosystem/
└── career_scraping_tools.py           # NEW MCP surface

tests/os/career/
├── test_policy.py                     # NEW
├── test_transport_selector.py
├── test_readiness.py
├── test_extraction.py
├── test_pagination.py
├── test_health.py
├── test_failures.py
├── test_quality.py
├── test_acquisition_service.py
├── test_career_scraping_tools.py
└── fixtures/
    └── career_sources/
        ├── remoteok/                 # API JSON fixtures
        └── arbeitnow/                # API JSON fixtures
```

---

## 5. Design Constraints (from existing code)

1. **No new browser daemon.** Use `BrowserGateway` exclusively.
2. **No new MCP server.** All tools go through `xninetzy.tools.registry`.
3. **No new cache backend.** Reuse `xninetzy/os/career/search_cache.py`.
4. **No new rate-limit engine.** Reuse `xninetzy/os/research/sources/rate_limit.py`.
5. **No new risk model.** Reuse `xninetzy/os/auth/policies/`.
6. **No new HITL mechanism.** Reuse `xninetzy/os/career/orchestrator.py` +
   `xninetzy/hitl/*`.
7. **No new secret store.** Reuse `xninetzy/os/auth/secrets/`.
8. **No new SSRF / safe_fetch.** Reuse existing.
9. **No new retry semantics.** Extend `RetryPolicy` only.
10. **No new circuit breaker semantics.** Extend `CircuitBreaker` only.

---

## 6. Dependency Graph (added modules)

```
SourcePolicy
    ↓
TransportSelector → SourceDefinition → SourceRegistry (existing)
    ↓
CareerAcquisitionService
    ├── PolicyGate → SourcePolicy
    ├── CircuitBreakerGuard (existing)
    ├── RateLimiter (existing)
    ├── retry_async (existing)
    ├── TransportSelector
    ├── Transport:
    │     ├── DocumentedApiTransport → SourceAdapter.search (existing)
    │     ├── StaticHttpTransport → httpx (existing in adapters)
    │     ├── BrowserTransport → BrowserSessionProvider → BrowserGateway (existing)
    │     └── CacheTransport → SearchCache (existing)
    ├── PageReadinessDetector (browser only)
    ├── SelectorStrategy
    ├── PaginationStrategy
    ├── ExtractionQualityEvaluator
    ├── SourceHealthService
    └── FailureClassifier → FailureTaxonomy
```

---

## 7. Risk + Authorization Map

| Tool | Risk | HITL | Idempotency | Notes |
|---|---|---|---|---|
| `career_search_jobs` | READ | no | yes (query hash) | exists |
| `career_get_job` | READ | no | yes (job id) | exists |
| `career_source_health` | READ | no | yes | exists |
| `career_source_capabilities` | READ | no | yes | exists |
| `career_scrape_diagnose` | READ | no | yes | NEW |
| `career_scrape_run` | READ | no | yes | NEW (preview + explicit confirm required) |
| `career_clear_cache` | WRITE | yes (cache delete) | yes (key) | NEW |
| `career_validate_source` | READ | no | yes | NEW |

---

## 8. Acceptance Criteria Mapping

| AC item | Where it lands |
|---|---|
| shared source registry | exists (`SOURCE_REGISTRY`) |
| source policy gate | NEW `policy.py` |
| common adapter contract | NEW `CareerSourceAdapter` Protocol in `xninetzy/os/career/acquisition/` |
| canonical Job model | normalize on existing `SourceRecord` + extend via `JobDetail` |
| HTTP transport | existing `httpx` (already in adapters) |
| Browser transport | existing `BrowserGateway` via `BrowserSessionProvider` |
| readiness engine | NEW `readiness.py` |
| selector fallback | NEW `extraction.py` |
| pagination abstraction | NEW `pagination.py` |
| retry engine | existing |
| backoff | existing |
| circuit breaker | existing |
| health service | NEW `health.py` |
| cache integration | existing `search_cache.py` |
| dedup | existing `applications_store` + per-job hash in `JobDetail` |
| provenance | NEW `provenance.py` |
| quality evaluation | NEW `quality.py` (extends `JobQualityScorer`) |
| partial success | NEW `service.py` `AcquisitionResult` |
| structured failure taxonomy | NEW `failures.py` |
| browser artifacts | NEW `artifacts.py` |
| source change detection | NEW in `health.py` |
| fixtures | NEW under `tests/os/career/fixtures/` |
| unit tests | NEW |
| MCP tools registered | NEW `career_scraping_tools.py` |
| security checks pass | existing safe_fetch preserved |

---

## 9. Known Limitations

1. The existing `RateLimiter` is single-bucket (per-minute). For sources that
   publish distinct daily/hourly limits, we extend with per-window buckets
   inside `RateLimiter` without breaking the public surface.
2. `retry_async` does not yet respect `Retry-After` headers. We add that
   inside the same function via a small extension, then mirror it in the
   new `BrowserTransport` (where server-side `Retry-After` is common).
3. `CircuitBreakerGuard` does not support a HALF_OPEN probe count beyond 1.
   Per-source override remains available.
4. No official job-board adapter currently covers Indonesia-local listings
   at API depth beyond RemoteOK / Arbeitnow. Browser-backed acquisition for
   Kalibrr / Glints / Dealls / Jobstreet remains gated by per-source policy.
5. Live integration tests are out-of-scope by default — the test suite is
   fixture-driven and offline.

---

## 10. Implementation Order (final)

1. `policy.py` — SourcePolicy + gate (no deps on new code)
2. `failures.py` — FailureTaxonomy + classifier
3. `transport_selector.py` — TransportPlan + selector
4. `readiness.py` — PageReadinessDetector
5. `extraction.py` — SelectorStrategy + SelectorChain
6. `pagination.py` — PaginationStrategy
7. `quality.py` — ExtractionQualityEvaluator
8. `health.py` — SourceHealthService
9. `service.py` — CareerAcquisitionService (composes above)
10. `auth_detector.py` — AuthenticationDetector
11. `session_provider.py` — BrowserSessionProvider Protocol
12. `career_scraping_tools.py` — MCP surface
13. Tests + fixtures
14. `career_scraping_audit.md` (this file's companion: implementation report)

---

End of audit.
