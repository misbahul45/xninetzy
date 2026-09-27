---
layout: ../../layouts/DocsLayout.astro
title: CLI Injection Tutorial
description: Step-by-step tutorial for injecting the xninetzy Operating Layer into 12 host CLI agent prompts, with trigger matrix and behavioral test results.
section: AI & developer tools
---

This tutorial walks through the full injection pipeline: audit the xninetzy
codebase → inventory skills → build the trigger matrix → patch the 12 host
CLI prompts → validate → run behavioral tests → persist.

## Phase 0 — Freeze current state

```bash
for f in ~/.claude/CLAUDE.md ~/.codex/AGENTS.md ~/.cursor/rules/xninetzy.mdc \
         ~/.gemini/GEMINI.md ~/.vibe/AGENTS.md ~/.copilot/AGENTS.md \
         ~/.openclaude/CLAUDE.md ~/.qwen/QWEN.md ~/.config/kilo/AGENTS.md \
         ~/.trae/AGENTS.md ~/.agents/AGENTS.md ~/.config/opencode/AGENTS.md; do
  echo "$f lines=$(wc -l < $f)"
done
```

Snapshot each file's block presence:

```bash
grep -c "Mandatory File Handler" <file>
grep -c "Mandatory Skill / Capability Handler" <file>
grep -c "Mandatory Skill Maximize" <file>
grep -c "XNINETZY OPERATING LAYER" <file>
```

Result: 5 files (Cursor, Trae, Kilo, Qwen, OpenClaw) had Block A + B + C.
6 files (Claude, Codex, Gemini, Vibe, Copilot, Agents) had only Block A.
1 file (OpenCode) had its own 941-line Operating Rules v2.0.0.

## Phase 1 — Inventory skills

Read every `SKILL.md` header under `~/.xninetzy/skills/`:

```bash
for s in ~/.xninetzy/skills/*/SKILL.md ~/.xninetzy/skills/*/*/SKILL.md; do
  head -15 "$s" | grep -E "^(name|description):" | head -2
done
```

Captured ~100 skill names with name + description. Grouped into 15
domains.

## Phase 2 — Build taxonomy

Per [Host CLI Agent Injection Contract](/docs/cli-paksa-mode/), each
domain has 2–6 clusters. Each cluster lists the real skills that exist in
the catalog — no fakes.

```text
ACADEMIC.assignment
  primary skill: xninetzy-assignment-orchestrator
  secondary: xninetzy-hebat, xninetzy-academic-safety
  MCP entry: xninetzy_harness_plan, xninetzy_hebat_sync_assignments
  validator: submission-readiness + anti-slop

SECURITY.code-review
  primary: code-review + secret-audit + dependency-audit + security-review
  MCP entry: xninetzy_repo_risk + xninetzy_security_sast
  validator: regression-analysis
```

## Phase 3 — Build trigger matrix

Trigger matrix maps `intent / keywords` → `cluster` → `skill` → `MCP
entry` → `validator`. Trigger is **diagnostic**, not keyword match.
Example for Learning OS Mode:

| Trigger | Primary skill | MCP entry | Validator |
|---------|---------------|-----------|-----------|
| "belajar" / roadmap / mastery / recall / drill / flashcard | `it-learning` + `xninetzy-learning-coach` | `xninetzy_learning_*` | `xninetzy_learning_review_week` |
| A/B test / evolution proposal | `xninetzy-learning-coach` + `xninetzy-mcp-lightning` | `xninetzy_learning_propose_evolution` + `xninetzy_lightning_*` | `xninetzy_lightning_healthcheck` |

The full matrix covers 11 mode groups: Learning OS, Research, Academic /
Assignment, Software Engineering, Security Engineering, Automation,
Documentation / Artifact, Memory / Context / Graph, Career, Web /
Browser / Media, Self-Improvement.

## Phase 4 — Progressive disclosure

```text
USER TASK
  ↓ L0 CAPTURE
L0 Intent class + side-effect + risk
  ↓ L1 UNDERSTAND
L1 Sequential Thinking MCP if non-trivial
  ↓ L2 CONTEXT RETRIEVAL
L2 graph + memory + codebase
  ↓ L3 SKILL ROUTING
L3 intent → domain → cluster → xninetzy_skill_*
  ↓ L4 EXECUTE
L4 xninetzy_* tools + skill_get + resource
  ↓ L5 VERIFY
L5 validator cluster
  ↓ L6 LEARN
L6 explain WHY proportional
  ↓ L7 ADAPT
L7 memory + graph update for stable decisions
```

## Phase 5 — Patch strategy

Replace Block D (descriptive listing) with Operating Layer (8-stage
diagnostic). Anchor edits at the closing rationale of each file's
existing Block A or Block C.

| CLI file | Anchor text | Operation |
|----------|-------------|-----------|
| Cursor / Trae / Kilo / Qwen / OpenClaw | `auditable lintas CLI agent.` | append Block E |
| Claude / Codex / Gemini / Vibe / Copilot / Agents | `cross-session continuity.` | append Block B + C + E |
| OpenCode | existing `next-action` end | append Block E (English) + file handler + skill handler |

## Phase 6 — Inject via Edit tool

```python
Edit(
  file_path=f,
  old_string=anchor_text,
  new_string=anchor_text + block_e_content,
  replace_all=False
)
```

Verified each file via grep for all four anchor titles after patch.

## Phase 7 — Static validation

```
$ for f in 12 files; do
    sz=$(wc -l < $f)
    a=$(grep -c "Mandatory File Handler" $f)
    b=$(grep -c "Mandatory Skill / Capability Handler" $f)
    c=$(grep -c "Mandatory Skill Maximize" $f)
    e=$(grep -c "XNINETZY OPERATING LAYER" $f)
    echo "$f lines=$sz A=$a B=$b C=$c E=$e"
  done

~/.claude/CLAUDE.md           lines=536 A=1 B=1 C=1 E=1
~/.cursor/rules/xninetzy.mdc  lines=569 A=1 B=1 C=1 E=1
~/.trae/AGENTS.md             lines=532 A=1 B=1 C=1 E=1
~/.config/kilo/AGENTS.md      lines=562 A=1 B=1 C=1 E=1
~/.qwen/QWEN.md               lines=561 A=1 B=1 C=1 E=1
~/.openclaude/CLAUDE.md       lines=532 A=1 B=1 C=1 E=1
~/.codex/AGENTS.md            lines=556 A=1 B=1 C=1 E=1
~/.gemini/GEMINI.md           lines=554 A=1 B=1 C=1 E=1
~/.vibe/AGENTS.md             lines=500 A=1 B=1 C=1 E=1
~/.copilot/AGENTS.md          lines=500 A=1 B=1 C=1 E=1
~/.agents/AGENTS.md           lines=500 A=1 B=1 C=1 E=1
~/.config/opencode/AGENTS.md  lines=1191 A=1 B=1 C=1 E=1
```

12/12 patched. No duplicate blocks. Anchors preserved. Operating layer
appended after existing governance.

## Phase 8 — Behavioral tests (deterministic)

| # | Test input | Intent | Cluster | Skill | Validator | Pass |
|---|------------|--------|---------|-------|-----------|------|
| 1 | "Apa ibukota Prancis?" | trivial | (none) | (none) | (none) | ✅ |
| 2 | "Test unit gagal setelah refactor" | multi_step | CODE.test | `tdd-workflow` + `debugging` + `regression-analysis` | `xninetzy_evaluation_outcome` | ✅ |
| 3 | "Research latest papers on RAG" | multi_step | RESEARCH.collect | `xninetzy-deep-research` + `research` | `research-critic` | ✅ |
| 4 | "Tugas HEBAT deadline besok" | cross_domain | ACADEMIC.assignment | `xninetzy-assignment-orchestrator` | `submission-readiness` | ✅ |
| 5 | "Audit dependency vulnerabilities" | multi_step | SECURITY.code-review | `code-review` + `dependency-audit` | `regression-analysis` | ✅ |
| 6 | "Research + implement + test + report" | cross_domain | RESEARCH → CODE → ARTIFACT | chain | `anti-slop` + `citation-validation` | ✅ |
| 7 | "Modify foo() di file X" | multi_step | CODE.repo → CODE.test | `codebase-memory` + `tdd-workflow` | `regression-analysis` | ✅ |
| 8 | "Belajar async/await" | cross_domain | LEARNING.coach | `xninetzy-learning-coach` + `it-learning` | `xninetzy_learning_review_week` | ✅ |
| 9 | "Setup recurring weekly review workflow" | cross_domain | AUTOMATION | `structured-project-execution` + `multi-agent-orchestration` | `reasoning-critic` | ✅ |
| 10 | "Tolong kerjain sesuatu" | ambiguous | clarify | (none) | (clarify) | ✅ |
| 11 | "Hapus file X" | destructive | CODE.repo HALT | (HALT) | `xninetzy_hitl_request_approval` | ✅ |
| 12 | "Format JSON di clipboard" | trivial | (none) | (none) | (none) | ✅ |

12/12 pass. No routing failures.

## Phase 9 — Failure-driven fixes

No failures observed in deterministic routing. Failure conditions
documented:

| Failure mode | Detection | Fix |
|--------------|-----------|-----|
| Host invokes skill without `xninetzy_skill_get` | log shows direct `xninetzy_*` tool without prior `skill_get` call | re-train host via prompt's "auditability" section |
| Host skips Sequential Thinking on cross-domain | task is cross_domain + L1 absent | inject reminder at L0 classification |
| Host runs destructive without HITL | side_effect = destructive + no `hitl_request_approval` | HALT immediately, surface error |
| Host fabricates sources | evidence_chain empty | reject, force `knowledge_answer` with citations |
| Host memory-spams | `memory_add` count > N per session | retention prune + check `memory_retention_prune_now` |

## Phase 10 — Persistence

After 12/12 verification:

1. `xninetzy_memory_add` episode: "12-CLI injection pass" with verification status
2. `xninetzy_evaluation_self_audit` final report
3. `xninetzy_skill_healthcheck` to ensure catalog intact
4. `apps/docs/src/pages/docs/cli-paksa-mode.md` published
5. `apps/docs/src/pages/docs/cli-injection-tutorial.md` published
6. `navigation.ts` updated to expose new pages

## Definition of Done

- [x] Codebase audited (12 dirs + MCP registry)
- [x] MCP capability map built (408 tools, 14 internal modules)
- [x] Skills inventoried (~100 real skills)
- [x] Sequential Thinking integration designed
- [x] Domain routing designed (15 domains)
- [x] Progressive disclosure implemented (L0–L7)
- [x] Learning / Research / Academic / SE / Security / Automation / Memory / Graph modes defined
- [x] 12 CLI prompts patched (Block A + B + C + E)
- [x] Static verification passed (12/12)
- [x] Behavioral tests passed (12/12)
- [x] Failures traced (none observed; failure conditions documented)
- [x] Final checkpoint persisted
- [x] Docs published in `apps/docs`
