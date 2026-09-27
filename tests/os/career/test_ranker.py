from __future__ import annotations

from datetime import datetime, timezone


def _record(**overrides) -> dict:
    base = {
        "id": "x",
        "title": "Backend Engineer",
        "company": "Acme",
        "url": "https://example.com",
        "source": "test",
        "posted_at": "2026-09-25T00:00:00+00:00",
        "snippet": "Python FastAPI",
        "identifiers": {},
        "quality_score": 0.6,
        "location_normalized": {
            "country_code": "ID",
            "region": "apac",
            "is_remote": False,
        },
    }
    base.update(overrides)
    return base


def test_score_record_components_in_unit_interval():
    from xninetzy.domains.career.services import score_record

    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    score = score_record(
        _record(),
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    for name in ("quality", "freshness", "relevance", "location_match", "work_mode_match", "total"):
        value = getattr(score, name)
        assert 0.0 <= value <= 1.0, f"{name}={value}"


def test_score_record_prefers_recent_postings():
    from xninetzy.domains.career.services import score_record

    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    fresh = score_record(
        _record(posted_at="2026-09-25T00:00:00+00:00"),
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    stale = score_record(
        _record(posted_at="2026-03-01T00:00:00+00:00"),
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    assert fresh.total > stale.total


def test_score_record_prefers_relevant_titles():
    from xninetzy.domains.career.services import score_record

    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    match = score_record(
        _record(title="Backend Engineer"),
        intent_terms=("backend", "engineer"),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    miss = score_record(
        _record(title="Marketing Manager", snippet="advertising sales"),
        intent_terms=("backend", "engineer"),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    assert match.total > miss.total


def test_score_record_matches_country_when_intent_country_given():
    from xninetzy.domains.career.services import score_record

    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    matched = score_record(
        _record(location_normalized={"country_code": "ID", "region": "apac", "is_remote": False}),
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    unmatched = score_record(
        _record(location_normalized={"country_code": "US", "region": "americas", "is_remote": False}),
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    assert matched.total > unmatched.total


def test_score_record_rewards_remote_when_intent_remote():
    from xninetzy.domains.career.services import score_record

    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    remote = score_record(
        _record(location_normalized={"country_code": "ID", "region": "apac", "is_remote": True}),
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="remote",
        now=now,
    )
    onsite = score_record(
        _record(location_normalized={"country_code": "ID", "region": "apac", "is_remote": False}),
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="remote",
        now=now,
    )
    assert remote.total > onsite.total


def test_rank_records_sorts_descending_by_total_score():
    from xninetzy.domains.career.services import rank_records

    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    records = [
        _record(id="low", title="Marketing", quality_score=0.2, posted_at="2025-01-01T00:00:00+00:00"),
        _record(id="hi", title="Backend Engineer", quality_score=0.95, posted_at="2026-09-26T00:00:00+00:00"),
        _record(id="mid", title="Backend Developer", quality_score=0.7, posted_at="2026-09-20T00:00:00+00:00"),
    ]
    ranked = rank_records(
        records,
        intent_terms=("backend", "engineer"),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    assert [r["id"] for r in ranked] == ["hi", "mid", "low"]
    assert all("rank_score" in r and "total" in r["rank_score"] for r in ranked)


def test_rank_records_includes_explainable_breakdown():
    from xninetzy.domains.career.services import rank_records

    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    ranked = rank_records(
        [_record()],
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="any",
        now=now,
    )
    score = ranked[0]["rank_score"]
    for dimension in ("quality", "freshness", "relevance", "location_match", "work_mode_match", "total"):
        assert dimension in score
        assert 0.0 <= score[dimension] <= 1.0


def test_rank_records_handles_empty_list():
    from xninetzy.domains.career.services import rank_records

    assert rank_records([], intent_terms=(), intent_country="", intent_work_mode="") == []


def test_score_record_clamps_missing_quality_score():
    from xninetzy.domains.career.services import score_record

    record = _record()
    record.pop("quality_score")
    score = score_record(
        record,
        intent_terms=("backend",),
        intent_country="ID",
        intent_work_mode="any",
    )
    assert 0.0 <= score.total <= 1.0


def test_rank_records_preserves_input_count():
    from xninetzy.domains.career.services import rank_records

    now = datetime(2026, 9, 27, tzinfo=timezone.utc)
    records = [_record(id=f"r{i}") for i in range(7)]
    ranked = rank_records(
        records,
        intent_terms=(),
        intent_country="",
        intent_work_mode="any",
        now=now,
    )
    assert len(ranked) == 7
