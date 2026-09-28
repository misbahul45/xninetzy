from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from xninetzy.context.routing.laya import LayaDecision


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    schema_version: str = "1.0"
    chat_id: str = ""
    owner_hash: str = ""
    active_projects: tuple[dict[str, Any], ...] = ()
    active_sessions: tuple[dict[str, Any], ...] = ()
    browser_sessions: tuple[dict[str, Any], ...] = ()
    available_artifacts: tuple[dict[str, Any], ...] = ()
    authentication_state: dict[str, str] = field(default_factory=dict)
    provider_health: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RouterLayerDecision:
    layer: str
    query: str
    selected: tuple[str, ...]
    confidence: dict[str, float] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    abstained: bool = False
    latency_ms: float = 0.0
    laya_decision: LayaDecision | None = None
    shortlist_size: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


def build_state_snapshot(*, chat_id: str = "", owner_hash: str = "") -> StateSnapshot:
    from pathlib import Path

    active_projects: list[dict[str, Any]] = []
    state_root = Path("data/routing_state")
    state_root.mkdir(parents=True, exist_ok=True)
    candidates = state_root / "active_projects.json"
    if candidates.exists():
        try:
            import json as _json

            active_projects = _json.loads(candidates.read_text(encoding="utf-8"))
        except Exception:
            active_projects = []
    return StateSnapshot(
        chat_id=chat_id,
        owner_hash=owner_hash,
        active_projects=tuple(active_projects),
    )


def state_influenced_rerank(score: float, *, state: StateSnapshot | None, requires_state: tuple[str, ...] = ()) -> float:
    if state is None or not requires_state:
        return score
    has_all = True
    for req in requires_state:
        if req.startswith("project."):
            token = req.split(".", 1)[1]
            if not any(token in p.get("kind", "") for p in state.active_projects):
                has_all = False
                break
    return score if has_all else score * 0.5
