"""Test extraction quality evaluator."""

from __future__ import annotations

from xninetzy.os.career.acquisition.quality import ExtractionQualityEvaluator


def _full_record() -> dict:
    return {
        "title": "Senior Software Engineer",
        "company": "Acme",
        "url": "https://example.com/jobs/123",
        "location": "Jakarta, ID",
        "description": "We are looking for a senior engineer to join our platform team...",
        "posted_at": "2026-09-25",
        "salary": "Rp 30,000,000",
        "skills": ["python", "fastapi"],
    }


def test_full_record_scores_high() -> None:
    verdict = ExtractionQualityEvaluator().evaluate(_full_record())
    assert verdict.score > 0.65
    assert verdict.recommended_action == "ACCEPT"
    assert not verdict.warnings


def test_missing_company_warns_and_lowers_score() -> None:
    record = _full_record()
    record["company"] = None
    verdict = ExtractionQualityEvaluator().evaluate(record)
    assert "MISSING_COMPANY" in verdict.warnings
    assert verdict.score < 0.85


def test_invalid_url_warns() -> None:
    record = _full_record()
    record["url"] = "not-a-url"
    verdict = ExtractionQualityEvaluator().evaluate(record)
    assert "INVALID_URL" in verdict.warnings


def test_short_description_warns() -> None:
    record = _full_record()
    record["description"] = "short"
    verdict = ExtractionQualityEvaluator().evaluate(record)
    assert "EMPTY_DESCRIPTION" in verdict.warnings


def test_empty_record_rejected() -> None:
    verdict = ExtractionQualityEvaluator().evaluate({})
    assert verdict.recommended_action == "REJECT"
    assert verdict.score < 0.45


def test_review_band() -> None:
    record = _full_record()
    record["description"] = ""
    record["salary"] = None
    record["posted_at"] = None
    verdict = ExtractionQualityEvaluator().evaluate(record)
    assert verdict.recommended_action in {"REVIEW", "REJECT"}
