from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from bs4 import BeautifulSoup

from xninetzy.db.sqlite import connect, init_db
from xninetzy.os.career.safe_fields import FormField, classify_field, partition_by_safety


class FormPageProtocol(Protocol):
    """Browser page operations exposed by the gateway; safe by construction."""

    def url(self) -> str: ...

    def title(self) -> str: ...

    def html(self) -> str: ...

    def fill(self, selector: str, value: str) -> None: ...

    def submit(self) -> None: ...


class FakeFormPage:
    """In-memory page used for tests. NEVER stores credentials in `current_value`."""

    def __init__(self, *, _url: str, _title: str, _html: str) -> None:
        self._url = _url
        self._title = _title
        self._html = _html
        self.filled: list[tuple[str, str]] = []
        self.submitted: bool = False

    def url(self) -> str:
        return self._url

    def title(self) -> str:
        return self._title

    def html(self) -> str:
        return self._html

    def fill(self, selector: str, value: str) -> None:
        self.filled.append((selector, value))

    def submit(self) -> None:
        self.submitted = True


@dataclass(frozen=True)
class InspectedForm:
    url: str
    title: str
    fields: tuple[FormField, ...]
    safe_count: int
    blocked_count: int

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "fields": [
                {
                    "name": f.name,
                    "type": f.field_type,
                    "label": f.label,
                    "required": f.required,
                    "selector": f.selector,
                    "current_value": "",
                    "safe_to_fill": f.safe_to_fill,
                    "safety_reason": f.safety_reason,
                }
                for f in self.fields
            ],
            "safe_count": self.safe_count,
            "blocked_count": self.blocked_count,
        }


@dataclass(frozen=True)
class FillResult:
    filled: tuple[dict[str, str], ...]
    skipped: tuple[dict[str, str], ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "filled": [{"name": f["name"], "value": "<redacted>"} for f in self.filled],
            "skipped": [{"name": s["name"], "reason": s["reason"]} for s in self.skipped],
        }


class ApplicationSessionRecord:
    """Audit row for an application browser session; never stores credentials."""

    def __init__(
        self,
        *,
        session_id: str,
        application_key: str,
        posting_id: str,
        sender_id: str,
        posting_url: str,
        state: str,
        opened_at: str,
        closed_at: str | None,
        last_inspected_at: str | None,
    ) -> None:
        self.session_id = session_id
        self.application_key = application_key
        self.posting_id = posting_id
        self.sender_id = sender_id
        self.posting_url = posting_url
        self.state = state
        self.opened_at = opened_at
        self.closed_at = closed_at
        self.last_inspected_at = last_inspected_at

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "application_key": self.application_key,
            "posting_id": self.posting_id,
            "sender_id": self.sender_id,
            "posting_url": self.posting_url,
            "state": self.state,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "last_inspected_at": self.last_inspected_at,
        }


