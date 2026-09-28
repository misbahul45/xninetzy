from __future__ import annotations

import hashlib
from pathlib import Path

from xninetzy.context.registry_extractor import (
    compute_drift,
    extract_provider_registry,
    extract_research_sources,
    extract_skill_registry,
    extract_tool_manifest,
    validate_against_schemas,
    write_outputs,
)
from xninetzy.tools.registry import get_tool_names


def test_extract_tool_manifest_is_idempotent() -> None:
    a = extract_tool_manifest()
    b = extract_tool_manifest()
    assert a == b
    assert len(a) == len(get_tool_names())
    assert len(a) > 0


def test_extract_tool_manifest_keys_match_meta_for() -> None:
    m = extract_tool_manifest()
    sample = m[get_tool_names()[0]]
    assert sample["name"] == get_tool_names()[0]
    assert sample["risk"] in {"read", "draft", "write", "final"}
    assert isinstance(sample["tags"], list)
    assert "auto_discovered" in sample
    assert "requires_approval" in sample
    assert "feature_pack" in sample
    assert "stability" in sample


def test_extract_skill_registry_loads_all_skills() -> None:
    s = extract_skill_registry()
    assert len(s) > 0
    for name, entry in s.items():
        assert entry["name"] == name
        assert entry["routing_version"] == "1.0.0"
        assert isinstance(entry["description"], str)
        assert "source" in entry
        assert "path" in entry


def test_extract_provider_registry_families_present() -> None:
    p = extract_provider_registry()
    assert "llm" in p
    assert "external_mcp" in p
    assert len(p["llm"]) >= 5
    for entry in p["llm"]:
        assert entry["name"]
        assert "default_model" in entry
        assert "enabled" in entry


def test_extract_research_sources_counts_at_least_30() -> None:
    s = extract_research_sources()
    assert len(s) >= 30
    for entry in s:
        assert "adapter" in entry
        assert "module_path" in entry
        assert "auto_discovered" in entry


def test_compute_drift_flags_readme_claim(tmp_path: Path) -> None:
    manifest = extract_tool_manifest()
    skills = extract_skill_registry()
    providers = extract_provider_registry()
    sources = extract_research_sources()

    d = compute_drift(
        current_manifest=manifest,
        current_skills=skills,
        current_providers=providers,
        current_sources=sources,
        output_root=tmp_path,
    )
    assert d["drift"]["tool_count"]["claimed_in_README"] == 508
    assert d["drift"]["tool_count"]["actual"] == len(get_tool_names())
    assert d["drift"]["empty_groups_count"] >= 0
    assert d["drift"]["providers"]["llm"] >= 5


def test_validate_against_schemas_for_all_five(tmp_path: Path) -> None:
    payload = write_outputs(tmp_path, write=True, verbose=False)
    for name in ("manifest", "skills", "providers", "research_sources", "drift"):
        assert validate_against_schemas(payload[name], name), f"{name} failed validation"


def test_sha256_sidecars_written(tmp_path: Path) -> None:
    payload = write_outputs(tmp_path, write=True, verbose=False)
    for name, path in payload["paths"].items():
        p = Path(path)
        sha_file = p.with_suffix(p.suffix + ".sha256")
        assert sha_file.exists(), f"missing sidecar for {name}"
        expected = hashlib.sha256(p.read_bytes()).hexdigest()
        assert sha_file.read_text().strip() == expected


def test_idempotent_bytes(tmp_path: Path) -> None:
    fixed_ts = "2026-09-28T00:00:00+00:00"
    a = write_outputs(tmp_path, write=True, verbose=False, generated_at=fixed_ts)
    a_bytes = {n: Path(p).read_bytes() for n, p in a["paths"].items()}
    b = write_outputs(tmp_path, write=True, verbose=False, generated_at=fixed_ts)
    for n, byts in a_bytes.items():
        assert byts == Path(b["paths"][n]).read_bytes(), f"non-idempotent for {n}"


def test_existing_mcp_tool_contracts_unchanged() -> None:
    must_exist = [
        "intent_resolve",
        "skill_route",
        "tool_catalog",
        "tool_rank",
        "tool_route",
        "action_policy_evaluate",
    ]
    names = set(get_tool_names())
    for n in must_exist:
        assert n in names, f"existing tool {n} disappeared from registry"


def test_skill_exists() -> None:
    s = extract_skill_registry()
    assert len(s) >= 1
    assert all(isinstance(k, str) and k for k in s.keys())
