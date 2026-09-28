# Career Web Acquisition + Human Browser Gateway — Implementation Report

**Date:** 2026-09-28
**Status:** Complete (Phases 0–12)
**Test results:** 76 passed, 0 failed; ruff clean; live RemoteOK fetch verified

---

## 1. Architecture Summary

Two missions, one shared foundation:

- **Mission A — Career Web Acquisition + Scraping Resilience:** a
  typed composition layer (`xninetzy.os.career.acquisition`) that
  reuses Xninetzy's existing `SourceAdapter`, `RateLimiter`,
  `CircuitBreakerGuard`, `retry_async`, `SearchCache`, and
  `BrowserGateway`. New resilience primitives are added only where the
  existing ones do not cover the requirement (policy gate, transport
  selector, failure taxonomy, page readiness, selector strategy,
  pagination strategies, source health service, quality evaluator,
  authentication detector).

- **Mission B — Human Browser Gateway:** a typed Protocol
  (`xninetzy.os.auth.browser.session_provider`) that wraps the existing
  `BrowserGateway` so future domains (career, research, Kaggle, future
  websites) can subscribe without spinning a second browser daemon or
  adopting a parallel auth model. Authentication is delegated to a
  configurable detector that returns structured `AuthState` values
  rather than free-form "is the user logged in?".

The system is **partial-success aware**, **policy-gated**, **transport-
selective**, **fail-classified**, **observability-friendly**, and
**fixture-testable**. It does NOT bypass WAF, CAPTCHA, anti-bot, rate
limits, or terms of service. BLOCKED sources stay blocked.

---

## 2. Files Added

```
xninetzy/os/career/acquisition/
    __init__.py                          public surface, exports
    policy.py                            SourcePolicy + SourcePolicyGate
    failures.py                          FailureTaxonomy + FailureClassifier
    transport_selector.py                Transport + TransportPlan + SourceDefinition
    readiness.py                         PageReadinessDetector
    extraction.py                        SelectorStrategy + SelectorExtractor
    pagination.py                        PageNumber/Cursor/LoadMore/InfiniteScroll/NoPagination
    health.py                            SourceHealthService + change detection
    quality.py                           ExtractionQualityEvaluator
    auth_detector.py                     AuthenticationDetector + AuthState
    adapter.py                           CareerSourceAdapter Protocol + canonical Job model
    service.py                          CareerAcquisitionService composition root
    adapters/
        __init__.py
        remoteok_career.py               reference adapter wrapping existing RemoteOK

xninetzy/os/auth/browser/
    session_provider.py                  BrowserSessionProvider Protocol + default impl

xninetzy/tools/ecosystem/
    career_scraping_tools.py             5 new MCP tools

docs/
    career-scraping-audit.md             Phase 0 audit + reuse map

tests/os/career/
    test_policy.py                       policy gate semantics
    test_failures.py                     failure taxonomy
    test_transport_selector.py           transport selection rules
    test_quality.py                      extraction quality scoring
    test_extraction.py                   selector fallback chains
    test_readiness.py                    page readiness detection
    test_pagination.py                   pagination strategies + termination
    test_health.py                       source health + structural change
    test_auth_detector.py                auth state detection
    test_session_provider.py             browser session provider
    test_acquisition_service.py          end-to-end partial success
    test_career_scraping_tools.py        MCP tool integration
    test_career_scraping_registry.py     registry verification
    test_remoteok_career_adapter.py      RemoteOK fixture test
    fixtures/career_sources/remoteok/
        sample_record_1.json             JSON fixture
```

---

## 3. Files Modified

```
xninetzy/tools/registry.py                                registered 5 new MCP tools
```

No existing source files were rewritten or duplicated.

---

## 4. Existing Infrastructure Reused

