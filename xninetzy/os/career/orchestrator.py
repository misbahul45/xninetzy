from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from xninetzy.db.sqlite import connect, init_db
from xninetzy.os.career.applications_store import (
    VALID_STATUSES,
    ApplicationStore,
)


TOKEN_TTL_SECONDS = 300


@dataclass(frozen=True)
class ConfirmationToken:
    token: str
    application_key: str
    posting_id: str
    sender_id: str
    target_status: str
    issued_at: str
    expires_at: str


class ConfirmationTokenStore:
    def issue(
        self,
        *,
        application_key: str,
        posting_id: str,
        sender_id: str,
        target_status: str,
        now: datetime | None = None,
        ttl_seconds: int = TOKEN_TTL_SECONDS,
    ) -> ConfirmationToken:
        if target_status not in VALID_STATUSES:
            raise ValueError(f"invalid status; expected one of {sorted(VALID_STATUSES)}")
        init_db()
        now = now or datetime.now(timezone.utc)
        token = secrets.token_urlsafe(24)
        issued_at = now.isoformat()
        expires_at = (now + timedelta(seconds=max(1, ttl_seconds))).isoformat()
        with connect() as conn:
            conn.execute(
                "BEGIN IMMEDIATE",
            )
            conn.execute(
                """
                DELETE FROM career_confirmation_tokens
                 WHERE application_key=? AND target_status=? AND consumed_at IS NULL
                """,
                (application_key, target_status),
            )
            conn.execute(
                """
                INSERT INTO career_confirmation_tokens
                  (token, application_key, posting_id, sender_id, target_status,
                   issued_at, expires_at, consumed_at, consumed_for_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    token,
                    application_key,
                    posting_id,
                    sender_id,
                    target_status,
                    issued_at,
                    expires_at,
                ),
            )
        return ConfirmationToken(
            token=token,
            application_key=application_key,
            posting_id=posting_id,
            sender_id=sender_id,
            target_status=target_status,
            issued_at=issued_at,
            expires_at=expires_at,
        )

    def consume(
        self,
        *,
        token: str,
        sender_id: str,
        now: datetime | None = None,
    ) -> tuple[str, str] | None:
        """Consume a token; return (application_key, target_status) on success or None on failure."""
        init_db()
        now = now or datetime.now(timezone.utc)
        now_iso = now.isoformat()
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM career_confirmation_tokens
                 WHERE token=? AND consumed_at IS NULL
                """,
                (token,),
            ).fetchone()
            if row is None:
                return None
            if row["sender_id"] != sender_id:
                return None
            if row["expires_at"] <= now_iso:
                return None
            conn.execute(
                """
                UPDATE career_confirmation_tokens
                   SET consumed_at=?, consumed_for_status=?
                 WHERE token=?
                """,
                (now_iso, row["target_status"], token),
            )
        return row["application_key"], row["target_status"]


class ApplicationOrchestrator:
    def __init__(
        self,
        *,
        applications: ApplicationStore | None = None,
        tokens: ConfirmationTokenStore | None = None,
    ) -> None:
        self._applications = applications or ApplicationStore()
        self._tokens = tokens or ConfirmationTokenStore()

    def request_status_change(
        self,
        *,
        posting_id: str,
        sender_id: str,
        target_status: str,
        notes: str = "",
        now: datetime | None = None,
    ) -> dict:
        application_key = f"{sender_id or ''}::{posting_id}"
        issued = self._tokens.issue(
            application_key=application_key,
            posting_id=posting_id,
            sender_id=sender_id,
            target_status=target_status,
            now=now,
        )
        return {
            "status_flag": "awaiting_confirmation",
            "application_key": application_key,
            "target_status": target_status,
            "token_id": issued.token[:8] + "...",
            "expires_at": issued.expires_at,
            "confirm_via": "career_confirm_application",
            "owner_prompt": (
                f"Owner must explicitly confirm status change to '{target_status}'. "
                f"Token expires at {issued.expires_at}. Single-use, app-bound."
            ),
        }

    def confirm_status_change(
        self,
        *,
        token: str,
        sender_id: str,
        now: datetime | None = None,
    ) -> dict:
        result = self._tokens.consume(token=token, sender_id=sender_id, now=now)
        if result is None:
            return {
                "status_flag": "error",
                "error": "invalid, expired, already-used, or non-owner token",
            }
        application_key, target_status = result
        posting_id = application_key.split("::", 1)[1] if "::" in application_key else application_key
        try:
            record = self._applications.record(
                application_key=application_key,
                posting_id=posting_id,
                sender_id=sender_id,
                status=target_status,
                notes="(confirmed via token)",
                now=now or datetime.now(timezone.utc),
            )
        except Exception as exc:
            return {"status_flag": "error", "error": str(exc)}
        return {
            "status_flag": "submitted",
            "application": {
                "application_key": record.get("application_key"),
                "posting_id": record.get("posting_id"),
                "status": record.get("status"),
                "updated_at": record.get("updated_at"),
            },
        }


__all__ = [
    "ApplicationOrchestrator",
    "ConfirmationToken",
    "ConfirmationTokenStore",
    "TOKEN_TTL_SECONDS",
]
