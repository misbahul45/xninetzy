from __future__ import annotations

from xninetzy.context.routing.dataset import (
    bucket_domains,
    redact_pii,
    split_temporal,
    write_dataset,
)


def test_redact_pii_removes_email_phone_key() -> None:
    assert "[redacted]" in redact_pii("contact me at foo@bar.com")
    assert "[redacted]" in redact_pii("phone 555-123-4567")
    assert "[redacted]" in redact_pii("api_key=sk-12345 abc")


def test_bucket_domains_returns_at_least_one_for_known_tools() -> None:
    cases = [
        (["hebat_sync_assignments"], "academic"),
        (["research_search_papers"], "research"),
        (["career_search_jobs"], "career"),
        (["video_render"], "media"),
        (["memory_add"], "knowledge"),
    ]
    for tools, expected in cases:
        assert expected in bucket_domains(tools), f"tools={tools} did not produce {expected}"


def test_bucket_domains_handles_unknown() -> None:
    assert bucket_domains(["some_random_tool_xyz"]) == []


def test_split_temporal_returns_iso_strings() -> None:
    a, b, c = split_temporal()
    for s in (a, b, c):
        assert isinstance(s, str) and "T" in s


def test_write_dataset_emits_files_and_curated(tmp_path) -> None:
    result = write_dataset(tmp_path, max_rows=50)
    paths = result["paths"]
    for name in ("raw", "train", "val", "test", "adversarial_curated", "coverage"):
        assert name in paths
        from pathlib import Path as _Path

        p = _Path(paths[name])
        if name != "coverage":
            assert p.exists(), f"{name} missing at {p}"
    assert len(result["adversarial_curated"]) >= 30


def test_write_dataset_idempotent_shape(tmp_path) -> None:
    a = write_dataset(tmp_path, max_rows=20)
    b = write_dataset(tmp_path, max_rows=20)
    from pathlib import Path as _Path

    raw_a = _Path(a["paths"]["raw"]).read_bytes()
    raw_b = _Path(b["paths"]["raw"]).read_bytes()
    assert raw_a == raw_b, "raw.jsonl must be byte-identical across runs"


def test_adversarial_set_contains_paraphrase_pairs(tmp_path) -> None:
    curated = write_dataset(tmp_path, max_rows=0)
    rows = curated["adversarial_curated"]
    texts = [r["input"]["text"] for r in rows]
    assert "find papers on adaptive learning" in texts
    assert "find React tutorials" in texts
    assert "find React internships" in texts
    assert "find remote React jobs" in texts
    assert "show my tasks" in texts
    assert "render it" in texts
