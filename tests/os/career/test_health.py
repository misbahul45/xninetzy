"""Test source health service."""

from __future__ import annotations

from xninetzy.os.career.acquisition.health import SourceHealthService


def test_unknown_initially() -> None:
    rec = SourceHealthService().snapshot("ghost")
    assert rec.status == "UNKNOWN"


def test_healthy_after_successes() -> None:
    svc = SourceHealthService()
    for _ in range(5):
        svc.record_success("remoteok", records=10, latency_ms=120)
    rec = svc.snapshot("remoteok")
    assert rec.success_count == 5
    assert rec.records_last_run == 10
    assert rec.status == "HEALTHY"


def test_degraded_when_failure_streak_reaches_3() -> None:
    svc = SourceHealthService()
    svc.record_failure("x", taxonomy="TIMEOUT")
    svc.record_failure("x", taxonomy="TIMEOUT")
    svc.record_failure("x", taxonomy="TIMEOUT")
    rec = svc.snapshot("x")
    assert rec.failure_streak == 3
    assert rec.status == "DEGRADED"


def test_blocked_count_increments_on_policy_blocked() -> None:
    svc = SourceHealthService()
    svc.record_failure("y", taxonomy="POLICY_BLOCKED")
    rec = svc.snapshot("y")
    assert rec.blocked_count == 1


def test_timeout_count_increments_on_timeout() -> None:
    svc = SourceHealthService()
    svc.record_failure("z", taxonomy="TIMEOUT")
    svc.record_failure("z", taxonomy="BROWSER_TIMEOUT")
    rec = svc.snapshot("z")
    assert rec.timeout_count == 2


def test_structural_change_detection() -> None:
    svc = SourceHealthService()
    svc.update_baseline_records("remoteok", 100)
    assert svc.detect_change("remoteok", 30) is True  # 30 < 100 * 0.5
    assert svc.detect_change("remoteok", 80) is False


def test_change_detection_requires_min_baseline() -> None:
    svc = SourceHealthService()
    svc.update_baseline_records("new", 5)
    # Baseline < min_baseline (10) ⇒ never flags.
    assert svc.detect_change("new", 0) is False
