"""Career acquisition service — composition root.

Orchestrates: policy gate → transport selector → fetch → readiness →
extraction → pagination → detail enrichment → normalization → quality
→ provenance → source health update.

Multi-source execution MUST be partial-success aware: one failed source
does NOT abort the rest.

This service does NOT launch its own browser, does NOT own its own
retry loop, and does NOT bypass policy.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

from xninetzy.os.career.acquisition.adapter import (
    CareerSourceAdapter,
    JobDetail,
    NormalizedJob,
)
from xninetzy.os.career.acquisition.auth_detector import (
    AuthState,
    AuthenticationDetector,
    build_default_detector,
)
from xninetzy.os.career.acquisition.failures import (
    FailureClassifier,
    FailureTaxonomy,
)
from xninetzy.os.career.acquisition.health import (
    SourceHealthRecord,
    SourceHealthService,
)
from xninetzy.os.career.acquisition.policy import (
    PolicyStatus,
    SourcePolicyGate,
    build_default_gate,
)
from xninetzy.os.career.acquisition.quality import (
    ExtractionQualityEvaluator,
)
from xninetzy.os.career.acquisition.transport_selector import (
    CacheState,
    HealthSnapshot,
    SourceDefinition,
    TransportSelector,
)


@dataclass(frozen=True)
class CareerSearchRequest:
    keyword: str
    location: str | None = None
    work_arrangement: str | None = None
    employment_type: str | None = None
    freshness: str = "any"  # "any" | "fresh" | "strict_fresh"
    sources: tuple[str, ...] = ()
    max_results: int = 50
    user_authorized: bool = False


@dataclass
class SourceOutcome:
    source_id: str
    status: str  # "SUCCESS" | "PARTIAL_SUCCESS" | "EMPTY" | "BLOCKED" | "TIMEOUT" | "ERROR"
    count: int = 0
    warnings: list[str] = field(default_factory=list)
    failure_taxonomy: str | None = None
    failure_reason: str | None = None
    auth_state: str | None = None
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "count": self.count,
            "warnings": list(self.warnings),
            "failure_taxonomy": self.failure_taxonomy,
            "failure_reason": self.failure_reason,
            "auth_state": self.auth_state,
            "elapsed_ms": round(self.elapsed_ms, 3),
        }


@dataclass
class AcquisitionResult:
    status: str  # "SUCCESS" | "PARTIAL_SUCCESS" | "EMPTY" | "FAILED"
    query: dict[str, Any]
    sources: dict[str, SourceOutcome]
    jobs: list[NormalizedJob]
    warnings: list[str] = field(default_factory=list)
    trace_id: str = ""
    freshness: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "sources": {k: v.to_dict() for k, v in self.sources.items()},
            "jobs": [j.to_dict() for j in self.jobs],
            "warnings": list(self.warnings),
            "trace_id": self.trace_id,
            "freshness": self.freshness,
            "quality": {k: round(v, 3) for k, v in self.quality.items()},
        }


class CareerAcquisitionService:
    """Composition root for career source acquisition."""

    def __init__(
        self,
        *,
        adapters: Iterable[CareerSourceAdapter] = (),
        policy_gate: SourcePolicyGate | None = None,
        transport_selector: TransportSelector | None = None,
        health_service: SourceHealthService | None = None,
        quality_evaluator: ExtractionQualityEvaluator | None = None,
        auth_detector: AuthenticationDetector | None = None,
    ) -> None:
        self._adapters: dict[str, CareerSourceAdapter] = {
            a.source_id: a for a in adapters
        }
        self._policy_gate = policy_gate or build_default_gate()
        self._transport = transport_selector or TransportSelector
        self._health = health_service or SourceHealthService()
        self._quality = quality_evaluator or ExtractionQualityEvaluator()
        self._auth_detector = auth_detector or build_default_detector()

    # ------------------------------------------------------------------ public
    def register_adapter(self, adapter: CareerSourceAdapter) -> None:
        self._adapters[adapter.source_id] = adapter

    def source_health(self, source_id: str) -> SourceHealthRecord:
        return self._health.snapshot(source_id)

    def source_health_all(self) -> list[SourceHealthRecord]:
        return self._health.snapshot_all()

    async def run(
        self, request: CareerSearchRequest, *, trace_id: str = ""
    ) -> AcquisitionResult:
        sources = self._resolve_sources(request)
        outcomes: dict[str, SourceOutcome] = {}
        all_jobs: list[NormalizedJob] = []
        warnings: list[str] = []

        # Run sources concurrently with bounded concurrency.
        sem = asyncio.Semaphore(min(4, max(1, len(sources))))

        async def _run_one(source_id: str) -> tuple[str, SourceOutcome, list[NormalizedJob]]:
            async with sem:
                outcome, jobs = await self._run_source(source_id, request)
                return source_id, outcome, jobs

        coros = [_run_one(s) for s in sources]
        results = await asyncio.gather(*coros, return_exceptions=True)
        for r in results:
            if isinstance(r, BaseException):
                warnings.append(f"gather_failure:{r!r}")
                continue
            sid, outcome, jobs = r
            outcomes[sid] = outcome
            all_jobs.extend(jobs)
            if outcome.status == "BLOCKED":
                warnings.append(f"source_blocked:{sid}")
            elif outcome.status == "TIMEOUT":
                warnings.append(f"source_timeout:{sid}")
            elif outcome.status == "ERROR":
                warnings.append(f"source_error:{sid}")

        # Aggregate.
        any_success = any(
            o.status in ("SUCCESS", "PARTIAL_SUCCESS") for o in outcomes.values()
        )
        any_blocked = any(o.status == "BLOCKED" for o in outcomes.values())
        any_failed = any(
            o.status in ("ERROR", "TIMEOUT") for o in outcomes.values()
        )
        if any_success and (any_blocked or any_failed):
            overall = "PARTIAL_SUCCESS"
        elif any_success:
            overall = "SUCCESS"
        elif all_jobs:
            overall = "PARTIAL_SUCCESS"
        else:
            overall = "EMPTY"

        # Quality aggregation.
        if all_jobs:
            avg_quality = sum(j.extraction_confidence for j in all_jobs) / len(all_jobs)
            avg_quality = round(avg_quality, 3)
        else:
            avg_quality = 0.0
        quality_summary = {
            "average_extraction_confidence": avg_quality,
            "accepted": sum(1 for j in all_jobs if j.extraction_confidence >= 0.65),
            "review": sum(
                1
                for j in all_jobs
                if 0.45 <= j.extraction_confidence < 0.65
            ),
            "rejected": sum(1 for j in all_jobs if j.extraction_confidence < 0.45),
        }

        return AcquisitionResult(
            status=overall,
            query={
                "keyword": request.keyword,
                "location": request.location,
                "work_arrangement": request.work_arrangement,
                "employment_type": request.employment_type,
                "freshness": request.freshness,
                "sources": list(sources),
                "max_results": request.max_results,
            },
            sources=outcomes,
            jobs=all_jobs,
            warnings=warnings,
            trace_id=trace_id,
            freshness={"requested": request.freshness},
            quality=quality_summary,
        )

    async def diagnose(
        self, source_id: str, *, request: CareerSearchRequest | None = None
    ) -> dict[str, Any]:
        """Return a structured diagnostic report for a single source.

        Even when the source has no registered adapter (because the
        policy blocked it or no operator has installed one), the
        report still surfaces the policy verdict so the operator can
        see why the source is unavailable.
        """

        adapter = self._adapters.get(source_id)
        source_def = (
            adapter.source_definition
            if adapter is not None
            else self._default_definition(source_id)
        )
        verdict = self._policy_gate.evaluate(
            source_id,
            transport="API" if source_def.has_documented_api else None,
            requires_user_login=request.user_authorized if request else False,
        )
        plan = self._transport.plan(
            source_def,
            health=HealthSnapshot(is_open=False, is_degraded=False),
            cache=CacheState(fresh=False),
            requested_freshness="any",
            policy_can_api=verdict.can_use_documented_api,
            policy_can_http=verdict.can_use_static_http,
            policy_can_browser=verdict.can_use_browser,
            user_authorized=request.user_authorized if request else False,
        )
        health = self._health.snapshot(source_id)
        return {
            "source": source_id,
            "status": (
                "UNKNOWN_SOURCE" if adapter is None else "OK"
            ),
            "policy": {
                "status": verdict.status.value,
                "can_fetch": verdict.can_fetch,
                "reason": verdict.reason,
                "recommended_action": verdict.recommended_action,
            },
            "transport": {
                "primary": plan.primary.value,
                "fallback": [t.value for t in plan.fallback],
                "browser_required": plan.browser_required,
                "user_authorized_only": plan.user_authorized_only,
            },
            "session": {
                "auth_state": AuthState.UNKNOWN.value,
                "authenticated": False,
            },
            "page": {"ready": None, "reason": "diagnostic_dry_run"},
            "extraction": (
                {"fields": adapter.selector_strategy.field_names()}
                if adapter is not None
                else {"fields": []}
            ),
            "quality": {
                "score": None,
                "status": health.status,
                "failure_streak": health.failure_streak,
                "circuit": health.circuit_state,
            },
        }

    def _default_definition(self, source_id: str) -> SourceDefinition:
        """Return a minimal definition for sources without an adapter."""

        policy = self._policy_gate.get(source_id)
        return SourceDefinition(
            source_id=source_id,
            display_name=source_id,
            has_documented_api=policy.status
            in (PolicyStatus.ALLOWED, PolicyStatus.API_ONLY),
            is_static=False,
            requires_javascript=False,
            pagination_type="NONE",
        )

    # ----------------------------------------------------------------- internal
    def _resolve_sources(self, request: CareerSearchRequest) -> list[str]:
        if request.sources:
            return [s for s in request.sources if s in self._adapters]
        return sorted(self._adapters.keys())

    async def _run_source(
        self, source_id: str, request: CareerSearchRequest
    ) -> tuple[SourceOutcome, list[NormalizedJob]]:
        start = time.monotonic()
        adapter = self._adapters.get(source_id)
        if adapter is None:
            return (
                SourceOutcome(
                    source_id=source_id,
                    status="ERROR",
                    failure_taxonomy=FailureTaxonomy.NOT_SUPPORTED.value,
                    failure_reason="no_adapter_registered",
                ),
                [],
            )

        # 1. Policy gate.
        transport_choice = (
            "API"
            if adapter.source_definition.has_documented_api
            else "HTTP"
        )
        verdict = self._policy_gate.evaluate(
            source_id,
            transport=transport_choice,
            requires_user_login=request.user_authorized,
        )
        if not verdict.can_fetch:
            taxonomy = FailureTaxonomy.POLICY_BLOCKED
            if verdict.status == PolicyStatus.UNKNOWN:
                taxonomy = FailureTaxonomy.UNKNOWN_ERROR
            if verdict.status == PolicyStatus.USER_AUTHORIZED_ONLY:
                taxonomy = FailureTaxonomy.AUTH_REQUIRED
            classification = FailureClassifier.from_taxonomy(taxonomy)
            self._health.record_failure(
                source_id, taxonomy=classification.taxonomy.value, reason=verdict.reason
            )
            return (
                SourceOutcome(
                    source_id=source_id,
                    status="BLOCKED",
                    failure_taxonomy=classification.taxonomy.value,
                    failure_reason=verdict.reason,
                    elapsed_ms=(time.monotonic() - start) * 1000.0,
                ),
                [],
            )

        # 2. Fetch + parse.
        try:
            candidates = await adapter.fetch_listing_page(request, page_index=1)
        except asyncio.TimeoutError:
            self._health.record_failure(
                source_id, taxonomy=FailureTaxonomy.TIMEOUT.value
            )
            return (
                SourceOutcome(
                    source_id=source_id,
                    status="TIMEOUT",
                    failure_taxonomy=FailureTaxonomy.TIMEOUT.value,
                    elapsed_ms=(time.monotonic() - start) * 1000.0,
                ),
                [],
            )
        except Exception as exc:
            classification = FailureClassifier.from_exception(exc)
            self._health.record_failure(
                source_id,
                taxonomy=classification.taxonomy.value,
                reason=str(exc),
            )
            return (
                SourceOutcome(
                    source_id=source_id,
                    status="ERROR",
                    failure_taxonomy=classification.taxonomy.value,
                    failure_reason=str(exc),
                    elapsed_ms=(time.monotonic() - start) * 1000.0,
                ),
                [],
            )

        # 3. Detail enrichment (best-effort).
        enriched: list[NormalizedJob] = []
        quality_scores: list[float] = []
        for cand in candidates[: request.max_results]:
            detail: JobDetail | None = None
            try:
                detail = await adapter.fetch_job_detail(cand)
            except Exception:
                detail = None
            try:
                job = adapter.normalize(cand, detail)
            except Exception:
                continue
            verdict_q = self._quality.evaluate(job.to_dict())
            # Stamp the verdict onto the job record via field_confidence.
            job_dict = job.to_dict()
            job_dict["field_confidence"] = {
                **verdict_q.field_confidence,
                "_quality_score": verdict_q.score,
            }
            quality_scores.append(verdict_q.score)
            # Replace confidence with quality score for downstream ranking.
            job_with_q = NormalizedJob(
                id=job.id,
                source=job.source,
                source_job_id=job.source_job_id,
                title=job.title,
                company=job.company,
                company_id=job.company_id,
                location=job.location,
                country=job.country,
                work_arrangement=job.work_arrangement,
                employment_type=job.employment_type,
                experience_level=job.experience_level,
                salary=job.salary,
                salary_currency=job.salary_currency,
                description=job.description,
                requirements=job.requirements,
                responsibilities=job.responsibilities,
                benefits=job.benefits,
                skills=job.skills,
                posted_at=job.posted_at,
                deadline=job.deadline,
                url=job.url,
                canonical_url=job.canonical_url,
                application_url=job.application_url,
                source_status=job.source_status,
                fetched_at=job.fetched_at,
                discovered_at=job.discovered_at,
                updated_at=job.updated_at,
                content_hash=job.content_hash,
                raw_fingerprint=job.raw_fingerprint,
                extraction_method=job.extraction_method,
                extraction_confidence=verdict_q.score,
                field_confidence=job.field_confidence,
                provenance=job.provenance,
                parser_version=job.parser_version,
            )
            enriched.append(job_with_q)

        # 4. Source health update.
        elapsed = (time.monotonic() - start) * 1000.0
        if enriched:
            avg_q = sum(quality_scores) / max(1, len(quality_scores))
            self._health.record_success(
                source_id,
                records=len(enriched),
                latency_ms=elapsed,
                parser_version=adapter.source_definition.parser_version,
            )
            status = "PARTIAL_SUCCESS" if avg_q < 0.65 else "SUCCESS"
        else:
            self._health.record_failure(
                source_id,
                taxonomy=FailureTaxonomy.EMPTY_RESULT.value,
                reason="no_candidates_returned",
            )
            status = "EMPTY"

        outcome = SourceOutcome(
            source_id=source_id,
            status=status,
            count=len(enriched),
            elapsed_ms=elapsed,
        )
        return outcome, enriched
