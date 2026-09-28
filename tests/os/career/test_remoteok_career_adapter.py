"""Test RemoteOK career adapter against fixtures."""

from __future__ import annotations

from xninetzy.os.career.acquisition.adapters.remoteok_career import (
    RemoteOkCareerAdapter,
)


def _load_fixture() -> dict:
    from pathlib import Path
    import json

    p = Path(__file__).parent / "fixtures/career_sources/remoteok/sample_record_1.json"
    return json.loads(p.read_text())


def test_normalize_minimal_record() -> None:
    adapter = RemoteOkCareerAdapter()
    rec = _load_fixture()
    # We bypass fetch_listing_page and exercise normalize + detail shape.
    from xninetzy.os.career.acquisition.adapter import (
        JobDetail,
        ListingCandidate,
    )

    cand = ListingCandidate(
        source_id="remoteok",
        source_job_id=str(rec["id"]),
        url=rec["url"],
        canonical_url=f"https://remoteok.com/remote-jobs/{rec['id']}",
        title=rec["position"],
        company=rec["company"],
        location=None,
        posted_at=rec["date"],
        work_arrangement="REMOTE",
        snippet=rec["description"],
        raw_fingerprint="remoteok-1",
    )
    detail = JobDetail(
        source_job_id=str(rec["id"]),
        description=rec["description"],
        application_url=rec["apply_url"],
    )
    job = adapter.normalize(cand, detail)
    d = job.to_dict()
    assert d["source"] == "remoteok"
    assert d["source_job_id"] == "1"
    assert d["title"] == "Senior Python Developer"
    assert d["company"] == "Acme Corp"
    assert d["work_arrangement"] == "REMOTE"
    assert d["application_url"] == "https://acme.com/apply/1"
    assert d["content_hash"]  # non-empty


def test_selector_strategy_lists_required_fields() -> None:
    adapter = RemoteOkCareerAdapter()
    fields = adapter.selector_strategy.field_names()
    assert {"title", "company", "url"}.issubset(set(fields))
