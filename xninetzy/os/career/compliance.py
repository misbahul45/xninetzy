from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ComplianceClass(StrEnum):
    READ = "read"
    PREPARE = "prepare"
    FILL = "fill"
    SUBMIT = "submit"
    NEVER = "never"


@dataclass(frozen=True)
class SourceCompliance:
    adapter_id: str
    declared_class: ComplianceClass
    tos_url: str
    risk_acknowledged: bool
    notes: str = ""


_DECLARATIONS: dict[str, SourceCompliance] = {
    "remoteok": SourceCompliance(
        adapter_id="remoteok",
        declared_class=ComplianceClass.READ,
        tos_url="https://remoteok.com/terms",
        risk_acknowledged=True,
        notes="Public JSON API; documented rate limits.",
    ),
    "arbeitnow": SourceCompliance(
        adapter_id="arbeitnow",
        declared_class=ComplianceClass.READ,
        tos_url="https://www.arbeitnow.com/terms",
        risk_acknowledged=True,
        notes="Public JSON API; documented.",
    ),
    "kalibrr": SourceCompliance(
        adapter_id="kalibrr",
        declared_class=ComplianceClass.READ,
        tos_url="https://www.kalibrr.com/terms",
        risk_acknowledged=True,
        notes="Owner-gated browser; ToS allows limited revocable access. R6 risk accepted.",
    ),
    "glints": SourceCompliance(
        adapter_id="glints",
        declared_class=ComplianceClass.READ,
        tos_url="https://glints.com/terms",
        risk_acknowledged=True,
        notes="Owner-gated browser; R6 risk accepted.",
    ),
    "dealls": SourceCompliance(
        adapter_id="dealls",
        declared_class=ComplianceClass.READ,
        tos_url="https://dealls.com/terms",
        risk_acknowledged=True,
        notes="Owner-gated browser; R6 risk accepted.",
    ),
    "jobstreet_id": SourceCompliance(
        adapter_id="jobstreet_id",
        declared_class=ComplianceClass.NEVER,
        tos_url="https://id.jobstreet.com/terms",
        risk_acknowledged=False,
        notes="SEEK Asia ToS explicitly restricts automated access. Read-only when feasible; autonomous writes NEVER.",
    ),
}


def declare(adapter_id: str, *, tos_url: str, declared_class: ComplianceClass, risk_acknowledged: bool = True, notes: str = "") -> SourceCompliance:
    """Register or update an adapter's compliance declaration."""
    record = SourceCompliance(
        adapter_id=adapter_id,
        declared_class=declared_class,
        tos_url=tos_url,
        risk_acknowledged=risk_acknowledged,
        notes=notes,
    )
    _DECLARATIONS[adapter_id] = record
    return record


def get(adapter_id: str) -> SourceCompliance | None:
    return _DECLARATIONS.get(adapter_id)


def all_declarations() -> tuple[SourceCompliance, ...]:
    return tuple(_DECLARATIONS.values())


def audit(adapter_ids: tuple[str, ...] | None = None) -> dict[str, Any]:
    targets = adapter_ids or tuple(_DECLARATIONS.keys())
    rows = [_DECLARATIONS[aid] for aid in targets if aid in _DECLARATIONS]
    drift = [r.adapter_id for r in rows if not r.risk_acknowledged and r.declared_class != ComplianceClass.NEVER]
    return {
        "status": "ok" if not drift else "drift",
        "total_adapters": len(rows),
        "drift": drift,
        "rows": [
            {
                "adapter": r.adapter_id,
                "class": r.declared_class.value,
                "tos_url": r.tos_url,
                "risk_acknowledged": r.risk_acknowledged,
                "notes": r.notes,
            }
            for r in rows
        ],
    }


def can_perform(adapter_id: str, action: ComplianceClass) -> tuple[bool, str]:
    declaration = _DECLARATIONS.get(adapter_id)
    if declaration is None:
        return False, f"no compliance declaration registered for {adapter_id}"
    if declaration.declared_class == ComplianceClass.NEVER:
        return False, f"{adapter_id} is NEVER class — no automated access"
    allowed = {
        ComplianceClass.READ: {ComplianceClass.READ},
        ComplianceClass.PREPARE: {ComplianceClass.READ, ComplianceClass.PREPARE},
        ComplianceClass.FILL: {ComplianceClass.READ, ComplianceClass.PREPARE, ComplianceClass.FILL},
        ComplianceClass.SUBMIT: {
            ComplianceClass.READ,
            ComplianceClass.PREPARE,
            ComplianceClass.FILL,
            ComplianceClass.SUBMIT,
        },
    }
    if action not in allowed[declaration.declared_class]:
        return False, (
            f"{adapter_id} class is {declaration.declared_class.value}; "
            f"requested action {action.value} not permitted"
        )
    return True, "ok"


__all__ = [
    "ComplianceClass",
    "SourceCompliance",
    "all_declarations",
    "audit",
    "can_perform",
    "declare",
    "get",
]
