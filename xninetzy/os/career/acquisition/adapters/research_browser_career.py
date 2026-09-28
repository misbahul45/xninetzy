"""Generic wrapper: research BrowserScrapingAdapter -> CareerSourceAdapter."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from xninetzy.os.career.acquisition.adapter import (
    JobDetail, ListingCandidate, NormalizedJob,
)
from xninetzy.os.career.acquisition.extraction import (
    SelectorCandidate, SelectorChain, SelectorStrategy,
)
from xninetzy.os.career.acquisition.transport_selector import SourceDefinition
from xninetzy.os.research.sources.base import SourceAdapter
from xninetzy.os.research.sources.registry import get_adapter as _get_research_adapter


def _fp(*p):
    return hashlib.sha256("|".join(p).encode()).hexdigest()[:32]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _strategy_for(source_id):
    s = SelectorStrategy()
    for f in ("title", "company", "location", "url"):
        s.add(SelectorChain(f, (SelectorCandidate(f, note="research_field"),)))
    return s


@dataclass
class ResearchBrowserCareerAdapter:
    source_id: str
    country: str = "ID"
    _inner: SourceAdapter = None
    _strategy: SelectorStrategy = None

    def __post_init__(self):
        if self._inner is None:
            self._inner = _get_research_adapter(self.source_id)
        if self._strategy is None:
            self._strategy = _strategy_for(self.source_id)

    @property
    def inner(self):
        return self._inner

    @property
    def source_definition(self):
        return SourceDefinition(
            source_id=self.source_id,
            display_name=self.source_id.title(),
            country=self.country,
            policy_status="API_ONLY",
            has_documented_api=True,
            is_static=False,
            requires_javascript=True,
            detail_pages_supported=False,
            search_supported=True,
            pagination_type="INFINITE_SCROLL",
            rate_limit_rpm=4,
            parser_version="1.0",
            notes=f"Career wrapper over research BrowserScrapingAdapter:{self.source_id}",
        )

    @property
    def selector_strategy(self):
        return self._strategy

    async def fetch_listing_page(self, request, *, page_index=1):
        if self._inner is None:
            return []
        try:
            records = await self._inner.search(
                query=request.keyword,
                limit=max(1, min(100, request.max_results)),
            )
        except Exception:
            return []
        out = []
        for r in records:
            sid = ((r.identifiers or {}).get(f"{self.source_id}_slug")
                   or r.url.rsplit("/", 1)[-1] or r.url)
            loc = (r.identifiers or {}).get("location")
            cand = ListingCandidate(
                source_id=self.source_id,
                source_job_id=sid,
                url=r.url,
                canonical_url=r.url,
                title=r.title,
                company=r.author,
                location=loc,
                posted_at=r.published_at,
                work_arrangement="HYBRID",
                snippet=r.snippet,
                raw_fingerprint=_fp(self.source_id, sid),
            )
            out.append(cand)
        return out

    async def fetch_job_detail(self, candidate):
        return JobDetail(
            source_job_id=candidate.source_job_id,
            description=candidate.snippet,
            application_url=candidate.url,
        )

    def normalize(self, candidate, detail):
        now = _now()
        desc = (detail.description if detail else None) or candidate.snippet
        content = "|".join([candidate.title, candidate.company or "",
                            candidate.location or "", desc or ""])
        ch = _fp(content)
        title_lower = (candidate.title or "").lower()
        is_intern = "intern" in title_lower or "magang" in title_lower
        return NormalizedJob(
            id=f"{self.source_id}:{candidate.source_job_id}",
            source=self.source_id,
            source_job_id=candidate.source_job_id,
            title=candidate.title,
            company=candidate.company,
            company_id=None,
            location=candidate.location,
            country=self.country,
            work_arrangement=candidate.work_arrangement or "HYBRID",
            employment_type="INTERN" if is_intern else "FULLTIME",
            experience_level="INTERN" if is_intern else "UNKNOWN",
            salary=None, salary_currency=None,
            description=desc,
            requirements=(), responsibilities=(), benefits=(), skills=(),
            posted_at=candidate.posted_at, deadline=None,
            url=candidate.url, canonical_url=candidate.canonical_url,
            application_url=detail.application_url if detail else candidate.url,
            source_status="LISTING",
            fetched_at=now, discovered_at=now, updated_at=now,
            content_hash=ch, raw_fingerprint=candidate.raw_fingerprint or ch,
            extraction_method="BROWSER_SCRAPE",
            extraction_confidence=0.55,
            field_confidence={}, provenance={},
            parser_version=self.source_definition.parser_version,
        )


def build_research_browser_career_adapter(source_id, country="ID"):
    return ResearchBrowserCareerAdapter(source_id=source_id, country=country)