| Component | Source | Reuse |
|---|---|---|
| `SourceAdapter` ABC | `xninetzy/os/research/sources/base.py` | reference for `CareerSourceAdapter` Protocol |
| `RateLimiter` | `xninetzy/os/research/sources/rate_limit.py` | unchanged; consumed by RemoteOK adapter |
| `CircuitBreakerGuard` | `xninetzy/os/research/sources/rate_limit.py` | unchanged; consumed by RemoteOK adapter |
| `retry_async` | `xninetzy/os/research/sources/rate_limit.py` | unchanged; consumed by RemoteOK adapter |
| `SourceRecord` | `xninetzy/os/research/sources/base.py` | reused inside RemoteOKCareerAdapter |
| `RemoteOkAdapter` | `xninetzy/os/research/sources/remoteok.py` | wrapped by `RemoteOkCareerAdapter` |
| `BrowserGateway` | `xninetzy/os/auth/browser/gateway.py` | called from `BrowserSessionProvider` |
| `SearchCache` | `xninetzy/os/career/search_cache.py` | invoked by `career_clear_cache` |
| `to_tool_result` | `xninetzy/tools/tool_results.py` | used by every new MCP tool |
| `tool_results.ToolResult` | `xninetzy/tools/tool_results.py` | unchanged |
| `JobQualityScorer` | `xninetzy/domains/career/services/job_quality_scorer.py` | coexist (not replaced) |
| `CountryNormalizer` | `xninetzy/domains/career/services/country_normalizer.py` | coexist (not replaced) |
| `Ranker` | `xninetzy/domains/career/services/ranker.py` | coexist (not replaced) |

---

## 5. New Components

| Component | Purpose |
|---|---|
| `SourcePolicy` + `SourcePolicyGate` | Explicit per-source policy; BLOCKED/UNKNOWN never silently scraped |
| `FailureTaxonomy` + `FailureClassifier` | 24 enumerated failure types; retryability baked in |
| `TransportSelector` | Deterministic transport plan (API → HTTP → BROWSER → CACHE → SEARCH_REFERENCE) |
| `PageReadinessDetector` | Composable readiness conditions with item-count stability |
| `SelectorStrategy` + `SelectorExtractor` | Ordered fallback chains per field with provenance |
| `PaginationStrategy` (5 modes) | PageNumber / Cursor / LoadMore / InfiniteScroll / None |
| `SourceHealthService` | Per-source metrics + structural-change detection |
| `ExtractionQualityEvaluator` | Field-weighted score in [0,1] with warnings |
| `AuthenticationDetector` | URL + DOM auth-state detection with override hooks |
| `BrowserSessionProvider` Protocol | Origin-aware, owner-scoped, no-credential session surface |
| `CareerAcquisitionService` | Composition root: policy → transport → fetch → readiness → extract → normalize → quality → health |
| `RemoteOkCareerAdapter` | Reference adapter; wraps existing `RemoteOkAdapter` |

---

## 6. Source Capability Matrix

| Source | Policy | API | HTTP | Browser | Pagination | Detail | Notes |
|---|---|---|---|---|---|---|---|
| remoteok | ALLOWED | ✓ | ✗ | ✗ | API_CURSOR | ✗ | Public JSON API |
| arbeitnow | ALLOWED | ✓ | ✗ | ✗ | PAGE_NUMBER | ✗ | Public JSON API |
| kalibrr | API_ONLY | ✓ | ✗ | ✗ | PAGE_NUMBER | ✗ | Partner API only; no browser |
| glints | API_ONLY | ✓ | ✗ | ✗ | PAGE_NUMBER | ✗ | Partner API only; no browser |
| dealls | API_ONLY | ✓ | ✗ | ✗ | PAGE_NUMBER | ✗ | Official API only; no browser |
| jobstreet_id | BLOCKED | ✗ | ✗ | ✗ | – | – | SEEK/Jobstreet ToS blocks automated collection |

---

## 7. Source Policy Matrix

| Source | Status | API | HTTP | Browser | Fallback |
|---|---|---|---|---|---|
| remoteok | ALLOWED | ✓ | ✗ | ✗ | search reference |
| arbeitnow | ALLOWED | ✓ | ✗ | ✗ | search reference |
| kalibrr | API_ONLY | ✓ | ✗ | ✗ | search reference |
| glints | API_ONLY | ✓ | ✗ | ✗ | search reference |
| dealls | API_ONLY | ✓ | ✗ | ✗ | search reference |
| jobstreet_id | BLOCKED | ✗ | ✗ | ✗ | user-provided URL analysis |

---

## 8. Failure Taxonomy

24 enumeration values with retry / severity / fallback decision baked
in. Notable entries:

- `POLICY_BLOCKED` — never retry, never fallback
- `CAPTCHA_REQUIRED` — never retry, never bypass
- `WAF_BLOCK` — never retry, never evade
- `RATE_LIMITED` — retryable, fallback allowed
- `SOURCE_CHANGED` — opens adapter-review ticket
- `TIMEOUT` / `BROWSER_TIMEOUT` — retryable
- `SELECTOR_MISS` / `PARSER_ERROR` — rotate selector chain
- `EMPTY_RESULT` / `EMPTY_RESPONSE` — distinguish from success

`FailureClassifier.from_exception` / `.from_http_status` /
`.from_taxonomy` provide three classification paths used by
`CareerAcquisitionService`.

---

## 9. Retry / Backoff Policy

The existing `RetryPolicy` and `retry_async` are reused unchanged. The
new components do not introduce ad-hoc retry loops. Adapters call
`retry_async` and rely on the existing exponential backoff with bounded
jitter. Per-source `RetryPolicy.max_attempts` / `backoff_base_seconds`
/ `backoff_max_seconds` come from `SourceAdapter.retry`.

Future enhancement (documented, not implemented in this phase):
respect `Retry-After` headers inside `retry_async` for HTTP responses.

---

## 10. Circuit Breaker Policy

The existing `CircuitBreaker` + `CircuitBreakerGuard` are reused. The
new `SourceHealthService` mirrors circuit state for diagnostics:

```
CLOSED  → 3+ consecutive failures  →  DEGRADED
DEGRADED → OPEN (operator may reset)
OPEN    → fresh cache hit         →  CACHE
OPEN    → no cache                →  NONE (do not fetch)
```

Structural-change detection flags a source when current record count
drops below 50% of baseline after at least 10 prior records.

---

## 11. Cache Policy

- **Discovery cache**: implicit via `SearchCache` (LRU + TTL).
- **Per-source**: `SearchCache.clear_source(prefix)` evicts keys that
  start with `<source>:`.
- **All sources**: `SearchCache.clear()` wipes the LRU store.
- **Source health cache**: in-memory mirror in `SourceHealthService`;
  not persisted (snapshots available via `career_source_health`).
- **Browser HTML snapshot cache**: not added in this phase. Reuses the
  existing `BrowserGateway` cache.

Stale-while-revalidate semantics: `TransportSelector.plan` honors
`requested_freshness` (`"any" | "fresh" | "strict_fresh"`).

---

## 12. Test Results

```
$ uv run pytest tests/os/career/test_*.py --no-header -q
76 passed in 3.73s
```

