"""Per-source health metrics + structural-change detection.

Tracks success / failure counts, latency statistics, fallback rate, parser
version, circuit-breaker mirror, and emits a typed ``SourceHealthRecord``
that the MCP surface (e.g. ``career_source_health``) returns verbatim.

State is in-memory; it is intentionally cheap to read and snapshot.
Operators can persist snapshots through the existing observability layer.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class _LatencyBucket:
    samples: Deque[float] = field(default_factory=lambda: deque(maxlen=200))

    def add(self, value_ms: float) -> None:
        self.samples.append(value_ms)

    def avg(self) -> float:
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)

    def p95(self) -> float:
        if not self.samples:
            return 0.0
        ordered = sorted(self.samples)
        idx = max(0, int(round(0.95 * (len(ordered) - 1))))
        return ordered[idx]


@dataclass(frozen=True)
class SourceHealthRecord:
    source_id: str
    status: str
    success_count: int
    failure_count: int
    rate_limited_count: int
    timeout_count: int
    blocked_count: int
    extraction_failure_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    records_last_run: int
    selector_fallback_rate: float
    parser_version: str
    circuit_state: str
    failure_streak: int
    last_success_at: str | None
    last_failure_at: str | None
    last_failure_reason: str | None
    last_failure_taxonomy: str | None


@dataclass
class _SourceStats:
    success_count: int = 0
    failure_count: int = 0
    rate_limited_count: int = 0
    timeout_count: int = 0
    blocked_count: int = 0
    extraction_failure_count: int = 0
    records_last_run: int = 0
    selector_fallback_total: int = 0
    selector_attempt_total: int = 0
    parser_version: str = "1.0"
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_failure_reason: str | None = None
    last_failure_taxonomy: str | None = None
    latency: _LatencyBucket = field(default_factory=_LatencyBucket)


class SourceHealthService:
    """In-memory per-source health + structural-change detector.

    The service is thread-safe for cooperative single-writer patterns
    (acquisition service writes sequentially per source).
    """

    def __init__(self) -> None:
        self._stats: dict[str, _SourceStats] = {}
        # circuit_state mirrors from xninetzy.os.research.sources.rate_limit
        self._circuit_state: dict[str, str] = {}
        self._failure_streak: dict[str, int] = {}
        self._last_baseline_records: dict[str, int] = {}

    # ------------------------------------------------------------------ record
    def record_success(
        self,
        source_id: str,
        *,
        records: int,
        latency_ms: float,
        parser_version: str | None = None,
        selector_fallback_used: bool = False,
    ) -> None:
        stats = self._stats.setdefault(source_id, _SourceStats())
        stats.success_count += 1
        stats.records_last_run = records
        stats.selector_attempt_total += 1
        if selector_fallback_used:
            stats.selector_fallback_total += 1
        if parser_version:
            stats.parser_version = parser_version
        stats.latency.add(latency_ms)
        stats.last_success_at = _now_iso()
        self._failure_streak[source_id] = 0

    def record_failure(
        self,
        source_id: str,
        *,
        taxonomy: str,
        reason: str | None = None,
    ) -> None:
        stats = self._stats.setdefault(source_id, _SourceStats())
        stats.failure_count += 1
        stats.last_failure_at = _now_iso()
        stats.last_failure_reason = reason
        stats.last_failure_taxonomy = taxonomy
        if taxonomy in ("POLICY_BLOCKED", "ROBOTS_DISALLOWED"):
            stats.blocked_count += 1
        if taxonomy in ("TIMEOUT", "BROWSER_TIMEOUT"):
            stats.timeout_count += 1
        if taxonomy == "RATE_LIMITED":
            stats.rate_limited_count += 1
        if taxonomy in ("SELECTOR_MISS", "PARSER_ERROR", "SCHEMA_MISMATCH"):
            stats.extraction_failure_count += 1
        self._failure_streak[source_id] = self._failure_streak.get(source_id, 0) + 1

    def set_circuit_state(self, source_id: str, state: str) -> None:
        self._circuit_state[source_id] = state

    # ------------------------------------------------------------------- read
    def snapshot(self, source_id: str) -> SourceHealthRecord:
        stats = self._stats.get(source_id, _SourceStats())
        total_attempts = stats.selector_attempt_total
        fb_rate = (
            stats.selector_fallback_total / total_attempts
            if total_attempts
            else 0.0
        )
        circuit = self._circuit_state.get(source_id, "CLOSED")
        streak = self._failure_streak.get(source_id, 0)
        status = self._derive_status(stats, circuit, streak)
        return SourceHealthRecord(
            source_id=source_id,
            status=status,
            success_count=stats.success_count,
            failure_count=stats.failure_count,
            rate_limited_count=stats.rate_limited_count,
            timeout_count=stats.timeout_count,
            blocked_count=stats.blocked_count,
            extraction_failure_count=stats.extraction_failure_count,
            avg_latency_ms=stats.latency.avg(),
            p95_latency_ms=stats.latency.p95(),
            records_last_run=stats.records_last_run,
            selector_fallback_rate=fb_rate,
            parser_version=stats.parser_version,
            circuit_state=circuit,
            failure_streak=streak,
            last_success_at=stats.last_success_at,
            last_failure_at=stats.last_failure_at,
            last_failure_reason=stats.last_failure_reason,
            last_failure_taxonomy=stats.last_failure_taxonomy,
        )

    def snapshot_all(self) -> list[SourceHealthRecord]:
        return [self.snapshot(s) for s in sorted(self._stats.keys())]

    # ---------------------------------------------------- change detection
    def update_baseline_records(self, source_id: str, count: int) -> None:
        """Store a per-source record-count baseline for change detection."""

        self._last_baseline_records[source_id] = count

    def detect_change(
        self,
        source_id: str,
        current_count: int,
        *,
        drop_ratio: float = 0.5,
        min_baseline: int = 10,
    ) -> bool:
        """Return True if the current record count is suspiciously low vs baseline.

        The brief requires structural-change detection. We compare the
        current run's record count to the previously observed baseline.
        A drop of ``drop_ratio`` (default 50%) after at least
        ``min_baseline`` prior records flags ``SOURCE_CHANGED``.
        """

        baseline = self._last_baseline_records.get(source_id)
        if baseline is None or baseline < min_baseline:
            return False
        if current_count < baseline * drop_ratio:
            return True
        return False

    # -------------------------------------------------------------- helpers
    def _derive_status(
        self, stats: _SourceStats, circuit: str, streak: int
    ) -> str:
        if circuit == "OPEN":
            return "BROKEN"
        if streak >= 3:
            return "DEGRADED"
        total = stats.success_count + stats.failure_count
        if total == 0:
            return "UNKNOWN"
        rate = stats.success_count / total
        if rate >= 0.9:
            return "HEALTHY"
        if rate >= 0.5:
            return "DEGRADED"
        return "BROKEN"


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
