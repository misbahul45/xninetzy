---
name: 2026-09-24-hebat-list-course-activities
description: Add MCP tool `hebat_list_course_activities` that reads HEBAT activities from local SQLite cache, replacing the truncated display of `hebat_sync_course_activities`.
metadata:
  type: design
  date: 2026-09-24
  scope: project
  status: approved
  authority:
    - AGENTS.md
---

# HEBAT List Course Activities — 2026-09-24

## Problem

`hebat_sync_course_activities` (in `xninetzy/os/academic/hebat/tools.py`)
synchronises all course activities into the local SQLite cache, but the
response body is truncated:

```python
for a in activities[:15]:
    ...
if len(activities) > 15:
    lines.append(f"... dan {len(activities) - 15} activity lainnya")
```

Concrete impact observed 2026-09-24 during a real session:

- Course `SII209 - Desain Interaksi (praktikum)` has **18 activities**.
  Display shows the first 15 plus `... dan 3 activity lainnya`.
- Course `SII208 - Desain Interaksi` has **24 activities**.
  Display shows the first 15 plus `... dan 9 activity lainnya`.

The hidden portion contains the very activities the owner is looking for
(an assignment titled `User Persona` is in the truncated tail of `SII209`).
This forces a manual trip to the HEBAT web UI to discover which course
hosts a given assignment title.

## Goal

Expose the **already-populated** SQLite cache via a new MCP tool so owners
can list, filter, and search activities without truncation.

## Non-goals

- Re-fetching from the HEBAT server (read-only tool — sync is its own
  operation).
- Paginated streaming responses (the cache is small; a single response is
  sufficient when `limit ≤ 200`).
- Editing activity metadata.

## Design

### Tool signature

```python
@tool
def hebat_list_course_activities(
    course_id: str | None = None,
    activity_type: str | None = None,
    search: str | None = None,
    limit: int = 50,
) -> str
```

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `course_id` | `str \| None` | `None` | Moodle course id. `None` = all courses. |
| `activity_type` | `str \| None` | `None` | `assign`, `resource`, `quiz`, `forum`, etc. `None` = all types. |
| `search` | `str \| None` | `None` | Case-insensitive substring match against `title`. `None` = no search. |
| `limit` | `int` | `50` | Maximum rows returned. Clamped to `[1, 200]`. |

### Tier and risk

- **Tier 0** — read-only, idempotent, no side effects.
- **RiskClass** — `READ` (per `xninetzy/tools/manifest.py` classification).
- **Confirmation** — none.

### Behaviour

1. Call `list_activities(course_id, activity_type)` from
   `xninetzy/os/academic/hebat/storage.py` (already exists, already imports
   cleanly into `tools.py` line 40).
2. If `search` is provided, filter Python-side with
   `title.lower().contains(search.lower())`.
3. Sort by `(course_id, section_title, title)`.
4. Clamp `limit` to `[1, 200]`.
5. Slice to `limit` rows.
6. Group rows by `course_id` when no `course_id` filter is supplied;
   otherwise emit a single flat list.
7. Format as a Markdown-friendly text response. If the slice is shorter
   than the post-search total, append a single line
   `(N more — naikkan limit atau pakai search untuk mempersempit)`.

### Output format

Single-course response:

```text
📋 Activities SII209 (7 ditemukan):

[Pertemuan 1] Pengumpulan Tugas Individu 1 (`assign`)
[Pertemuan 2] Wadah Pengumpulan Tugas Individu 2 (`assign`)
[Pertemuan 3] Wadah Pengumpulan Tema (`assign`)
[Pertemuan 4] Wadah Pengumpulan Progress ke-1 (`assign`)
[Pertemuan 5] Wadah Pengumpulan Progress ke-2 (`assign`)
[General] Template Laporan UAS (`resource`)
[Pertemuan 7] User Persona (`assign`)

Total: 7. Sync terakhir: 2026-09-24 06:12 UTC.
```

Multi-course response (no `course_id` filter):

```text
📋 Activities (42 ditemukan, grouped by course):

=== SII208 - Desain Interaksi ===
[General] Kontrak Perkuliahan (`resource`)
...

=== SII209 - Desain Interaksi (Praktikum) ===
...
```

### Empty / error states

- Cache empty for the given filter →

  ```text
  Belum ada activity di cache untuk filter ini.
  Jalankan `hebat_sync_course_activities(course_id=...)` dulu.
  ```

- Cache entirely empty →

  ```text
  Belum ada activity sama sekali.
  Jalankan `hebat_sync_courses` lalu `hebat_sync_course_activities`.
  ```

### Constraints honoured

- **§10 No comments** — function body carries zero `#`, zero docstring,
  zero inline trailing comments. Self-describing names only.
- **§2.3 Architecture boundary** — implementation lives in
  `xninetzy/os/academic/hebat/tools.py`; no `httpx`, no `fastapi`, no MCP
  primitives imported.
- **§15 Idempotency** — read-only, no `idempotency_key` required.
- **§19 Completion contract** — tests cover new invariants;
  `AGENTS.md`, `README.md`, and implementation stay consistent.

## File changes

| File | Change |
|------|--------|
| `xninetzy/os/academic/hebat/tools.py` | Add `hebat_list_course_activities` after `hebat_sync_course_activities` (≈ line 422). ~50 LOC. |
| `tests/os/academic/hebat/test_hebat_list_course_activities.py` | New test file. ~150 LOC. |

No registry edit required — the `@tool` decorator + the existing
`xninetzy/tools/registry.py` autodiscovery picks up new functions.

## Testing

`pytest` cases (RED first, GREEN second):

1. `test_returns_helpful_message_when_cache_empty`
2. `test_returns_single_course_list_when_course_id_filtered`
3. `test_groups_by_course_when_no_course_id_filter`
4. `test_filters_by_activity_type`
5. `test_search_matches_title_substring_case_insensitive`
6. `test_limit_clamps_negative_to_one`
7. `test_limit_clamps_over_200_to_200`
8. `test_suggests_running_sync_when_no_match`
9. `test_round_trip_sync_then_list` (integration: populate via
   `hebat_sync_course_activities` with mocked `fetch_course_activities`,
   then list).

Pattern follows `tests/os/academic/hebat/test_hebat_sync_performance.py`
(mock storage via `unittest.mock.patch`, `pytest.mark.asyncio` where
needed; this tool itself is sync so no async marker).

## Acceptance criteria

- `uv run pytest tests/os/academic/hebat/test_hebat_list_course_activities.py -ra` passes.
- `uv run pytest -ra` (full suite) shows no new failures.
- `uv run ruff check xninetzy tests` reports zero violations.
- `uv run ruff format --check xninetzy tests` reports zero diffs.
- Manual smoke: log into HEBAT, run `hebat_sync_course_activities` for
  `SII209`, then `hebat_list_course_activities(course_id="10974")`
  returns the full 18 entries (instead of the previous 15 + truncation).
- The function file `tools.py` contains zero comments and zero docstrings
  on the new function (verified by `grep -E '^\s*#|"""|'\''\''\s*$'`
  returning nothing on the new function block).
