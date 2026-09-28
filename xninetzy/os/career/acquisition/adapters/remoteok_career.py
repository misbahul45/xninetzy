"""RemoteOK reference adapter — career-domain wrapper.

This adapter demonstrates the canonical career acquisition flow on top of
RemoteOK's public JSON API. It reuses the existing
``xninetzy.os.research.sources.remoteok.RemoteOkAdapter`` for raw
fetching (rate limit, retry, circuit breaker) and wraps its output in
the ``CareerSourceAdapter`` Protocol.

Other adapters (Arbeitnow, Kalibrr-API, etc.) follow the same shape.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from xninetzy.core.logging import logging
from xninetzy.os.career.acquisition.adapter import (
    JobDetail,
    ListingCandidate,
    NormalizedJob,
)
from xninetzy.os.career.acquisition.extraction import (
    SelectorCandidate,
    SelectorChain,
    SelectorStrategy,
)
from xninetzy.os.career.acquisition.transport_selector import SourceDefinition
from xninetzy.os.research.sources.remoteok import RemoteOkAdapter


logger = logging.getLogger(__name__)


def _stable_fingerprint(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RemoteOkCareerAdapter:
    """Career adapter that wraps the existing RemoteOK research adapter."""

    source_id: str = "remoteok"
    _inner: RemoteOkAdapter = None  # type: ignore[assignment]
    _strategy: SelectorStrategy = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self._inner is None:
            self._inner = RemoteOkAdapter()
        if self._strategy is None:
            self._strategy = SelectorStrategy()
            self._strategy.add(
                SelectorChain(
                    field_name="title",
                    candidates=(
                        SelectorCandidate(selector="position", note="api_field"),
                        SelectorCandidate(selector="title", note="alt_field"),
                    ),
                )
            )
            self._strategy.add(
                SelectorChain(
                    field_name="company",
                    candidates=(
                        SelectorCandidate(selector="company", note="api_field"),
                    ),
                )
            )
            self._strategy.add(
                SelectorChain(
                    field_name="location",
                    candidates=(
                        SelectorCandidate(selector="location", note="api_field"),
                    ),
                )
            )
            self._strategy.add(
                SelectorChain(
                    field_name="url",
                    candidates=(
                        SelectorCandidate(
                            selector="url", attribute="href", note="api_field"
                        ),
                        SelectorCandidate(selector="apply_url", note="api_field"),
                    ),
                )
            )

    @property
    def inner(self) -> RemoteOkAdapter:
        return self._inner

    @property
    def source_definition(self) -> SourceDefinition:
        return SourceDefinition(
            source_id=self.source_id,
            display_name="RemoteOK",
            domains=("remoteok.com",),
            country="GLOBAL",
            policy_status="ALLOWED",
            has_documented_api=True,
            is_static=True,
            requires_javascript=False,
            detail_pages_supported=False,
            search_supported=True,
            pagination_type="API_CURSOR",
            rate_limit_rpm=10,
            parser_version="1.0",
            notes="Public JSON API at /api",
        )

    @property
    def selector_strategy(self) -> SelectorStrategy:
        return self._strategy

    async def fetch_listing_page(
        self, request: Any, *, page_index: int = 1
    ) -> list[ListingCandidate]:
        # Reuse the existing adapter. RemoteOK returns the entire feed;
        # pagination is implicit.
        try:
            records = await self._inner.search(
                query=request.keyword, limit=max(1, min(100, request.max_results))
            )
        except Exception as exc:
            logger.warning("remoteok career fetch failed: %s", exc)
            return []
        out: list[ListingCandidate] = []
        for rec in records:
            remoteok_id = rec.identifiers.get("remoteok_id") or rec.url.rsplit(
                "/", 1
            )[-1]
            url = rec.url
            canonical = (
                f"https://remoteok.com/remote-jobs/{remoteok_id}"
                if remoteok_id
                else url
            )
            cand = ListingCandidate(
                source_id=self.source_id,
                source_job_id=remoteok_id or url,
                url=url,
                canonical_url=canonical,
                title=rec.title,
                company=rec.author,
                location=None,
                posted_at=rec.published_at,
                work_arrangement="REMOTE",
                snippet=rec.snippet,
                raw_fingerprint=_stable_fingerprint(
                    self.source_id, remoteok_id or url
                ),
            )
            out.append(cand)
        return out

    async def fetch_job_detail(
        self, candidate: ListingCandidate
    ) -> JobDetail | None:
        # RemoteOK listing payload is essentially the entire record; treat
        # the listing snippet as the description.
        return JobDetail(
            source_job_id=candidate.source_job_id,
            description=candidate.snippet,
            requirements=(),
            responsibilities=(),
            benefits=(),
            skills=tuple(
                filter(
                    None,
                    [
                        t.strip()
                        for t in (
                            self._extract_tags_from_snippet(candidate.snippet or "")
                        )
                    ],
                )
            ),
            salary=None,
            salary_currency=None,
            deadline=None,
            application_url=candidate.url,
        )

    @staticmethod
    def _extract_tags_from_snippet(snippet: str) -> list[str]:
        # The career adapter does not parse HTML here; the snippet is plain
        # text. Tags are surfaced via the upstream adapter's identifiers.
        return []

    def normalize(
        self,
        candidate: ListingCandidate,
        detail: JobDetail | None,
    ) -> NormalizedJob:
        now = _now_iso()
        description = (detail.description if detail else None) or candidate.snippet
        skills = detail.skills if detail else ()
        content = "|".join(
            [
                candidate.title,
                candidate.company or "",
                candidate.location or "",
                description or "",
            ]
        )
        content_hash = _stable_fingerprint(content)
        return NormalizedJob(
            id=f"{self.source_id}:{candidate.source_job_id}",
            source=self.source_id,
            source_job_id=candidate.source_job_id,
            title=candidate.title,
            company=candidate.company,
            company_id=None,
            location=candidate.location,
            country=None,
            work_arrangement=candidate.work_arrangement or "REMOTE",
            employment_type="UNKNOWN",
            experience_level="UNKNOWN",
            salary=None,
            salary_currency=None,
            description=description,
            requirements=(),
            responsibilities=(),
            benefits=(),
            skills=skills,
            posted_at=candidate.posted_at,
            deadline=None,
            url=candidate.url,
            canonical_url=candidate.canonical_url,
            application_url=detail.application_url if detail else candidate.url,
            source_status="LISTING",
            fetched_at=now,
            discovered_at=now,
            updated_at=now,
            content_hash=content_hash,
            raw_fingerprint=candidate.raw_fingerprint or content_hash,
            extraction_method="API",
            extraction_confidence=0.85,
            field_confidence={},
            provenance={},
            parser_version=self.source_definition.parser_version,
        )


def build_remoteok_career_adapter() -> RemoteOkCareerAdapter:
    return RemoteOkCareerAdapter()