class ApplicationSessionStore:
    def __init__(self) -> None:
        self._memory: dict[str, ApplicationSessionRecord] = {}
        self._page_factory: dict[str, FormPageProtocol] = {}

    def attach_page(self, session_id: str, page: FormPageProtocol) -> None:
        self._page_factory[session_id] = page

    def open(
        self,
        *,
        application_key: str,
        posting_id: str,
        sender_id: str,
        posting_url: str,
    ) -> ApplicationSessionRecord:
        init_db()
        now = datetime.now(timezone.utc).isoformat()
        existing = self._find_for(application_key)
        if existing is not None and existing.state == "open":
            raise ValueError(f"open session already exists for {application_key}")
        session_id = f"app-{uuid.uuid4().hex[:16]}"
        record = ApplicationSessionRecord(
            session_id=session_id,
            application_key=application_key,
            posting_id=posting_id,
            sender_id=sender_id,
            posting_url=posting_url,
            state="open",
            opened_at=now,
            closed_at=None,
            last_inspected_at=None,
        )
        self._memory[session_id] = record
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO career_browser_sessions
                  (session_id, application_key, posting_id, sender_id, posting_url,
                   state, opened_at, closed_at, last_inspected_at)
                VALUES (?, ?, ?, ?, ?, 'open', ?, NULL, NULL)
                """,
                (session_id, application_key, posting_id, sender_id, posting_url, now),
            )
        return record

    def get(self, session_id: str) -> ApplicationSessionRecord | None:
        return self._memory.get(session_id)

    def get_for(self, application_key: str) -> ApplicationSessionRecord | None:
        return self._find_for(application_key)

    def _find_for(self, application_key: str) -> ApplicationSessionRecord | None:
        for record in self._memory.values():
            if record.application_key == application_key:
                return record
        return None

    def list_open(self, sender_id: str | None = None) -> list[ApplicationSessionRecord]:
        records = [r for r in self._memory.values() if r.state == "open"]
        if sender_id is not None:
            records = [r for r in records if r.sender_id == sender_id]
        return records

    def inspect(self, session_id: str) -> None:
        record = self.get(session_id)
        if record is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        record.last_inspected_at = now
        with connect() as conn:
            conn.execute(
                "UPDATE career_browser_sessions SET last_inspected_at=? WHERE session_id=?",
                (now, session_id),
            )

    def close(self, session_id: str) -> bool:
        record = self.get(session_id)
        if record is None or record.state == "closed":
            return False
        now = datetime.now(timezone.utc).isoformat()
        record.state = "closed"
        record.closed_at = now
        with connect() as conn:
            conn.execute(
                "UPDATE career_browser_sessions SET state='closed', closed_at=? WHERE session_id=?",
                (now, session_id),
            )
        self._page_factory.pop(session_id, None)
        return True

    def get_page(self, session_id: str) -> FormPageProtocol | None:
        return self._page_factory.get(session_id)


def parse_form(html: str) -> tuple[str, list[FormField]]:
    soup = BeautifulSoup(html, "lxml")
    title = (soup.title.string or "").strip() if soup.title else ""
    fields: list[FormField] = []
    for tag in soup.select("input, textarea, select"):
        ftype = (tag.get("type") or "text").lower()
        name = tag.get("name") or ""
        if tag.name == "textarea":
            ftype = "textarea"
        if tag.name == "select":
            ftype = "select"
        label_text = ""
        label_id = tag.get("id")
        if label_id:
            label_el = soup.select_one(f'label[for="{label_id}"]')
            if label_el:
                label_text = label_el.get_text(strip=True)
        if not label_text:
            parent_label = tag.find_parent("label")
            if parent_label:
                label_text = parent_label.get_text(strip=True)
        required = tag.has_attr("required")
        selector = _selector_for(tag)
        current_value = tag.get("value") or ""
        fields.append(
            classify_field(
                name=name,
                field_type=ftype,
                label=label_text,
                required=required,
                selector=selector,
                current_value=current_value,
            )
        )
    return title, fields


def _selector_for(tag) -> str:
    name = tag.get("name")
    tag_id = tag.get("id")
    tag_type = tag.get("type")
    if tag_id:
        return f"#{tag_id}"
    if name:
        return f'[name="{name}"]'
    if tag_type:
        return f"{tag.name}[type={tag_type}]"
    return tag.name


def inspect_page(page: FormPageProtocol) -> InspectedForm:
    title, fields = parse_form(page.html())
    safe, unsafe = partition_by_safety(fields)
    return InspectedForm(
        url=page.url(),
        title=title,
        fields=tuple(fields),
        safe_count=len(safe),
        blocked_count=len(unsafe),
    )


def fill_safe_fields(
    page: FormPageProtocol,
    values: dict[str, str],
) -> FillResult:
    title, fields = parse_form(page.html())
    safe_map = {f.name: f for f in fields if f.safe_to_fill and f.name}
    filled: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for name, value in values.items():
        field = safe_map.get(name)
        if field is None:
            reason = "field not found or not safe"
            for f in fields:
                if f.name == name:
                    reason = f.safety_reason
                    break
            skipped.append({"name": name, "reason": reason})
            continue
        try:
            page.fill(field.selector, value)
            filled.append({"name": name, "value": value})
        except Exception as exc:
            skipped.append({"name": name, "reason": f"fill failed: {exc}"})
    return FillResult(filled=tuple(filled), skipped=tuple(skipped))


__all__ = [
    "ApplicationSessionRecord",
    "ApplicationSessionStore",
    "FakeFormPage",
    "FillResult",
    "FormPageProtocol",
    "InspectedForm",
    "fill_safe_fields",
    "inspect_page",
    "parse_form",
]
