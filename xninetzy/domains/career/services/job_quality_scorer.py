from __future__ import annotations

from datetime import datetime, timezone

from xninetzy.os.research.sources.base import SourceRecord


_SOURCE_RELIABILITY: dict[str, float] = {
    "remoteok": 0.85,
    "arbeitnow": 0.80,
}

_FRESHNESS_WEIGHT = 0.3
_COMPLETENESS_WEIGHT = 0.3
_SOURCE_WEIGHT = 0.2
_URL_WEIGHT = 0.1
_CONFIDENCE_WEIGHT = 0.1


def score_quality(record: SourceRecord, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    freshness = _freshness_score(record.published_at, now)
    completeness = _completeness_score(record)
    source_rel = _SOURCE_RELIABILITY.get(record.source, 0.5)
    url_valid = 1.0 if str(record.url).startswith(("http://", "https://")) else 0.0
    confidence = max(0.0, min(1.0, float(record.confidence)))
    raw = (
        freshness * _FRESHNESS_WEIGHT
        + completeness * _COMPLETENESS_WEIGHT
        + source_rel * _SOURCE_WEIGHT
        + url_valid * _URL_WEIGHT
        + confidence * _CONFIDENCE_WEIGHT
    )
    return max(0.0, min(1.0, raw))


def _freshness_score(published_at: str | None, now: datetime) -> float:
    if not published_at:
        return 0.3
    parsed = _parse_iso(published_at)
    if parsed is None:
        return 0.3
    age_days = (now - parsed).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    if age_days >= 90:
        return 0.0
    return max(0.0, 1.0 - age_days / 90.0)


def _completeness_score(record: SourceRecord) -> float:
    score = 0.0
    if record.title.strip():
        score += 0.25
    if record.author and record.author.strip():
        score += 0.25
    snippet_len = len(record.snippet or "")
    if snippet_len >= 600:
        score += 0.5
    elif snippet_len >= 200:
        score += 0.3
    elif snippet_len > 0:
        score += 0.1
    return min(1.0, score)


def _parse_iso(value: str | int | float | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, TypeError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed