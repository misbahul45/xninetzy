---
name: "xninetzy-obsidian-orchestra"
description: "Structural and navigational operating system for the canonical Xninetzy Obsidian vault. Use for folder/file conventions, course and project structures, migrations, semester archiving, MOCs, frontmatter normalization, Mermaid visualization, vault health, naming integrity, portal-to-Obsidian ingestion, backlink consistency, and safe structural changes. metadata:"
---
type: note|concept|material|assignment|daily|moc
course: COURSE_CODE
course_name: FULL_NAME
semester: "YYYY Period"
tags: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active|archived|draft
---
```

Only include course fields when the note is academic. Do not invent metadata values.

## MOC architecture

MOCs are navigation systems, not content dumps. Use `00 - Index.md`. A course MOC may link Overview, Materials, Assignments, Lecture Notes, Concepts, Projects, and Related Courses. Keep MOCs compact.

## MOC refresh triggers

Refresh MOCs after course creation, significant migration, five or more new notes, semester archival, major renaming, structural reorganization, or user request. Do not regenerate every MOC after every tiny note edit.

## Vault health check

Run health checks for folder structure, naming violations, misplaced files, duplicate notes, orphaned TODOs, broken references, missing frontmatter, FTS/index health, excessive nesting, and stale MOCs.

## Reference map

* `references/migrations-and-safety.md` — migration workflow, preview, safety, naming repair, conflict resolution, frontmatter normalization, idempotency, duplicate detection, broken-link safety, aliases, anti-patterns, and verification after mutation.
* `references/mocs-and-diagrams.md` — MOC architecture, refresh triggers, integrity, nesting limit, inbox, daily, archive, portal-to-Obsidian ingestion, portal naming, portal overview notes, per-page notes, Mermaid standard, diagram mapping, Mermaid syntax, diagram selection rule, and current course reference.
* `references/semesters-and-validation.md` — current vs archive boundary, semester transition, structural vs content operations, safe mutation model, small vs broad changes, semester archives, completion contract, standard health output, and operating rules.

## Routing

* Reading and answering from vault evidence → `obsidian-knowledge`.
* Semantic knowledge querying → `xninetzy-knowledge-answer`.
* HEBAT context → `hebat-academic`.
* Cyber Campus and KRS → `xninetzy-cyber-campus`.
* Cross-session continuity → `xninetzy-memory`.
* Graph relationships → `graph-rag`.

## Operating rules

The system must:

* inspect before restructuring,
* use human-readable canonical names,
* separate active and archived academic content,
* preserve existing valid conventions,
* preview broad mutations,
* preserve content and metadata during migration,
* repair links after structural changes,
* maintain MOCs as navigation systems,
* use Mermaid for meaningful structural/process visualization,
* never fabricate dates in diagrams,
* avoid deep folder nesting,
* keep `Daily/` restricted to daily notes,
* verify actual vault state after mutations,
* avoid duplicate creation through idempotent checks,
* separate structural orchestration from note-content reasoning,
* report incomplete operations honestly.

The central objective is:

> **Maintain one coherent, human-readable, machine-retrievable Obsidian vault in which structure is intentional, naming is canonical, navigation remains usable, and every structural change can be inspected and verified.**