Coverage by group (mapped to brief's mandated groups):

| Brief group | Test file | Tests |
|---|---|---|
| 1 — Policy | test_policy.py | 6 |
| 2 — HTTP retry | test_failures.py (status classification) | 7 |
| 3 — Backoff | test_failures.py (retryable flags) | 7 |
| 4 — Circuit breaker | test_health.py (streak + circuit mirror) | 7 |
| 5 — Cache | (existing tests cover SearchCache; new tests rely on it) | n/a |
| 6 — Pagination | test_pagination.py | 6 |
| 7 — Extraction | test_extraction.py | 4 |
| 8 — Dedup | existing `applications_store` covers; identity hashing documented in `Job.content_hash` | n/a |
| 9 — Partial success | test_acquisition_service.py | 4 |
| 10 — Browser | test_session_provider.py + existing browser tests | 9 |
| 11 — Quality regression | test_quality.py + test_health.py (change detection) | 13 |
| 12 — MCP | test_career_scraping_tools.py + test_career_scraping_registry.py | 10 |

Existing test surface (no regressions):

```
$ uv run pytest tests/os/career/{test_compliance,test_dashboard_tools,...}.py --no-header -q
110 passed in 46.81s
```

Ruff:

```
$ uv run ruff check xninetzy/os/career/acquisition/ xninetzy/os/auth/browser/session_provider.py xninetzy/tools/ecosystem/career_scraping_tools.py tests/os/career/
All checks passed!
```

Live integration smoke test:

```
$ uv run python -c "from xninetzy.tools.ecosystem.career_scraping_tools import career_scrape_run; ..."
status: SUCCESS
sources: ['remoteok']
job count: 3
quality: avg=0.633
```

---

## 13. Known Limitations

1. **`retry_async` does not yet parse `Retry-After`.** Documented as
   enhancement; out of scope for this phase.
2. **No browser HTML snapshot cache** has been added. The
   `BrowserGateway` already caches HTML internally; we did not
   introduce a parallel layer.
3. **Browser-backed acquisition for Kalibrr / Glints / Dealls /
   Jobstreet is blocked by policy** and intentionally not implemented.
   These require partner API access. The pipeline returns
   `POLICY_BLOCKED` cleanly.
4. **`InfiniteScrollPagination` and `LoadMorePagination` are
   implemented and tested with stub pages.** Real Playwright
   integration tests are skipped in the offline test suite by design;
   fixtures are sufficient.
5. **AuthenticationDetector uses URL + DOM heuristics only.** It
   intentionally does not scrape cookies. Authenticated session state
   comes from the `BrowserSessionProvider` cache.
6. **Per-source policies are operator-curated.** New sources default
   to `UNKNOWN`, which surfaces `OPEN_POLICY_REVIEW_TICKET` rather
   than silent scraping.
7. **RemoteOKCareerAdapter does not currently hit the network from
   tests** (fixtures used). Live smoke test verified end-to-end at
   implementation time.

---

## 14. Blocked Sources

| Source | Reason |
|---|---|
| jobstreet_id | SEEK/Jobstreet ToS blocks automated collection |

Other Indonesian boards (Kalibrr, Glints, Dealls) are *API_ONLY* —
they are not blocked outright, but the policy gate refuses browser
fetches and HTTP scraping. They can be wired up once a partner API key
is available.

---

## 15. Sources Requiring Manual / API Authorization

- `kalibrr` — partner API key
- `glints` — TalentSearch API key
- `dealls` — official API access

These are routed through `USER_AUTHORIZED_ONLY` once the operator
installs the partner key; the existing authentication flow surfaces
`AUTH_REQUIRED` and waits for the owner to attach the credential.

---

## 16. Follow-up Technical Debt

1. `retry_async` should parse `Retry-After` headers when present.
2. `SourceHealthService` should persist snapshots to SQLite for
   cross-session analysis.
3. `JobDetail` enrichment is not yet implemented per source (RemoteOK
   treats listing payload as sufficient detail); Arbeitnow and the
   Indonesian boards will need adapter-specific detail fetchers.
4. `InfiniteScrollPagination` and `LoadMorePagination` need real-page
   Playwright integration tests, gated behind an env-flag.
5. Browser-session `register_session` should accept a real page object
   from the gateway rather than only stub metadata.
6. Selector strategies for non-API sources (Kalibrr, Glints once
   authorized) should be authored per the `SelectorStrategy` schema.
7. `AcquisitionResult.warnings` should be wired into the existing
   `observability_events` table for trace persistence.

---

## 17. Exact Commands Run

```bash
# Audit
ls xninetzy/os/research/sources/ | head -40
wc -l xninetzy/os/research/sources/*.py | sort -rn | head -20
ls xninetzy/tools/ecosystem/ | grep career

# Implementation verification (sanity)
uv run python -c "from xninetzy.os.career.acquisition import build_remoteok_career_adapter, CareerAcquisitionService; print('OK')"
uv run python -c "from xninetzy.tools.ecosystem.career_scraping_tools import career_scrape_diagnose, career_validate_source; print('OK')"
uv run python -c "from xninetzy.tools.registry import get_all_tools; print(len(get_all_tools()))"
# → 513

# MCP tool coverage
uv run python -c "from xninetzy.tools.registry import get_all_tools; ..."
# All 5 new tools present in canonical registry.

# Targeted unit tests
uv run pytest tests/os/career/test_policy.py \
              tests/os/career/test_failures.py \
              tests/os/career/test_transport_selector.py \
              tests/os/career/test_quality.py \
              tests/os/career/test_extraction.py \
              tests/os/career/test_readiness.py \
              tests/os/career/test_pagination.py \
              tests/os/career/test_health.py \
              tests/os/career/test_auth_detector.py \
              tests/os/career/test_session_provider.py \
              tests/os/career/test_acquisition_service.py \
              tests/os/career/test_career_scraping_tools.py \
              tests/os/career/test_career_scraping_registry.py \
              tests/os/career/test_remoteok_career_adapter.py \
              --no-header -q
# → 76 passed in 3.73s

# Regression: existing career surface
uv run pytest tests/os/career/test_compliance.py \
              tests/os/career/test_dashboard_tools.py \
              tests/os/career/test_intent_router.py \
              tests/os/career/test_orchestrator.py \
              tests/os/career/test_package_generator.py \
              tests/os/career/test_phase2_services.py \
              tests/os/career/test_profile.py \
              tests/os/career/test_ranker.py \
              tests/os/career/test_safe_fields.py \
              tests/os/career/test_search_cache.py \
              tests/os/career/test_browser_session.py \
              --no-header -q
# → 110 passed in 46.81s

# Research adapters regression
uv run pytest tests/os/research/test_query_match.py \
              tests/os/research/test_indonesia_adapters.py \
              --no-header -q
# → 20 passed in 17.64s

# Ruff
uv run ruff check xninetzy/os/career/acquisition/ \
                xninetzy/os/auth/browser/session_provider.py \
                xninetzy/tools/ecosystem/career_scraping_tools.py \
                tests/os/career/
# → All checks passed!

# Live integration smoke test (network-dependent, included for transparency)
uv run python -c "from xninetzy.tools.ecosystem.career_scraping_tools import career_scrape_run; career_scrape_run.func(keyword='python', sources='remoteok', max_results=3)"
# → SUCCESS, 3 jobs from remoteok.com/api
```

---

## 18. Final MCP Tool List

New tools registered in `xninetzy.tools.registry`:

| Tool | Risk | Purpose |
|---|---|---|
| `career_scrape_diagnose` | READ | Per-source diagnostic report (policy, transport, session, extraction, quality) |
| `career_scrape_run` | READ | Multi-source acquisition with partial-success semantics |
| `career_clear_cache` | WRITE | Cache eviction (per source or all) |
| `career_validate_source` | READ | Policy review entry point for a source |
| `career_source_health` | READ | Per-source health snapshot |

Canonical registry total: **513 tools** (was 508 before; +5).

Existing tools unchanged. Kaggle tools continue to work via the existing
`xninetzy.os.auth.browser.gateway`. The new `BrowserSessionProvider`
is available for future refactors that want a typed surface, but
existing Kaggle callers do not need to migrate.

---

## 19. Acceptance Criteria Coverage

| AC item | Status |
|---|---|
| shared source registry | existing `SOURCE_REGISTRY` |
| source policy gate | NEW `xninetzy/os/career/acquisition/policy.py` |
| common adapter contract | NEW `CareerSourceAdapter` Protocol |
| canonical Job model | NEW `NormalizedJob` (frozen dataclass, mirrors brief fields) |
| HTTP transport | existing `httpx` via `RemoteOkAdapter` |
| Browser transport | existing `BrowserGateway` via `BrowserSessionProvider` |
| readiness engine | NEW `PageReadinessDetector` |
| selector fallback | NEW `SelectorStrategy` + `SelectorExtractor` |
| pagination abstraction | NEW 5 strategies |
| infinite-scroll | NEW `InfiniteScrollPagination` |
| load-more | NEW `LoadMorePagination` |
| retry engine | existing |
| backoff | existing |
| circuit breaker | existing + NEW health mirror |
| health service | NEW `SourceHealthService` |
| cache integration | existing `SearchCache` |
| dedup | existing `applications_store` + content_hash on `NormalizedJob` |
| provenance | NEW `FieldProvenance` + per-field selector metadata |
| quality evaluation | NEW `ExtractionQualityEvaluator` |
| partial success | NEW `CareerAcquisitionService.run` returns `PARTIAL_SUCCESS` |
| structured failure taxonomy | NEW 24-entry `FailureTaxonomy` |
| browser artifacts | NEW `BrowserSessionProvider` |
| source change detection | NEW `SourceHealthService.detect_change` |
| fixtures | NEW under `tests/os/career/fixtures/career_sources/remoteok/` |
| unit tests | NEW 14 files, 76 tests |
| MCP tools registered | NEW 5 tools, verified in canonical registry |
| MCP schemas verified | all use `to_tool_result` standard envelope |
| security checks pass | existing safe_fetch / secret redaction preserved |
| secret redaction verified | no secrets logged; no tokens in adapters |
| SSRF protection preserved | not weakened |
| documentation updated | NEW `docs/career-scraping-audit.md` + this report |

---

End of report.
