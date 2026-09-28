"""Test structured failure taxonomy + classifier."""

from __future__ import annotations


from xninetzy.os.career.acquisition.failures import (
    FailureClassifier,
    FailureTaxonomy,
)


def test_all_taxonomy_entries_have_classification() -> None:
    table = FailureClassifier.all()
    assert set(table.keys()) == set(FailureTaxonomy)
    for cls in table.values():
        assert cls.taxonomy in FailureTaxonomy
        assert isinstance(cls.retryable, bool)
        assert cls.severity in {"low", "medium", "high", "critical"}


def test_policy_blocked_is_non_retryable() -> None:
    cls = FailureClassifier.from_taxonomy(FailureTaxonomy.POLICY_BLOCKED)
    assert cls.retryable is False
    assert cls.recommended_action == "STOP_DO_NOT_RETRY"


def test_rate_limited_is_retryable_and_can_fallback() -> None:
    cls = FailureClassifier.from_taxonomy(FailureTaxonomy.RATE_LIMITED)
    assert cls.retryable is True
    assert cls.fallback_allowed is True


def test_captcha_required_is_non_retryable() -> None:
    cls = FailureClassifier.from_taxonomy(FailureTaxonomy.CAPTCHA_REQUIRED)
    assert cls.retryable is False
    assert "NEVER_BYPASS_CAPTCHA" in cls.recommended_action


def test_http_status_classification() -> None:
    assert FailureClassifier.from_http_status(200).taxonomy in FailureTaxonomy
    assert FailureClassifier.from_http_status(401).taxonomy == FailureTaxonomy.AUTH_REQUIRED
    assert FailureClassifier.from_http_status(429).taxonomy == FailureTaxonomy.RATE_LIMITED
    assert FailureClassifier.from_http_status(503).taxonomy == FailureTaxonomy.HTTP_5XX
    assert FailureClassifier.from_http_status(403).taxonomy == FailureTaxonomy.HTTP_4XX


def test_exception_classifier_heuristics() -> None:
    captcha = FailureClassifier.from_exception(RuntimeError("captcha required"))
    assert captcha.taxonomy == FailureTaxonomy.CAPTCHA_REQUIRED
    auth = FailureClassifier.from_exception(RuntimeError("401 unauthorized"))
    assert auth.taxonomy == FailureTaxonomy.AUTH_REQUIRED
    rate = FailureClassifier.from_exception(RuntimeError("429 too many requests"))
    assert rate.taxonomy == FailureTaxonomy.RATE_LIMITED


def test_classifier_stage_override() -> None:
    cls = FailureClassifier.from_taxonomy(
        FailureTaxonomy.TIMEOUT, stage="extract"
    )
    assert cls.stage == "extract"
