"""Selector strategy + extraction quality evaluation.

Brief mandates ordered fallback chains per field. This module defines:

- ``SelectorChain``: ordered list of selector candidates with provenance.
- ``SelectorStrategy``: a collection of chains keyed by field name.
- ``FieldProvenance``: the resolved (selector used, confidence) pair.
- ``ExtractionQualityEvaluator``: scores a normalized record.

Adapters populate ``SelectorStrategy`` at construction time. The
extractor tries the first selector, then iterates until a non-empty
result is produced. The chosen selector is recorded for telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SelectorCandidate:
    selector: str
    attribute: str | None = None  # when extracting an attribute (e.g. "href")
    note: str = ""


@dataclass(frozen=True)
class SelectorChain:
    field_name: str
    candidates: tuple[SelectorCandidate, ...]

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError(
                f"SelectorChain[{self.field_name}] must declare ≥1 candidate"
            )


@dataclass
class FieldProvenance:
    field_name: str
    value: Any
    selected_selector: str | None
    candidate_index: int
    confidence: float
    extraction_method: str  # "DOM" | "JSON-LD" | "API" | "SEMANTIC" | "TEXT"
    fallback_used: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "selected_selector": self.selected_selector,
            "candidate_index": self.candidate_index,
            "confidence": round(self.confidence, 3),
            "extraction_method": self.extraction_method,
            "fallback_used": self.fallback_used,
        }


@dataclass
class SelectorStrategy:
    """Per-source ordered selector chains."""

    chains: dict[str, SelectorChain] = field(default_factory=dict)

    def add(self, chain: SelectorChain) -> None:
        self.chains[chain.field_name] = chain

    def get(self, field_name: str) -> SelectorChain | None:
        return self.chains.get(field_name)

    def field_names(self) -> list[str]:
        return sorted(self.chains.keys())


@dataclass
class _ResolveCallable:
    pass  # placeholder; real signatures are duck-typed below


# Duck-typed resolver signature:
#   async (selector: str, page: Any) -> Optional[str]
Resolver = Any


class SelectorExtractor:
    """Resolve fields via ordered selectors and emit provenance.

    The extractor is intentionally minimal: it does not know about the
    page type. Adapters provide a ``resolve`` callable that maps a
    selector → extracted text or attribute value.
    """

    def __init__(self, strategy: SelectorStrategy) -> None:
        self.strategy = strategy

    async def extract(
        self,
        field_name: str,
        page: Any,
        resolver: Resolver,
        *,
        extraction_method: str = "DOM",
        confidence_floor: float = 0.0,
    ) -> FieldProvenance | None:
        chain = self.strategy.get(field_name)
        if chain is None:
            return None
        for idx, cand in enumerate(chain.candidates):
            try:
                value = await resolver(cand.selector, page)
            except Exception:
                value = None
            if value is None:
                continue
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    continue
            fallback_used = idx > 0
            confidence = max(
                confidence_floor, 0.99 - (0.05 * idx)
            )
            return FieldProvenance(
                field_name=field_name,
                value=value,
                selected_selector=cand.selector,
                candidate_index=idx,
                confidence=confidence,
                extraction_method=extraction_method,
                fallback_used=fallback_used,
            )
        return None
