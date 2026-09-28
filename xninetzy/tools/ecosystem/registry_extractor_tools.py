from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from xninetzy.context.registry_extractor import (
    compute_drift,
    extract_provider_registry,
    extract_research_sources,
    extract_skill_registry,
    extract_tool_manifest,
    validate_against_schemas,
    write_outputs,
)
from xninetzy.tools.tool_results import to_tool_result


@tool
def registry_extract(write: bool = False, output_root: str = "data/registry") -> str:
    """Run the Xninetzy routing registry extractor.

    Args:
        write: When True, persist the five JSON manifests + sha256
            sidecars + history entry to disk.
        output_root: Directory under repo root for outputs.

    Returns:
        JSON summary with counts and (when write=True) the
        destination paths and sha256 fingerprints.
    """
    payload = write_outputs(output_root, write=write, verbose=False)
    summary = {
        "ok": True,
        "tool_count": len(payload["manifest"]["tools"]),
        "skill_count": len(payload["skills"]["skills"]),
        "provider_count": sum(
            len(payload["providers"]["providers"].get(family, []) or [])
            for family in ("external_mcp", "llm", "render", "dashboard")
        ),
        "research_source_count": len(payload["research_sources"]["sources"]),
        "paths": payload["paths"],
        "shas": payload.get("shas", {}),
        "drift": payload["drift"]["drift"],
    }
    return to_tool_result(
        f"Routing registry extracted ({summary['tool_count']} tools, "
        f"{summary['skill_count']} skills, "
        f"{summary['provider_count']} providers, "
        f"{summary['research_source_count']} research sources).",
        items=[summary],
        meta={"write": write, "output_root": output_root},
    )


@tool
def registry_drift_summary() -> str:
    """Reload the latest persisted drift summary from data/registry/.

    Returns:
        JSON drift summary or a structured error if no drift file
        has been written yet.
    """
    candidate = Path("data/registry/routing_drift.json")
    if not candidate.exists():
        return to_tool_result(
            "no drift summary on disk; run registry_extract(write=True) first",
            items=[],
            meta={"hint": "run registry_extract(write=True)"},
            ok=False,
        )

    payload = json.loads(candidate.read_text(encoding="utf-8"))
    drift = payload.get("drift", {})
    summary = {
        "tool_count": drift.get("tool_count", {}).get("actual"),
        "tool_count_delta_vs_README": drift.get("tool_count", {}).get("delta"),
        "empty_groups": drift.get("empty_groups", []),
        "skill_count": drift.get("skill_count", {}).get("actual"),
        "skill_count_delta_vs_README": drift.get("skill_count", {}).get("delta"),
        "providers": drift.get("providers", {}),
        "research_source_count": drift.get("research_source_count"),
        "generated_at": payload.get("generated_at"),
    }
    return to_tool_result(
        "Routing drift summary loaded.", items=[summary], meta={"path": str(candidate)}
    )


@tool
def registry_validate(output_root: str = "data/registry") -> str:
    """Validate the five persisted manifests against JSON Schemas.

    Returns:
        JSON `{ok, schema_results}` where schema_results is a dict
        keyed by schema name with `valid: bool` and any error string.
    """
    root = Path(output_root)
    files = {
        "manifest": root / "routing_manifest.json",
        "skills": root / "routing_skills.json",
        "providers": root / "routing_providers.json",
        "research_sources": root / "routing_research_sources.json",
        "drift": root / "routing_drift.json",
    }
    schema_results: dict[str, dict[str, Any]] = {}
    overall_ok = True
    for name, path in files.items():
        if not path.exists():
            schema_results[name] = {"valid": False, "error": "missing"}
            overall_ok = False
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validate_against_schemas(payload, name)
            schema_results[name] = {"valid": True}
        except Exception as exc:
            schema_results[name] = {"valid": False, "error": str(exc)}
            overall_ok = False
    return to_tool_result(
        "Routing registry schema validation finished.",
        items=[{"overall_ok": overall_ok, "results": schema_results}],
        meta={"ok": overall_ok},
    )


registry_extractor_tools = [
    registry_extract,
    registry_drift_summary,
    registry_validate,
]


_ = compute_drift
_ = extract_provider_registry
_ = extract_research_sources
_ = extract_skill_registry
_ = extract_tool_manifest


from typing import Any as _Any  # noqa: E402
_ = _Any
