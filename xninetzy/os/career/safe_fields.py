from __future__ import annotations

from dataclasses import dataclass


_SAFE_INPUT_TYPES = frozenset(
    {"text", "email", "tel", "number", "url", "search", "textarea"}
)
_UNSAFE_INPUT_TYPES = frozenset(
    {"password", "submit", "reset", "button", "file", "image", "hidden"}
)

_SAFE_NAME_HINTS = (
    "name", "full_name", "first", "last", "email", "phone", "mobile",
    "linkedin", "github", "portfolio", "url", "website",
    "summary", "cover", "about", "message", "note",
    "experience", "education", "school", "company",
    "address", "city", "country", "location",
    "title", "role", "position", "headline",
)
_UNSAFE_NAME_HINTS = (
    "password", "pwd", "secret", "token", "apikey", "api_key",
    "credit", "card", "cvv", "ssn", "nik", "ktp",
    "submit", "consent", "agree", "tos",
)


@dataclass(frozen=True)
class FormField:
    name: str
    field_type: str
    label: str
    required: bool
    selector: str
    current_value: str
    safe_to_fill: bool
    safety_reason: str


def classify_field(
    *,
    name: str,
    field_type: str,
    label: str = "",
    required: bool = False,
    selector: str = "",
    current_value: str = "",
) -> FormField:
    ftype = (field_type or "text").lower()
    fname = (name or "").lower()
    is_submit_name = fname in {"submit", "button"}
    is_submit_type = ftype in {"submit", "reset", "button"}
    is_safe_by_type = ftype in _SAFE_INPUT_TYPES
    is_unsafe_by_name = any(hint in fname for hint in _UNSAFE_NAME_HINTS)
    is_safe_by_name = any(hint in fname for hint in _SAFE_NAME_HINTS)
    if is_submit_name or (is_submit_type and not is_safe_by_name and not fname):
        safe = False
        reason = "submit/button element — never filled"
    elif ftype in _UNSAFE_INPUT_TYPES:
        safe = False
        reason = f"unsafe input type '{ftype}'"
    elif is_unsafe_by_name:
        safe = False
        reason = f"name matches unsafe pattern ({fname})"
    elif is_safe_by_type and (is_safe_by_name or not fname):
        safe = True
        reason = "safe input type + neutral/safe name"
    elif is_safe_by_name:
        safe = True
        reason = "name matches safe pattern"
    elif not fname and ftype in _SAFE_INPUT_TYPES:
        safe = True
        reason = "safe input type, no name"
    else:
        safe = False
        reason = f"no safe signal (type={ftype}, name={fname})"
    return FormField(
        name=name,
        field_type=ftype,
        label=label,
        required=required,
        selector=selector,
        current_value=current_value,
        safe_to_fill=safe,
        safety_reason=reason,
    )


def safe_fields(fields: list[FormField]) -> list[FormField]:
    return [f for f in fields if f.safe_to_fill]


def partition_by_safety(fields: list[FormField]) -> tuple[list[FormField], list[FormField]]:
    safe: list[FormField] = []
    unsafe: list[FormField] = []
    for f in fields:
        (safe if f.safe_to_fill else unsafe).append(f)
    return safe, unsafe


__all__ = [
    "FormField",
    "classify_field",
    "partition_by_safety",
    "safe_fields",
]
