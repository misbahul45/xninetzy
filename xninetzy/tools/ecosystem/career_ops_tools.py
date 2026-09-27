from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from xninetzy.db.migrations import run_migrations
from xninetzy.db.sqlite import init_db
from xninetzy.domains.career.eval import (
    EvalRunReport,
    load_eval_set,
    run_eval,
)
from xninetzy.os.research.sources import get_adapter, list_adapters
from xninetzy.tools.tool_results import to_tool_result


def _ensure_db() -> None:
    init_db()
    run_migrations()


def _emit_checkpoint(plan_id: str, step_id: str, status: str, payload: dict[str, Any]) -> None:
    _ensure_db()
    from datetime import datetime, timezone

    from xninetzy.db.sqlite import connect

    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO observability_events
              (event_kind, severity, source, subject, payload_json, occurred_at)
            VALUES ('harness_checkpoint', 'info', 'career_ops', ?, ?, ?)
            """,
            (
                f"{plan_id}:{step_id}",
                json.dumps({"status": status, **payload}, ensure_ascii=False),
                now,
            ),
        )


@tool
def career_adapter_health(
    adapter_ids: str = "",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Snapshot health for every registered career adapter (or a comma-separated subset).

    Args:
        adapter_ids: Optional comma-separated list of adapter ids to filter.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    _ensure_db()
    wanted = [a.strip() for a in adapter_ids.split(",") if a.strip()]
    ids = wanted or list_adapters()
    rows: list[dict[str, Any]] = []
    for adapter_id in ids:
        adapter = get_adapter(adapter_id)
        if adapter is None:
            rows.append({"adapter": adapter_id, "status": "unknown"})
            continue
        try:
            breaker_state = getattr(adapter._breaker, "_state", None)
            open_until = getattr(breaker_state, "open_until", 0.0) if breaker_state else 0.0
            state = getattr(breaker_state, "state", "unknown") if breaker_state else "unknown"
            rows.append(
                {
                    "adapter": adapter_id,
                    "category": getattr(adapter, "category", None).value
                    if getattr(adapter, "category", None)
                    else None,
                    "rate_limit_rpm": adapter.rate_limit.requests_per_minute,
                    "circuit_state": state,
                    "circuit_open_until": open_until,
                    "api_browser": "browser" in type(adapter).__module__,
                }
            )
        except Exception as exc:
            rows.append({"adapter": adapter_id, "status": "error", "error": str(exc)})
    out = {"status_flag": "ok", "adapters": rows, "total": len(rows)}
    if plan_id:
        _emit_checkpoint(plan_id, step_id or "career_adapter_health", "ok", {"count": len(rows)})
    return to_tool_result(json.dumps(out, ensure_ascii=False))


@tool
def career_capability_revalidate(
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Reconcile the live adapter registry with the design capability matrix.

    Reports which career adapters are registered, which the matrix expects, and
    whether each adapter's category matches.

    Args:
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    from xninetzy.os.research.router import _ROUTING_TABLE
    from xninetzy.os.research.sources import SourceCategory

    expected_company = set(_ROUTING_TABLE.get(SourceCategory.COMPANY, ()))
    actual = set(list_adapters())
    expected_career = {aid for aid in expected_company if aid in {"remoteok", "arbeitnow", "kalibrr", "glints", "dealls", "jobstreet_id"}}
    actual_career = expected_career & actual
    missing = expected_career - actual
    extras = {
        aid
        for aid in actual
        if aid.startswith(("remoteok", "arbeitnow", "kalibrr", "glints", "dealls", "jobstreet"))
    } - expected_career
    out = {
        "status_flag": "ok",
        "expected_career_adapters": sorted(expected_career),
        "registered_career_adapters": sorted(actual_career),
        "missing": sorted(missing),
        "extras": sorted(extras),
        "total_registered": len(actual),
        "drift": bool(missing or extras),
    }
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_capability_revalidate",
            "ok" if not out["drift"] else "drift",
            {"missing": len(missing), "extras": len(extras)},
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


@tool
def career_run_eval(
    eval_path: str = "data/career/eval/indonesia_internships.json",
    limit: int = 25,
    country: str = "",
    work_mode: str = "any",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Run a career eval set against `career_search_internships` and return mean recall.

    Args:
        eval_path: Path to the eval JSON (relative to repo root or absolute).
        limit: Max results to fetch per query.
        country: Country filter forwarded to the search.
        work_mode: Work mode filter forwarded to the search.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    from pathlib import Path

    from xninetzy.tools.ecosystem.career_tools import career_search_internships

    path = Path(eval_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        out = {"status_flag": "error", "error": f"eval set not found: {path}"}
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_run_eval", "not_found", {"path": str(path)})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    eval_set = load_eval_set(path)

    def _query(query) -> list[Any]:
        raw = career_search_internships.func(
            query=query.query_text,
            country=country or query.country,
            work_mode=work_mode or query.work_mode,
            limit=limit,
            plan_id=plan_id,
            step_id=f"career_run_eval.{query.query_id}",
            chat_id=chat_id,
            sender_id=sender_id,
            idempotency_key=idempotency_key,
        )
        envelope = json.loads(raw)
        payload = json.loads(envelope.get("summary", "{}"))
        return [
            {"url": item.get("url", ""), "title": item.get("title", "")}
            for item in payload.get("results", [])
        ]

    report: EvalRunReport = run_eval(eval_set, _query)
    out = {
        "status_flag": "ok",
        "subset": report.subset,
        "query_count": report.query_count,
        "mean_recall_at_10": round(report.mean_recall_at_10, 4),
        "mean_recall_at_25": round(report.mean_recall_at_25, 4),
        "per_query": [
            {
                "query_id": q.query_id,
                "retrieved_count": q.retrieved_count,
                "hits": q.hits,
                "recall_at_10": round(q.recall_at_10, 4),
                "recall_at_25": round(q.recall_at_25, 4),
            }
            for q in report.per_query
        ],
    }
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_run_eval",
            "ok" if out["mean_recall_at_10"] >= 0.5 else "below_threshold",
            {"r10": out["mean_recall_at_10"], "r25": out["mean_recall_at_25"]},
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


career_ops_tools = [
    career_adapter_health,
    career_capability_revalidate,
    career_run_eval,
]


__all__ = [
    "career_adapter_health",
    "career_capability_revalidate",
    "career_run_eval",
    "career_ops_tools",
]
