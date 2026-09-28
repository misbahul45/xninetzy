"""Test CareerAcquisitionService composition root."""

from __future__ import annotations

import asyncio
from typing import Any

from xninetzy.os.career.acquisition.adapter import (
    JobDetail,
    ListingCandidate,
    NormalizedJob,
)
from xninetzy.os.career.acquisition.service import (
    CareerAcquisitionService,
    CareerSearchRequest,
)


class _FakeAdapter:
    def __init__(
        self,
        *,
        source_id: str,
        candidates: list[ListingCandidate],
        raise_exc: Exception | None = None,
    ) -> None:
        self._source_id = source_id
        self._candidates = candidates
        self._raise = raise_exc

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def source_definition(self):
        from xninetzy.os.career.acquisition import SourceDefinition

        return SourceDefinition(
            source_id=self._source_id,
            display_name=self._source_id,
            has_documented_api=True,
            is_static=True,
        )

    @property
    def selector_strategy(self):
        from xninetzy.os.career.acquisition import SelectorStrategy

        return SelectorStrategy()

    async def fetch_listing_page(self, request: Any, *, page_index: int = 1):
        if self._raise is not None:
            raise self._raise
        return list(self._candidates)

    async def fetch_job_detail(self, candidate: ListingCandidate):
        return JobDetail(source_job_id=candidate.source_job_id, description=candidate.snippet or "")

    def normalize(self, candidate: ListingCandidate, detail: JobDetail | None):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        return NormalizedJob(
            id=f"{self._source_id}:{candidate.source_job_id}",
            source=self._source_id,
            source_job_id=candidate.source_job_id,
            title=candidate.title,
            company=candidate.company,
            company_id=None,
            location=candidate.location,
            country=None,
            work_arrangement="REMOTE",
            employment_type="UNKNOWN",
            experience_level="UNKNOWN",
            salary=None,
            salary_currency=None,
            description=(detail.description if detail else None) or candidate.snippet,
            requirements=(),
            responsibilities=(),
            benefits=(),
            skills=(),
            posted_at=candidate.posted_at,
            deadline=None,
            url=candidate.url,
            canonical_url=candidate.url,
            application_url=candidate.url,
            source_status="LISTING",
            fetched_at=now,
            discovered_at=now,
            updated_at=now,
            content_hash=candidate.raw_fingerprint or candidate.source_job_id,
            raw_fingerprint=candidate.raw_fingerprint or candidate.source_job_id,
            extraction_method="API",
            extraction_confidence=0.85,
            field_confidence={},
            provenance={},
            parser_version="1.0",
        )


def _candidate(source: str, idx: int, title: str = "Engineer") -> ListingCandidate:
    return ListingCandidate(
        source_id=source,
        source_job_id=f"{source}-{idx}",
        url=f"https://example.com/{source}/{idx}",
        title=title,
        company="Acme",
        location="Jakarta",
        snippet="Senior engineer role",
        work_arrangement="REMOTE",
        raw_fingerprint=f"{source}-{idx}",
    )


def test_partial_success_when_one_source_fails() -> None:
    good = _FakeAdapter(
        source_id="remoteok",
        candidates=[_candidate("remoteok", i) for i in range(3)],
    )
    bad = _FakeAdapter(
        source_id="broken",
        candidates=[],
        raise_exc=RuntimeError("captcha required"),
    )
    blocked_adapter = _FakeAdapter(
        source_id="jobstreet_id",
        candidates=[_candidate("jobstreet_id", 1)],
    )
    from xninetzy.os.career.acquisition.policy import (
        PolicyStatus,
        SourcePolicy,
        SourcePolicyGate,
    )

    gate = SourcePolicyGate()
    gate.register(
        SourcePolicy(
            source_id="remoteok",
            status=PolicyStatus.ALLOWED,
            allowed_transports=("API",),
        )
    )
    gate.register(
        SourcePolicy(
            source_id="broken",
            status=PolicyStatus.ALLOWED,
            allowed_transports=("API",),
        )
    )
    gate.register(
        SourcePolicy(
            source_id="jobstreet_id",
            status=PolicyStatus.BLOCKED,
            allowed_transports=("API",),
        )
    )
    svc = CareerAcquisitionService(
        adapters=[good, bad, blocked_adapter],
        policy_gate=gate,
    )
    request = CareerSearchRequest(
        keyword="engineer",
        sources=("remoteok", "broken", "jobstreet_id"),
    )
    result = asyncio.run(svc.run(request))
    assert result.status in {"PARTIAL_SUCCESS", "SUCCESS"}
    assert result.sources["remoteok"].count == 3
    assert result.sources["broken"].status in {"ERROR", "TIMEOUT"}
    assert result.sources["jobstreet_id"].status == "BLOCKED"
    assert any("source_blocked" in w for w in result.warnings)


def test_empty_when_all_blocked() -> None:
    a = _FakeAdapter(source_id="jobstreet_id", candidates=[])
    svc = CareerAcquisitionService(adapters=[a])
    request = CareerSearchRequest(
        keyword="engineer", sources=("jobstreet_id",)
    )
    result = asyncio.run(svc.run(request))
    assert result.status == "EMPTY"
    assert result.sources["jobstreet_id"].status == "BLOCKED"


def test_quality_summary_includes_aggregation() -> None:
    a = _FakeAdapter(
        source_id="remoteok",
        candidates=[_candidate("remoteok", i) for i in range(2)],
    )
    svc = CareerAcquisitionService(adapters=[a])
    request = CareerSearchRequest(keyword="x", sources=("remoteok",))
    result = asyncio.run(svc.run(request))
    assert "average_extraction_confidence" in result.quality
    assert result.quality["accepted"] >= 0


def test_diagnose_returns_structured_report() -> None:
    from xninetzy.os.career.acquisition import SelectorStrategy

    class _AdapterWithStrategy(_FakeAdapter):
        @property
        def selector_strategy(self):  # type: ignore[override]
            s = SelectorStrategy()
            from xninetzy.os.career.acquisition import (
                SelectorCandidate,
                SelectorChain,
            )
            s.add(
                SelectorChain(
                    field_name="title",
                    candidates=(SelectorCandidate(selector="h1"),),
                )
            )
            return s

    a2 = _AdapterWithStrategy(
        source_id="remoteok", candidates=[]
    )
    svc = CareerAcquisitionService(adapters=[a2])
    request = CareerSearchRequest(keyword="x", sources=("remoteok",))
    report = asyncio.run(svc.diagnose("remoteok", request=request))
    assert report["source"] == "remoteok"
    assert report["policy"]["status"] == "ALLOWED"
    assert report["transport"]["primary"] == "DOCUMENTED_API"
    assert "title" in report["extraction"]["fields"]
