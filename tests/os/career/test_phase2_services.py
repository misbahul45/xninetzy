from __future__ import annotations

from datetime import datetime, timezone


def test_country_normalizer_maps_iso_aliases():
    from xninetzy.domains.career.services.country_normalizer import normalize_location

    for raw, expected in (
        ("ID", "ID"),
        ("id", "ID"),
        ("Indonesia", "ID"),
        ("indonesia", "ID"),
        ("USA", "US"),
        ("United States", "US"),
        ("SG", "SG"),
        ("Singapore", "SG"),
    ):
        result = normalize_location(raw, identifiers={})
        assert result.country_code == expected, f"{raw} -> {result.country_code}"


def test_country_normalizer_returns_empty_for_unknown():
    from xninetzy.domains.career.services.country_normalizer import normalize_location

    result = normalize_location("Atlantis", identifiers={})
    assert result.country_code == ""


def test_country_normalizer_infers_region_from_country_code():
    from xninetzy.domains.career.services.country_normalizer import normalize_location

    assert normalize_location("ID", identifiers={}).region == "apac"
    assert normalize_location("US", identifiers={}).region == "americas"
    assert normalize_location("DE", identifiers={}).region == "emea"


def test_country_normalizer_detects_remote_from_text():
    from xninetzy.domains.career.services.country_normalizer import normalize_location

    remote_text = normalize_location("Remote", identifiers={})
    assert remote_text.is_remote is True


def test_country_normalizer_detects_remote_from_identifiers():
    from xninetzy.domains.career.services.country_normalizer import normalize_location

    explicit = normalize_location("anywhere", identifiers={"remote": "1"})
    assert explicit.is_remote is True


def test_country_normalizer_office_when_no_remote_signal():
    from xninetzy.domains.career.services.country_normalizer import normalize_location

    onsite = normalize_location("Berlin", identifiers={"remote": "0"})
    assert onsite.is_remote is False


def test_job_quality_scorer_returns_score_in_unit_interval():
    from xninetzy.os.research.sources.base import (
        SourceRecord,
        make_retrieved_at,
    )
    from xninetzy.domains.career.services.job_quality_scorer import score_quality

    record = SourceRecord(
        title="Senior Backend Engineer",
        url="https://remoteok.com/jobs/123",
        source="remoteok",
        source_type="job",
        published_at="2026-09-20T00:00:00+00:00",
        updated_at="2026-09-20T00:00:00+00:00",
        author="Acme",
        snippet="Python, FastAPI, PostgreSQL, Docker, Kubernetes. " * 5,
        content=None,
        language="en",
        license=None,
        retrieved_at=make_retrieved_at(),
        confidence=0.8,
        primary_source=True,
        citation=None,
        identifiers={"remoteok_id": "123"},
    )
    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    score = score_quality(record, now)
    assert 0.0 <= score <= 1.0
    assert score > 0.5, "fresh + complete + reputable source should score > 0.5"


def test_job_quality_scorer_penalizes_stale_postings():
    from xninetzy.os.research.sources.base import SourceRecord, make_retrieved_at
    from xninetzy.domains.career.services.job_quality_scorer import score_quality

    base_kwargs = dict(
        title="Backend Engineer",
        url="https://example.com/jobs/1",
        source="remoteok",
        source_type="job",
        updated_at="2026-01-01T00:00:00+00:00",
        author="Acme",
        snippet="x" * 200,
        content=None,
        language="en",
        license=None,
        retrieved_at=make_retrieved_at(),
        confidence=0.7,
        primary_source=True,
        citation=None,
        identifiers={},
    )
    fresh = SourceRecord(**{**base_kwargs, "published_at": "2026-09-25T00:00:00+00:00"})
    stale = SourceRecord(**{**base_kwargs, "published_at": "2026-01-01T00:00:00+00:00"})
    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    assert score_quality(fresh, now) > score_quality(stale, now)


def test_job_quality_scorer_penalizes_short_snippets():
    from xninetzy.os.research.sources.base import SourceRecord, make_retrieved_at
    from xninetzy.domains.career.services.job_quality_scorer import score_quality

    base_kwargs = dict(
        title="Backend Engineer",
        url="https://remoteok.com/jobs/9",
        source="remoteok",
        source_type="job",
        published_at="2026-09-25T00:00:00+00:00",
        updated_at="2026-09-25T00:00:00+00:00",
        author="Acme",
        content=None,
        language="en",
        license=None,
        retrieved_at=make_retrieved_at(),
        confidence=0.7,
        primary_source=True,
        citation=None,
        identifiers={},
    )
    detailed = SourceRecord(**{**base_kwargs, "snippet": "Python FastAPI Docker " * 20})
    sparse = SourceRecord(**{**base_kwargs, "snippet": ""})
    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    assert score_quality(detailed, now) > score_quality(sparse, now)


def test_job_quality_scorer_clamps_to_unit_interval():
    from xninetzy.os.research.sources.base import SourceRecord, make_retrieved_at
    from xninetzy.domains.career.services.job_quality_scorer import score_quality

    record = SourceRecord(
        title="x",
        url="not-a-url",
        source="unknown_source",
        source_type="job",
        published_at=None,
        updated_at=None,
        author=None,
        snippet="",
        content=None,
        language="en",
        license=None,
        retrieved_at=make_retrieved_at(),
        confidence=2.0,
        primary_source=False,
        citation=None,
        identifiers={},
    )
    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    score = score_quality(record, now)
    assert 0.0 <= score <= 1.0


def test_career_search_jobs_output_includes_quality_and_location_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "search.sqlite3"))
    from xninetzy.core.config import get_settings

    get_settings.cache_clear()

    from xninetzy.tools.ecosystem.career_tools import career_search_jobs

    raw = career_search_jobs.func(
        query="backend",
        country="",
        work_mode="any",
        posted_within_days=0,
        limit=5,
        posting_id="",
        plan_id="",
        step_id="",
        chat_id="system",
        sender_id="",
        idempotency_key="",
    )
    import json

    payload = json.loads(json.loads(raw)["summary"])
    assert payload["status"] == "ok"
    if payload["results"]:
        first = payload["results"][0]
        assert "quality_score" in first, "career_search_jobs must annotate quality_score"
        assert "location_normalized" in first, "career_search_jobs must include location_normalized"
        loc = first["location_normalized"]
        assert "country_code" in loc
        assert "is_remote" in loc
        assert "region" in loc
    get_settings.cache_clear()