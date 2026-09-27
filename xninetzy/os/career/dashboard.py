from __future__ import annotations

from typing import Any

from xninetzy.db.migrations import run_migrations
from xninetzy.db.sqlite import init_db
from xninetzy.os.career.compliance import audit as audit_compliance
from xninetzy.os.career.search_cache import SearchCache
from xninetzy.os.research.sources import list_adapters


_CACHE = SearchCache()


def cache() -> SearchCache:
    return _CACHE


def init() -> None:
    init_db()
    run_migrations()


def _source_quality_rows() -> list[dict[str, Any]]:
    from xninetzy.db.sqlite import connect

    init()
    with connect() as conn:
        rows = conn.execute(
            "SELECT source, postings_total, outcomes_total, interviews_total, offers_total, rejects_total, quality_score, updated_at FROM career_source_quality"
        ).fetchall()
    return [dict(r) for r in rows]


def _outcome_summary(since_iso: str | None = None) -> dict[str, int]:
    from xninetzy.db.sqlite import connect

    init()
    sql = (
        "SELECT outcome, COUNT(*) AS n FROM career_outcomes"
        + (" WHERE recorded_at >= ?" if since_iso else "")
        + " GROUP BY outcome"
    )
    with connect() as conn:
        rows = conn.execute(sql, (since_iso,) if since_iso else ()).fetchall()
    return {row["outcome"]: row["n"] for row in rows}


def _application_state_distribution() -> dict[str, int]:
    from xninetzy.db.sqlite import connect

    init()
    with connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM career_applications GROUP BY status"
        ).fetchall()
    return {row["status"]: row["n"] for row in rows}


def _observation_counts() -> dict[str, int]:
    from xninetzy.db.sqlite import connect

    init()
    counts: dict[str, int] = {}
    with connect() as conn:
        for kind in ("harness_action", "harness_checkpoint"):
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM observability_events WHERE event_kind=? AND source IN ('career', 'career_browser', 'career_package', 'career_orchestrator', 'career_ops', 'career_profile')",
                (kind,),
            ).fetchone()
            counts[kind] = row["n"]
    return counts


def _browser_sessions_summary() -> dict[str, int]:
    from xninetzy.db.sqlite import connect

    init()
    with connect() as conn:
        rows = conn.execute(
            "SELECT state, COUNT(*) AS n FROM career_browser_sessions GROUP BY state"
        ).fetchall()
    return {row["state"]: row["n"] for row in rows}


def _active_tokens() -> int:
    from datetime import datetime, timezone

    init()
    from xninetzy.db.sqlite import connect

    now_iso = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM career_confirmation_tokens WHERE consumed_at IS NULL AND expires_at > ?",
            (now_iso,),
        ).fetchone()
    return row["n"]


def build_dashboard() -> dict[str, Any]:
    init()
    cache_stats = _CACHE.stats()
    return {
        "status_flag": "ok",
        "snapshot_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "adapters": {
            "registered": list(list_adapters()),
            "compliance": audit_compliance(),
        },
        "search_cache": cache_stats,
        "source_quality": _source_quality_rows(),
        "outcomes": _outcome_summary(),
        "application_state_distribution": _application_state_distribution(),
        "browser_sessions": _browser_sessions_summary(),
        "active_confirmation_tokens": _active_tokens(),
        "observability": _observation_counts(),
        "totals": {"applications_in_store": _count_rows("career_applications")},
    }


def _count_rows(table: str) -> int:
    from xninetzy.db.sqlite import connect

    init()
    with connect() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
    return row["n"]


def recovery_snapshot(stuck_after_days: int = 7) -> list[dict[str, Any]]:
    from datetime import datetime, timedelta, timezone

    init()
    from xninetzy.db.sqlite import connect

    cutoff = (datetime.now(timezone.utc) - timedelta(days=stuck_after_days)).isoformat()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT application_key, posting_id, status, updated_at
              FROM career_applications
             WHERE updated_at < ?
               AND status NOT IN ('offer', 'rejected', 'withdrawn')
            """,
            (cutoff,),
        ).fetchall()
    return [dict(r) for r in rows]


__all__ = [
    "build_dashboard",
    "cache",
    "init",
    "recovery_snapshot",
]
