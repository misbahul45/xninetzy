"""Structured failure taxonomy + classifier.

Every fetch/parse/extraction failure MUST be classified into a finite,
enumerated taxonomy. The classifier returns a typed ``FailureClassification``
that downstream code (retry engine, circuit breaker, telemetry, MCP
result) can act on without parsing free-form exception messages.

Retryability is decided by the classifier, not by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FailureTaxonomy(StrEnum):
    POLICY_BLOCKED = "POLICY_BLOCKED"
    ROBOTS_DISALLOWED = "ROBOTS_DISALLOWED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    WAF_BLOCK = "WAF_BLOCK"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    DNS_ERROR = "DNS_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    HTTP_4XX = "HTTP_4XX"
    HTTP_5XX = "HTTP_5XX"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    EMPTY_RESULT = "EMPTY_RESULT"
    PAGE_NOT_READY = "PAGE_NOT_READY"
    SELECTOR_MISS = "SELECTOR_MISS"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    PARSER_ERROR = "PARSER_ERROR"
    BROWSER_CRASH = "BROWSER_CRASH"
    BROWSER_TIMEOUT = "BROWSER_TIMEOUT"
    SOURCE_CHANGED = "SOURCE_CHANGED"
    ENDPOINT_DEPRECATED = "ENDPOINT_DEPRECATED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    CACHE_ERROR = "CACHE_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True)
class FailureClassification:
    taxonomy: FailureTaxonomy
    retryable: bool
    severity: str  # "low" | "medium" | "high" | "critical"
    source_health_impact: str  # "none" | "low" | "medium" | "high"
    fallback_allowed: bool
    recommended_action: str
    http_status: int | None = None
    stage: str = "fetch"  # "policy" | "fetch" | "parse" | "extract" | "normalize" | "store"


# Pre-built classification table for the common cases.
_TABLE: dict[FailureTaxonomy, FailureClassification] = {
    FailureTaxonomy.POLICY_BLOCKED: FailureClassification(
        taxonomy=FailureTaxonomy.POLICY_BLOCKED,
        retryable=False,
        severity="high",
        source_health_impact="high",
        fallback_allowed=False,
        recommended_action="STOP_DO_NOT_RETRY",
    ),
    FailureTaxonomy.ROBOTS_DISALLOWED: FailureClassification(
        taxonomy=FailureTaxonomy.ROBOTS_DISALLOWED,
        retryable=False,
        severity="high",
        source_health_impact="high",
        fallback_allowed=False,
        recommended_action="STOP_RESPECT_ROBOTS",
    ),
    FailureTaxonomy.AUTH_REQUIRED: FailureClassification(
        taxonomy=FailureTaxonomy.AUTH_REQUIRED,
        retryable=False,
        severity="medium",
        source_health_impact="medium",
        fallback_allowed=False,
        recommended_action="REQUEST_USER_LOGIN",
    ),
    FailureTaxonomy.CAPTCHA_REQUIRED: FailureClassification(
        taxonomy=FailureTaxonomy.CAPTCHA_REQUIRED,
        retryable=False,
        severity="high",
        source_health_impact="high",
        fallback_allowed=False,
        recommended_action="STOP_NEVER_BYPASS_CAPTCHA",
    ),
    FailureTaxonomy.WAF_BLOCK: FailureClassification(
        taxonomy=FailureTaxonomy.WAF_BLOCK,
        retryable=False,
        severity="high",
        source_health_impact="high",
        fallback_allowed=False,
        recommended_action="STOP_DO_NOT_EVADE_WAF",
    ),
    FailureTaxonomy.RATE_LIMITED: FailureClassification(
        taxonomy=FailureTaxonomy.RATE_LIMITED,
        retryable=True,
        severity="medium",
        source_health_impact="medium",
        fallback_allowed=True,
        recommended_action="BACKOFF_RESPECT_RETRY_AFTER",
    ),
    FailureTaxonomy.TIMEOUT: FailureClassification(
        taxonomy=FailureTaxonomy.TIMEOUT,
        retryable=True,
        severity="medium",
        source_health_impact="low",
        fallback_allowed=True,
        recommended_action="RETRY_WITH_BACKOFF",
    ),
    FailureTaxonomy.DNS_ERROR: FailureClassification(
        taxonomy=FailureTaxonomy.DNS_ERROR,
        retryable=True,
        severity="medium",
        source_health_impact="medium",
        fallback_allowed=True,
        recommended_action="RETRY_BACKOFF",
    ),
    FailureTaxonomy.CONNECTION_ERROR: FailureClassification(
        taxonomy=FailureTaxonomy.CONNECTION_ERROR,
        retryable=True,
        severity="medium",
        source_health_impact="medium",
        fallback_allowed=True,
        recommended_action="RETRY_BACKOFF",
    ),
    FailureTaxonomy.HTTP_4XX: FailureClassification(
        taxonomy=FailureTaxonomy.HTTP_4XX,
        retryable=False,
        severity="medium",
        source_health_impact="medium",
        fallback_allowed=False,
        recommended_action="INSPECT_RESPONSE",
    ),
    FailureTaxonomy.HTTP_5XX: FailureClassification(
        taxonomy=FailureTaxonomy.HTTP_5XX,
        retryable=True,
        severity="medium",
        source_health_impact="medium",
        fallback_allowed=True,
        recommended_action="RETRY_BACKOFF",
    ),
    FailureTaxonomy.EMPTY_RESPONSE: FailureClassification(
        taxonomy=FailureTaxonomy.EMPTY_RESPONSE,
        retryable=False,
        severity="low",
        source_health_impact="low",
        fallback_allowed=True,
        recommended_action="INSPECT_PARSER",
    ),
    FailureTaxonomy.EMPTY_RESULT: FailureClassification(
        taxonomy=FailureTaxonomy.EMPTY_RESULT,
        retryable=False,
        severity="low",
        source_health_impact="low",
        fallback_allowed=False,
        recommended_action="RETURN_EMPTY_WITH_TELEMETRY",
    ),
    FailureTaxonomy.PAGE_NOT_READY: FailureClassification(
        taxonomy=FailureTaxonomy.PAGE_NOT_READY,
        retryable=True,
        severity="medium",
        source_health_impact="low",
        fallback_allowed=True,
        recommended_action="WAIT_OR_FALLBACK",
    ),
    FailureTaxonomy.SELECTOR_MISS: FailureClassification(
        taxonomy=FailureTaxonomy.SELECTOR_MISS,
        retryable=False,
        severity="high",
        source_health_impact="high",
        fallback_allowed=True,
        recommended_action="ROTATE_SELECTOR_CHAIN",
    ),
    FailureTaxonomy.SCHEMA_MISMATCH: FailureClassification(
        taxonomy=FailureTaxonomy.SCHEMA_MISMATCH,
        retryable=False,
        severity="high",
        source_health_impact="high",
        fallback_allowed=False,
        recommended_action="OPEN_PARSER_TICKET",
    ),
    FailureTaxonomy.PARSER_ERROR: FailureClassification(
        taxonomy=FailureTaxonomy.PARSER_ERROR,
        retryable=False,
        severity="medium",
        source_health_impact="medium",
        fallback_allowed=True,
        recommended_action="ROTATE_SELECTOR_CHAIN",
    ),
    FailureTaxonomy.BROWSER_CRASH: FailureClassification(
        taxonomy=FailureTaxonomy.BROWSER_CRASH,
        retryable=True,
        severity="high",
        source_health_impact="medium",
        fallback_allowed=True,
        recommended_action="RECONNECT_BROWSER",
    ),
    FailureTaxonomy.BROWSER_TIMEOUT: FailureClassification(
        taxonomy=FailureTaxonomy.BROWSER_TIMEOUT,
        retryable=True,
        severity="medium",
        source_health_impact="low",
        fallback_allowed=True,
        recommended_action="RETRY_OR_FALLBACK",
    ),
    FailureTaxonomy.SOURCE_CHANGED: FailureClassification(
        taxonomy=FailureTaxonomy.SOURCE_CHANGED,
        retryable=False,
        severity="critical",
        source_health_impact="high",
        fallback_allowed=True,
        recommended_action="OPEN_ADAPTER_REVIEW_TICKET",
    ),
    FailureTaxonomy.ENDPOINT_DEPRECATED: FailureClassification(
        taxonomy=FailureTaxonomy.ENDPOINT_DEPRECATED,
        retryable=False,
        severity="high",
        source_health_impact="high",
        fallback_allowed=False,
        recommended_action="MIGRATE_ADAPTER",
    ),
    FailureTaxonomy.NOT_SUPPORTED: FailureClassification(
        taxonomy=FailureTaxonomy.NOT_SUPPORTED,
        retryable=False,
        severity="low",
        source_health_impact="none",
        fallback_allowed=False,
        recommended_action="RETURN_UNSUPPORTED",
    ),
    FailureTaxonomy.CACHE_ERROR: FailureClassification(
        taxonomy=FailureTaxonomy.CACHE_ERROR,
        retryable=True,
        severity="low",
        source_health_impact="none",
        fallback_allowed=True,
        recommended_action="BYPASS_CACHE",
    ),
    FailureTaxonomy.UNKNOWN_ERROR: FailureClassification(
        taxonomy=FailureTaxonomy.UNKNOWN_ERROR,
        retryable=False,
        severity="medium",
        source_health_impact="low",
        fallback_allowed=False,
        recommended_action="LOG_AND_INSPECT",
    ),
}


class FailureClassifier:
    """Stateless classifier mapping raw inputs to structured failure data."""

    @staticmethod
    def from_exception(
        exc: BaseException, *, stage: str = "fetch"
    ) -> FailureClassification:
        """Best-effort classifier for an arbitrary exception."""

        msg = str(exc).lower()
        if "captcha" in msg:
            base = _TABLE[FailureTaxonomy.CAPTCHA_REQUIRED]
        elif "policy" in msg and "block" in msg:
            base = _TABLE[FailureTaxonomy.POLICY_BLOCKED]
        elif "robot" in msg:
            base = _TABLE[FailureTaxonomy.ROBOTS_DISALLOWED]
        elif "auth" in msg or "login" in msg or "unauthorized" in msg:
            base = _TABLE[FailureTaxonomy.AUTH_REQUIRED]
        elif "rate limit" in msg or "too many" in msg or "429" in msg:
            base = _TABLE[FailureTaxonomy.RATE_LIMITED]
        elif "timeout" in msg or "timed out" in msg:
            base = _TABLE[FailureTaxonomy.TIMEOUT]
        elif "dns" in msg or "name resolution" in msg:
            base = _TABLE[FailureTaxonomy.DNS_ERROR]
        elif "connection" in msg or "reset" in msg:
            base = _TABLE[FailureTaxonomy.CONNECTION_ERROR]
        elif "browser" in msg and "crash" in msg:
            base = _TABLE[FailureTaxonomy.BROWSER_CRASH]
        else:
            base = _TABLE[FailureTaxonomy.UNKNOWN_ERROR]
        # Keep classifier pure — return new object with stage override.
        return FailureClassification(
            taxonomy=base.taxonomy,
            retryable=base.retryable,
            severity=base.severity,
            source_health_impact=base.source_health_impact,
            fallback_allowed=base.fallback_allowed,
            recommended_action=base.recommended_action,
            stage=stage,
        )

    @staticmethod
    def from_http_status(
        status: int, *, stage: str = "fetch"
    ) -> FailureClassification:
        if status == 401:
            base = _TABLE[FailureTaxonomy.AUTH_REQUIRED]
        elif status == 403:
            # 403 may be policy/security or just auth — classifier treats it
            # as HTTP_4XX (non-retryable); policy gate handles the distinction
            # upstream.
            base = _TABLE[FailureTaxonomy.HTTP_4XX]
        elif status == 404:
            base = _TABLE[FailureTaxonomy.HTTP_4XX]
        elif status == 408:
            base = _TABLE[FailureTaxonomy.TIMEOUT]
        elif status == 429:
            base = _TABLE[FailureTaxonomy.RATE_LIMITED]
        elif 500 <= status < 600:
            base = _TABLE[FailureTaxonomy.HTTP_5XX]
        elif 400 <= status < 500:
            base = _TABLE[FailureTaxonomy.HTTP_4XX]
        else:
            base = _TABLE[FailureTaxonomy.UNKNOWN_ERROR]
        return FailureClassification(
            taxonomy=base.taxonomy,
            retryable=base.retryable,
            severity=base.severity,
            source_health_impact=base.source_health_impact,
            fallback_allowed=base.fallback_allowed,
            recommended_action=base.recommended_action,
            http_status=status,
            stage=stage,
        )

    @staticmethod
    def from_taxonomy(
        taxonomy: FailureTaxonomy, *, stage: str = "fetch", **overrides: Any
    ) -> FailureClassification:
        base = _TABLE.get(taxonomy, _TABLE[FailureTaxonomy.UNKNOWN_ERROR])
        return FailureClassification(
            taxonomy=base.taxonomy,
            retryable=overrides.get("retryable", base.retryable),
            severity=overrides.get("severity", base.severity),
            source_health_impact=overrides.get(
                "source_health_impact", base.source_health_impact
            ),
            fallback_allowed=overrides.get(
                "fallback_allowed", base.fallback_allowed
            ),
            recommended_action=overrides.get(
                "recommended_action", base.recommended_action
            ),
            stage=overrides.get("stage", stage),
        )

    @staticmethod
    def all() -> dict[FailureTaxonomy, FailureClassification]:
        return dict(_TABLE)
