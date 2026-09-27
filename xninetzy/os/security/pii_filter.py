from __future__ import annotations

import logging
import re


_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("phone_id", re.compile(r"\+?62[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,5}")),
    ("phone_e164", re.compile(r"\+\d{1,3}[\s\-]?\d{3,4}[\s\-]?\d{3,4}[\s\-]?\d{3,5}")),
    ("nik", re.compile(r"\b\d{16}\b")),
    ("card", re.compile(r"\b(?:\d[ \-]?){13,16}\d\b")),
    ("token_bearer", re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}")),
    ("token_basic", re.compile(r"(?i)basic\s+[A-Za-z0-9._\-]{20,}")),
    ("token_api_key", re.compile(r"(?i)(?:api[_\-]?key|access[_\-]?token)[\"':=\s]+[A-Za-z0-9._\-]{16,}")),
    ("cookie_session", re.compile(r"(?i)(?:session|sid|phpsessid)=[A-Za-z0-9]{16,}")),
)


class PIIRedactionFilter(logging.Filter):
    def __init__(self, *, name: str = "") -> None:
        super().__init__(name)
        self._counts: dict[str, int] = {label: 0 for label, _ in _PII_PATTERNS}

    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.msg, str):
            return True
        redacted, hits = redact_pii(record.msg)
        if hits:
            for label, count in hits.items():
                self._counts[label] = self._counts.get(label, 0) + count
            record.msg = redacted
            record.pii_redacted = True  # type: ignore[attr-defined]
            record.pii_redaction_counts = hits  # type: ignore[attr-defined]
        return True

    def summary(self) -> dict[str, int]:
        return dict(self._counts)


def redact_pii(text: str) -> tuple[str, dict[str, int]]:
    if not text:
        return text, {}
    counts: dict[str, int] = {}
    out = text
    for label, pattern in _PII_PATTERNS:
        out, n = pattern.subn(f"[REDACTED:{label}]", out)
        if n > 0:
            counts[label] = counts.get(label, 0) + n
    return out, counts


def install_pii_filter(logger: logging.Logger | None = None) -> PIIRedactionFilter:
    target = logger or logging.getLogger()
    flt = PIIRedactionFilter()
    for handler in target.handlers:
        if not any(isinstance(existing, PIIRedactionFilter) for existing in handler.filters):
            handler.addFilter(flt)
    if not any(isinstance(h, PIIRedactionFilter) for h in target.filters):
        target.addFilter(flt)
    return flt


def pii_summary(filter_instance: PIIRedactionFilter) -> dict[str, int]:
    return filter_instance.summary()
