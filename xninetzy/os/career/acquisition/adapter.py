"""Career source adapter contract + composition root.

``CareerSourceAdapter`` is a thin Protocol layered on top of the existing
``SourceAdapter`` (research adapters). Adapters implementing this
contract gain access to the structured career acquisition engine:

- policy gate enforcement
- transport selection
- failure classification
- source health updates
- extraction quality evaluation

Adapters implementing this contract MUST NOT contain their own retry /
circuit-breaker / cache logic. Those concerns live in the shared engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from xninetzy.os.career.acquisition.extraction import (
    FieldProvenance,
    SelectorStrategy,
)
from xninetzy.os.career.acquisition.transport_selector import SourceDefinition


@dataclass(frozen=True)
class ListingCandidate:
    """Listing-level record before detail enrichment.

    Required: id, url, title. Everything else is best-effort.
    """

    source_id: str
    source_job_id: str
    url: str
    title: str
    company: str | None = None
    location: str | None = None
    posted_at: str | None = None
    work_arrangement: str | None = None
    snippet: str | None = None
    canonical_url: str | None = None
    raw_fingerprint: str | None = None
    provenance: dict[str, FieldProvenance] = field(default_factory=dict)


@dataclass(frozen=True)
class JobDetail:
    """Detail-enriched record."""

    source_job_id: str
    description: str | None = None
    requirements: tuple[str, ...] = ()
    responsibilities: tuple[str, ...] = ()
    benefits: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    salary: str | None = None
    salary_currency: str | None = None
    deadline: str | None = None
    application_url: str | None = None
    provenance: dict[str, FieldProvenance] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedJob:
    """Final record exposed via MCP and persisted in the cache.

    Field set follows the brief's canonical Job model.
    """

    id: str
    source: str
    source_job_id: str
    title: str
    company: str | None
    company_id: str | None
    location: str | None
    country: str | None
    work_arrangement: str
    employment_type: str
    experience_level: str
    salary: str | None
    salary_currency: str | None
    description: str | None
    requirements: tuple[str, ...]
    responsibilities: tuple[str, ...]
    benefits: tuple[str, ...]
    skills: tuple[str, ...]
    posted_at: str | None
    deadline: str | None
    url: str
    canonical_url: str | None
    application_url: str | None
    source_status: str
    fetched_at: str
    discovered_at: str
    updated_at: str
    content_hash: str
    raw_fingerprint: str
    extraction_method: str
    extraction_confidence: float
    field_confidence: dict[str, float]
    provenance: dict[str, FieldProvenance]
    parser_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "source_job_id": self.source_job_id,
            "title": self.title,
            "company": self.company,
            "company_id": self.company_id,
            "location": self.location,
            "country": self.country,
            "work_arrangement": self.work_arrangement,
            "employment_type": self.employment_type,
            "experience_level": self.experience_level,
            "salary": self.salary,
            "salary_currency": self.salary_currency,
            "description": self.description,
            "requirements": list(self.requirements),
            "responsibilities": list(self.responsibilities),
            "benefits": list(self.benefits),
            "skills": list(self.skills),
            "posted_at": self.posted_at,
            "deadline": self.deadline,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "application_url": self.application_url,
            "source_status": self.source_status,
            "fetched_at": self.fetched_at,
            "discovered_at": self.discovered_at,
            "updated_at": self.updated_at,
            "content_hash": self.content_hash,
            "raw_fingerprint": self.raw_fingerprint,
            "extraction_method": self.extraction_method,
            "extraction_confidence": round(self.extraction_confidence, 3),
            "field_confidence": {
                k: round(v, 3) for k, v in self.field_confidence.items()
            },
            "parser_version": self.parser_version,
        }


class CareerSourceAdapter(Protocol):
    """Protocol every career source adapter implements.

    Methods intentionally minimal: each adapter owns source-specific
    semantics only. Shared resilience lives in the engine.
    """

    @property
    def source_id(self) -> str: ...

    @property
    def source_definition(self) -> SourceDefinition: ...

    @property
    def selector_strategy(self) -> SelectorStrategy: ...

    async def fetch_listing_page(
        self, request: Any, *, page_index: int = 1
    ) -> list[ListingCandidate]: ...

    async def fetch_job_detail(
        self, candidate: ListingCandidate
    ) -> JobDetail | None: ...

    def normalize(
        self,
        candidate: ListingCandidate,
        detail: JobDetail | None,
    ) -> NormalizedJob: ...
