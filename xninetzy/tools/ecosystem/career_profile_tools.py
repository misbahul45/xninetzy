from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from xninetzy.db.migrations import run_migrations
from xninetzy.db.sqlite import init_db
from xninetzy.domains.career.profile import (
    CandidateProfile,
    ProfileStore,
    default_profile_path,
)
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
            VALUES ('harness_checkpoint', 'info', 'career_profile', ?, ?, ?)
            """,
            (
                f"{plan_id}:{step_id}",
                json.dumps({"status": status, **payload}, ensure_ascii=False),
                now,
            ),
        )


@tool
def career_get_candidate_profile(
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Return the owner's CandidateProfile from disk (gitignored path).

    Args:
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    store = _store()
    profile = store.load()
    if profile is None:
        out = {
            "status_flag": "not_found",
            "path": str(default_profile_path()),
            "hint": "Seed profile via career_update_candidate_profile with seed_from_cv=true",
        }
        if plan_id:
            _emit_checkpoint(plan_id, step_id or "career_get_candidate_profile", "not_found", {})
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    out = {
        "status_flag": "ok",
        "profile": profile.to_dict(),
        "path": str(default_profile_path()),
    }
    if plan_id:
        _emit_checkpoint(plan_id, step_id or "career_get_candidate_profile", "ok", {"skills": len(profile.skills)})
    return to_tool_result(json.dumps(out, ensure_ascii=False))


@tool
def career_update_candidate_profile(
    update_json: str = "",
    seed_from_cv: bool = False,
    cv_text: str = "",
    github_username: str = "misbahul45",
    plan_id: str = "",
    step_id: str = "",
    chat_id: str = "system",
    sender_id: str = "",
    idempotency_key: str = "",
) -> str:
    """Update the CandidateProfile (JSON Patch shape) or re-seed from CV + GitHub.

    Two modes:
    - seed_from_cv=true: re-extract skills/experience/education from CV text and rebuild.
      Use `cv_text` to pass the raw CV (else reads data/candidate/raw/*.txt). Optionally
      pass `github_username` to fetch the user's public repos.
    - seed_from_cv=false: apply a JSON Patch to the existing profile (update_json must
      be a dict of top-level fields to replace).

    Args:
        update_json: JSON-encoded dict of fields to replace.
        seed_from_cv: If True, rebuild profile from CV + GitHub.
        cv_text: Raw CV text (used only when seed_from_cv=true).
        github_username: GitHub handle to fetch public repos from.
        plan_id: Harness plan id.
        step_id: Harness step id.
        chat_id: Chat ID.
        sender_id: Owner principal.
        idempotency_key: Optional idempotency key.
    """
    from datetime import datetime, timezone

    store = _store()
    if seed_from_cv:
        from pathlib import Path
        from urllib.request import urlopen
        from urllib.error import URLError

        from xninetzy.domains.career.profile.builder import build_seed_profile

        if not cv_text:
            candidates = list(Path("data/candidate/raw").glob("*.txt"))
            if not candidates:
                out = {
                    "status_flag": "error",
                    "error": "no CV text provided and no files found under data/candidate/raw/",
                }
                if plan_id:
                    _emit_checkpoint(
                        plan_id, step_id or "career_update_candidate_profile", "no_cv", {}
                    )
                return to_tool_result(json.dumps(out, ensure_ascii=False))
            cv_text = candidates[0].read_text(encoding="utf-8")
        repos: list[dict[str, Any]] = []
        if github_username:
            try:
                with urlopen(
                    f"https://api.github.com/users/{github_username}/repos?per_page=100&sort=updated",
                    timeout=20,
                ) as resp:
                    repos = json.loads(resp.read())
            except (URLError, TimeoutError, json.JSONDecodeError):
                repos = []
        profile = build_seed_profile(cv_text, github_repos=repos)
        store.save(profile)
        out = {
            "status_flag": "ok",
            "profile": profile.to_dict(),
            "mode": "seeded",
            "skills": len(profile.skills),
            "experience": len(profile.experience),
            "education": len(profile.education),
            "projects": len(profile.projects),
        }
        if plan_id:
            _emit_checkpoint(
                plan_id,
                step_id or "career_update_candidate_profile",
                "ok",
                {"mode": "seeded", "skills": len(profile.skills)},
            )
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    existing = store.load()
    if existing is None:
        out = {
            "status_flag": "error",
            "error": "no existing profile; call with seed_from_cv=true first",
        }
        if plan_id:
            _emit_checkpoint(
                plan_id, step_id or "career_update_candidate_profile", "not_found", {}
            )
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    if not update_json.strip():
        out = {"status_flag": "error", "error": "update_json must be non-empty"}
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    try:
        patch = json.loads(update_json)
    except json.JSONDecodeError as exc:
        out = {"status_flag": "error", "error": f"invalid JSON: {exc}"}
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    if not isinstance(patch, dict):
        out = {"status_flag": "error", "error": "update_json must decode to an object"}
        return to_tool_result(json.dumps(out, ensure_ascii=False))
    data = existing.to_dict()
    for key, value in patch.items():
        if key in {"full_name", "email", "phone", "location", "headline", "summary"}:
            data[key] = value
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated = CandidateProfile(**{k: data[k] for k in [
        "full_name", "email", "phone", "location", "headline", "summary",
        "education", "experience", "projects", "skills", "links", "updated_at",
    ]})
    store.save(updated)
    out = {"status_flag": "ok", "profile": updated.to_dict(), "mode": "patched"}
    if plan_id:
        _emit_checkpoint(
            plan_id, step_id or "career_update_candidate_profile", "ok", {"mode": "patched"}
        )
    return to_tool_result(json.dumps(out, ensure_ascii=False))


career_profile_tools = [
    career_get_candidate_profile,
    career_update_candidate_profile,
]


__all__ = [
    "career_get_candidate_profile",
    "career_update_candidate_profile",
    "career_profile_tools",
]
