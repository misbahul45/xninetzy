from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from xninetzy.db.migrations import run_migrations
from xninetzy.db.sqlite import init_db
from xninetzy.domains.career.profile import ProfileStore, default_profile_path
from xninetzy.domains.career.services import build_package, package_to_dict
from xninetzy.tools.tool_results import to_tool_result


def _ensure_db() -> None:
    init_db()
    run_migrations()


def _store() -> ProfileStore:
    return ProfileStore(default_profile_path())


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
            VALUES ('harness_checkpoint', 'info', 'career_package', ?, ?, ?)
            """,
            (
                f"{plan_id}:{step_id}",
                json.dumps({"status": status, **payload}, ensure_ascii=False),
                now,
            ),
        )


def _posting_from_search(posting_id: str, sender_id: str = "") -> dict[str, Any]:
    from xninetzy.tools.ecosystem.career_tools import career_search_jobs

    raw = career_search_jobs.func(
        query="",
        country="",
        work_mode="any",
        posted_within_days=0,
        limit=1,
        posting_id=posting_id,
        plan_id="",
        step_id="",
        chat_id="system",
        sender_id=sender_id,
        idempotency_key="",
    )
    envelope = json.loads(raw)
    payload = json.loads(envelope.get("summary", "{}"))
    if payload.get("status") == "not_found":
        return {"id": posting_id, "title": "", "company": "", "url": "", "snippet": ""}
    return payload.get("posting", {"id": posting_id})


@tool
def career_generate_application_package(
    posting_id: str,
    sender_id: str = "",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    idempotency_key: str = "",
) -> str:
    """Generate a tailored application package for a posting — every claim cites profile evidence.

    Pulls the posting (or accepts a cached snapshot), the CandidateProfile,
    and produces: CV diff, cover letter, common-questions answers, missing-info list,
    and a fabrication check. Refuses to emit any claim without an evidence link.

    Args:
        posting_id: Posting identifier (RemoteOK id, ArbeitNow slug, etc.).
        sender_id: Owner principal.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        idempotency_key: Optional idempotency key.
    """
    profile = _store().load()
    if profile is None:
        out = {
            "status_flag": "error",
            "error": "candidate profile missing — seed it via career_update_candidate_profile(seed_from_cv=true)",
        }
        if plan_id:
            _emit_checkpoint(
                plan_id, step_id or "career_generate_application_package", "no_profile", {}
            )
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    posting = _posting_from_search(posting_id, sender_id=sender_id)
    if not posting.get("id"):
        posting = {
            "id": posting_id,
            "title": "",
            "company": "",
            "url": "",
            "snippet": "",
        }
    pkg = build_package(profile=profile, posting=posting)
    out = {
        "status_flag": "ok",
        "package": package_to_dict(pkg),
    }
    if plan_id:
        _emit_checkpoint(
            plan_id,
            step_id or "career_generate_application_package",
            "ok",
            {
                "matched_skills": len(pkg.matched_skills),
                "matched_experiences": len(pkg.matched_experiences),
                "evidence_links": pkg.fabrication_check["evidence_links_total"],
                "missing": len(pkg.missing_information),
            },
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


career_application_tools = [career_generate_application_package]


__all__ = [
    "career_application_tools",
    "career_generate_application_package",
]
