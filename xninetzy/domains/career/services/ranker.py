from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class RankScore:
    quality: float
    freshness: float
    relevance: float
    location_match: float
    work_mode_match: float
    total: float

    def to_dict(self) -> dict[str, float]:
        return {
            "quality": round(self.quality, 4),
            "freshness": round(self.freshness, 4),
            "relevance": round(self.relevance, 4),
            "location_match": round(self.location_match, 4),
            "work_mode_match": round(self.work_mode_match, 4),
            "total": round(self.total, 4),
        }


WEIGHTS = {
    "quality": 0.3,
    "freshness": 0.2,
    "relevance": 0.3,
    "location_match": 0.1,
    "work_mode_match": 0.1,
}


def _freshness_component(published_at: str | int | None, now: datetime) -> float:
    if not published_at:
        return 0.3
    if isinstance(published_at, (int, float)):
        try:
            parsed = datetime.fromtimestamp(float(published_at), tz=timezone.utc)
        except (OverflowError, OSError, TypeError, ValueError):
            return 0.3
    elif isinstance(published_at, str):
        try:
            parsed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return 0.3
    else:
        return 0.3
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - parsed).total_seconds() / 86400.0)
    if age_days <= 0:
        return 1.0
    if age_days >= 90:
        return 0.0
    return max(0.0, 1.0 - age_days / 90.0)


def _relevance_component(title: str, snippet: str, query_terms: tuple[str, ...]) -> float:
    if not query_terms:
        return 0.5
    haystack = f"{title or ''}\n{snippet or ''}".lower()
    if not haystack.strip():
        return 0.0
    hits = sum(1 for term in query_terms if term in haystack)
    return hits / len(query_terms)


def _location_match_component(record_country: str, intent_country: str) -> float:
    if not intent_country:
        return 1.0
    if not record_country:
        return 0.4
    if record_country.upper() == intent_country.upper():
        return 1.0
    return 0.0


def _work_mode_match_component(record_is_remote: bool, intent_work_mode: str) -> float:
    if intent_work_mode == "any" or not intent_work_mode:
        return 1.0
    if intent_work_mode == "remote":
        return 1.0 if record_is_remote else 0.0
    if intent_work_mode == "onsite":
        return 0.0 if record_is_remote else 1.0
    return 0.7


def score_record(
    record: dict[str, Any],
    *,
    intent_terms: tuple[str, ...],
    intent_country: str,
    intent_work_mode: str,
    now: datetime | None = None,
) -> RankScore:
    now = now or datetime.now(timezone.utc)
    quality = float(record.get("quality_score", 0.5))
    freshness = _freshness_component(record.get("posted_at"), now)
    relevance = _relevance_component(
        record.get("title", ""), record.get("snippet", ""), intent_terms
    )
    loc_normalized = record.get("location_normalized") or {}
    location_match = _location_match_component(
        loc_normalized.get("country_code", ""), intent_country
    )
    work_mode_match = _work_mode_match_component(
        bool(loc_normalized.get("is_remote", False)), intent_work_mode
    )
    total = (
        quality * WEIGHTS["quality"]
        + freshness * WEIGHTS["freshness"]
        + relevance * WEIGHTS["relevance"]
        + location_match * WEIGHTS["location_match"]
        + work_mode_match * WEIGHTS["work_mode_match"]
    )
    return RankScore(
        quality=quality,
        freshness=freshness,
        relevance=relevance,
        location_match=location_match,
        work_mode_match=work_mode_match,
        total=total,
    )


def rank_records(
    records: list[dict[str, Any]],
    *,
    intent_terms: tuple[str, ...],
    intent_country: str,
    intent_work_mode: str,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    scored: list[tuple[RankScore, dict[str, Any]]] = []
    for record in records:
        score = score_record(
            record,
            intent_terms=intent_terms,
            intent_country=intent_country,
            intent_work_mode=intent_work_mode,
            now=now,
        )
        enriched = dict(record)
        enriched["rank_score"] = score.to_dict()
        scored.append((score, enriched))
    scored.sort(key=lambda pair: pair[0].total, reverse=True)
    return [record for _, record in scored]


__all__ = [
    "RankScore",
    "WEIGHTS",
    "rank_records",
    "score_record",
]
