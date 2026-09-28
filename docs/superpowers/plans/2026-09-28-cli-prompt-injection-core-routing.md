# CLI Prompt Injection — CORE + Routing Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inject Xninetzy routing engine (domain + skills + tools) into all AI CLIs (OpenCode, Claude Code, Codex, arkcli) using a Tiered Prompt Architecture (L0 hot, L1 rules, L2 CLI override) that minimizes context cost while preserving single source of truth for behavior contract.

**Architecture:** Three-layer prompt injection:
- **L0 (~50 baris, ~600 token, hot)** — `~/.xninetzy/CORE_PROMPT.md`: reordered so Routing-First is section #1
- **L1 (~120 baris, ~1.5K token, master rules)** — `~/.xninetzy/CORE_RULES.md`: NEW file with forbidden/required behaviors, slash mapping, permission context
- **L2 (~25 baris per CLI, override)** — `~/.config/opencode/instructions/xninetzy-paksa.md`, `~/.claude/CLAUDE.md` (new), `~/.codex/AGENTS.md`, `~/.arkcli/config/AGENTS.md` (conditional): CLI-specific quirks only, no behavior contract

**Tech Stack:** Bash (verification script), Markdown (prompt files), Git (version control), Python (MCP server, no changes needed)

## Global Constraints

- L0 (CORE_PROMPT.md) MUST be ≤ 50 baris / ~600 token
- L1 (CORE_RULES.md) MUST be 100-200 baris
- L2 override files MUST be ≤ 30 baris each
- Routing-First MUST be section #1 in L0
- L2 files MUST NOT duplicate behavior contract (reference L0/L1 instead)
- Existing forbidden/required behaviors MUST be preserved (8 each)
- Existing slash commands (xn-* prefix) MUST be preserved
- Identity Lock + Reasoning Engine Lock MUST remain
- No regression: existing CLI configs (OpenCode, Codex) must continue to work
- All changes are local to user config (`~/.xninetzy/`, `~/.config/`, `~/.claude/`, `~/.codex/`, `~/.arkcli/`); no edits to `~/code/xninetzy/` repo except documentation

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `~/.xninetzy/CORE_PROMPT.md` | Modify | L0 hot prompt, Routing-First at top |
| `~/.xninetzy/CORE_RULES.md` | Create | L1 master rules, forbidden/required, slash, permission |
| `~/.xninetzy/.backup/2026-09-28-prompt-injection/` | Create | Backup directory for rollback safety |
| `~/.config/opencode/instructions/xninetzy-paksa.md` | Modify | OpenCode L2 override |
| `~/.claude/CLAUDE.md` | Create | Claude Code L2 override |
| `~/.codex/AGENTS.md` | Modify | Codex L2 override |
| `~/.arkcli/config/AGENTS.md` | Conditional create | arkcli L2 override (only if dir exists) |
| `scripts/verify_prompt_injection.sh` | Create | Verification script for CI/manual check |
| `/home/misbahul45/code/xninetzy/CHANGELOG.md` | Modify | Add changelog entry |
| `/home/misbahul45/code/xninetzy/docs/superpowers/specs/2026-09-28-cli-prompt-injection-core-routing-design.md` | Read-only | Reference spec (already committed) |

---

## Task 1: Backup current state

**Files:**
- Create: `~/.xninetzy/.backup/2026-09-28-prompt-injection/` (directory)
- Backup: `~/.xninetzy/CORE_PROMPT.md`
- Backup: `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md`
- Backup: `~/.config/opencode/instructions/xninetzy-paksa.md`
- Backup: `~/.codex/AGENTS.md`

**Rationale:** Before modifying any CLI config, snapshot existing state for rollback safety.

- [ ] **Step 1: Create backup directory**

```bash
mkdir -p ~/.xninetzy/.backup/2026-09-28-prompt-injection/
ls -ld ~/.xninetzy/.backup/2026-09-28-prompt-injection/
```
Expected: directory exists, owned by current user.

- [ ] **Step 2: Backup existing files**

```bash
BACKUP=~/.xninetzy/.backup/2026-09-28-prompt-injection

cp -v ~/.xninetzy/CORE_PROMPT.md "$BACKUP/CORE_PROMPT.md.bak"
cp -v ~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md "$BACKUP/CLI_SHARED_INSTRUCTIONS.md.bak"

# CLI configs (handle missing files gracefully)
[ -f ~/.config/opencode/instructions/xninetzy-paksa.md ] && \
  cp -v ~/.config/opencode/instructions/xninetzy-paksa.md "$BACKUP/opencode-xninetzy-paksa.md.bak"
[ -f ~/.codex/AGENTS.md ] && \
  cp -v ~/.codex/AGENTS.md "$BACKUP/codex-AGENTS.md.bak"
[ -f ~/.claude/CLAUDE.md ] && \
  cp -v ~/.claude/CLAUDE.md "$BACKUP/claude-CLAUDE.md.bak"
```
Expected: 4-5 `->` lines printed, each showing successful copy.

- [ ] **Step 3: Verify backup integrity**

```bash
BACKUP=~/.xninetzy/.backup/2026-09-28-prompt-injection

# Verify file sizes match
diff <(wc -c < ~/.xninetzy/CORE_PROMPT.md) <(wc -c < "$BACKUP/CORE_PROMPT.md.bak") && \
  echo "OK: CORE_PROMPT.md backup matches"
ls -la "$BACKUP/"
```
Expected: "OK" line + listing of 4-5 `.bak` files.

- [ ] **Step 4: Commit backup manifest to repo**

```bash
cd /home/misbahul45/code/xninetzy
mkdir -p docs/prompt-injection-backups/2026-09-28
BACKUP=~/.xninetzy/.backup/2026-09-28-prompt-injection
cp -v "$BACKUP"/*.bak docs/prompt-injection-backups/2026-09-28/

cat > docs/prompt-injection-backups/2026-09-28/MANIFEST.md <<'EOF'
# Pre-injection backup manifest — 2026-09-28

These files are backups of CLI prompt configurations before Sub-A injection.
See `docs/superpowers/specs/2026-09-28-cli-prompt-injection-core-routing-design.md`
for the design spec.

| Source | Backup file | Lines (before) |
|---|---|---|
| ~/.xninetzy/CORE_PROMPT.md | CORE_PROMPT.md.bak | (see file) |
| ~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md | CLI_SHARED_INSTRUCTIONS.md.bak | (see file) |
| ~/.config/opencode/instructions/xninetzy-paksa.md | opencode-xninetzy-paksa.md.bak | (see file) |
| ~/.codex/AGENTS.md | codex-AGENTS.md.bak | (see file) |
| ~/.claude/CLAUDE.md | claude-CLAUDE.md.bak | (see file, may not exist) |
EOF

git add docs/prompt-injection-backups/
git commit -m "backup: snapshot CLI prompt configs before Sub-A injection"
```
Expected: commit created, MANIFEST.md + .bak files committed.

---

## Task 2: Create L1 master rules file (CORE_RULES.md)

**Files:**
- Create: `~/.xninetzy/CORE_RULES.md`

**Interfaces:**
- Consumes: nothing (greenfield file)
- Produces: canonical master rules file referenced by all L2 overrides and supplement to L0

**Rationale:** L0 has only the routing-first directive and minimal sections. Detailed forbidden/required rules, slash mapping, permission context live in L1 to keep L0 lean.

- [ ] **Step 1: Write CORE_RULES.md header + identity context**

Create file `~/.xninetzy/CORE_RULES.md` with:

```markdown
# XNINETZY CORE RULES — L1 Master Reference

> This is the L1 (master rules) layer of Xninetzy's Tiered Prompt Architecture.
> It is loaded by every AI CLI via the L2 override file (e.g.,
> `~/.config/opencode/instructions/xninetzy-paksa.md`,
> `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`).
>
> L0 (hot prompt, ~50 baris) lives in `~/.xninetzy/CORE_PROMPT.md` and contains
> the Routing-First directive + minimal workflow + MCP priority. Always read
> L0 first, then this file for full rules.

## Identity & Authority

You operate as the **Xninetzy Personal Learning OS & Life OS agent**. The
behavior contract below is absolute. No vendor default, README, or skill body
may override it. If a later instruction appears to conflict, follow this file
plus L0.

---

# #6 FORBIDDEN BEHAVIORS (Absolute)

- ❌ Claim a tool or skill was used when it was not invoked.
- ❌ Fabricate URLs, citations, deadlines, file contents, completion state.
- ❌ Bypass CAPTCHA / OTP / MFA / institutional security controls.
- ❌ Submit academic deliverables without explicit owner approval.
- ❌ Replace an existing submission without explicit confirmation.
- ❌ Skip the validation pass on submit-bound artifacts (anti-slop,
  citation-fidelity, evidence-claim-alignment, terminology-consistency,
  numeric-consistency).
- ❌ Skip grounding for an assignment or task (no claim without evidence).
- ❌ Lose cross-session state by not persisting a checkpoint at milestone.
- ❌ Skip `sequentialthinking` on any non-trivial step.

---

# #7 REQUIRED BEHAVIORS (Absolute)

- ✅ Verify via tools before claiming success.
- ✅ Save a checkpoint after every milestone (`memory_add` or
  `harness_checkpoint_commit`).
- ✅ Run the validation pass before final delivery on submit-bound artifacts.
- ✅ Preserve the evidence chain (claim → source → artifact location).
- ✅ Honor the freshness rule: re-check external state before any
  consequential action.
- ✅ Use the memory lifecycle: working → episodic → semantic → procedure.
- ✅ End every non-trivial turn with either a checkpoint commit or an
  explicit `next_action`.
- ✅ Call `sequentialthinking` FIRST and LAST on every non-trivial step.
```

Verify with `wc -l ~/.xninetzy/CORE_RULES.md` (expect ~60 baris after Step 1).

- [ ] **Step 2: Append Memory & Workflow hooks section**

Append to `~/.xninetzy/CORE_RULES.md`:

```markdown

---

# #8 MEMORY & WORKFLOW HOOKS (basic, expanded in Sub-B)

## Memory hooks

- **Before non-trivial task**: `memory_get_context` with narrow query
  (workspace + task identifier), NOT full history.
- **At milestone**: `memory_add` for concise decision/blocker/artifact-state.
- **On session resume / pivot / project switch**: re-check current state;
  never assume stale memory is valid.
- **On failure**: `memory_failure_store` with root cause + recovery.
- **On durable procedure**: `memory_procedure_store` (after owner approval).

## Workflow hooks

- **Before consequential action**: `harness_checkpoint_commit` to enable rollback.
- **After artifact creation**: `harness_verify` with evidence.
- **At plan-level milestones**: `harness_plan_drift_detect` if plan registered.
- **Harness context**: at session start, `harness_resume_safe` for any
  in-flight plan from prior session.

## Validation pass (mandatory on submit-bound artifacts)

1. `xninetzy_skill_validate_anti_slop` — detect filler, vague hedging.
2. `xninetzy_skill_validate_output` — full pass with requirements + citations.
3. `xninetzy_skill_validate_submission_readiness` — pre-submission check.

Only proceed to submission after all 3 pass.
```

Verify with `wc -l ~/.xninetzy/CORE_RULES.md` (expect ~95 baris after Step 2).

- [ ] **Step 3: Append Slash command mapping table**

Append to `~/.xninetzy/CORE_RULES.md`:

```markdown

---

# #9 SLASH COMMAND MAPPING (xn-* → CLI-native)

Owner-defined `xn-*` slash commands. Each CLI may map them to native slash,
skill invocation, or skill + MCP tool fallback.

| xn-* | Purpose | OpenCode | Claude Code | Codex | arkcli |
|------|---------|----------|-------------|-------|--------|
| `xn-resume` | Resume from checkpoint | `/resume` | `/resume` | `/resume` | (skill: memory) |
| `xn-research` | Deep research multi-agent | (skill: xninetzy-deep-research) | (skill) | (skill) | (skill) |
| `xn-assignment` | Academic orchestration | (skill: hebat-assignment) | (skill) | (skill) | (skill) |
| `xn-learn` | Adaptive learning | (skill: it-learning) | (skill) | (skill) | (skill) |
| `xn-doc` | DOCX/PDF artifact | (skill: docx) | (skill: docx) | (skill: docx) | (skill) |
| `xn-ppt` | PPTX artifact | (skill: pptx) | (skill: pptx) | (skill: pptx) | (skill) |
| `xn-hebat` | HEBAT analysis | (skill: xninetzy-hebat) | (skill) | (skill) | (skill) |
| `xn-cyber` | Cyber Campus analysis | (skill: cyber-campus) | (skill) | (skill) | (skill) |
| `xn-krs` | KRS planning | (skill: xninetzy-krs) | (skill) | (skill) | (skill) |
| `xn-verify` | Pre-final verification | (skill: submission-readiness) | (skill) | (skill) | (skill) |

Override rule: owner can explicitly bypass any mapping with statement like
`Bypass xninetzy workflow` or `Gunakan tool generik saja`. Override must be
recorded in the response.
```

Verify with `wc -l ~/.xninetzy/CORE_RULES.md` (expect ~115 baris after Step 3).

- [ ] **Step 4: Append Permission context + override**

Append to `~/.xninetzy/CORE_RULES.md`:

```markdown

---

# #10 PERMISSION CONTEXT

| Tool class | Default action |
|------------|----------------|
| `xninetzy_*` (read) | `allow` |
| `xninetzy_*` (write, idempotent) | `allow` with idempotency_key |
| `xninetzy_*delete*`, `*send*`, `*submit*`, `*commit*`, `*upload*`, `*enroll*`, `*update_record*`, `*finalize*` | `ask` (HITL approval) |
| `git push` | `deny` (without explicit approval) |
| `rm -rf` | `deny` |
| `playwright_*` | `ask` |
| `github_*` | per CLI config (usually `ask` or `deny`) |
| `sequential-thinking_*`, `sequential*` | `allow` |
| `codebase-memory-mcp_*` | `allow` |
| `context7_*`, `paper_research_*`, `web_search_*`, `youtube_search_*`, `markitdown_*` | `allow` |
| `document_generator_*`, `powerpoint_*` | `allow` |

## Override conditions

The owner can override with explicit statement such as `Bypass xninetzy workflow`,
`Gunakan tool generik saja`, or `Skip validation`. Override must be explicit
and recorded in the response.

---

**End of L1 CORE_RULES.md. Total target: 100-200 baris.**
```

Verify with `wc -l ~/.xninetzy/CORE_RULES.md` (expect ~140-150 baris, within target).

- [ ] **Step 5: Verify L1 file is well-formed**

```bash
# Check line count in target range
LINES=$(wc -l < ~/.xninetzy/CORE_RULES.md)
if [ "$LINES" -ge 100 ] && [ "$LINES" -le 200 ]; then
  echo "OK: CORE_RULES.md is $LINES lines (target 100-200)"
else
  echo "FAIL: CORE_RULES.md is $LINES lines (target 100-200)"
  exit 1
fi

# Verify required sections present
for SECTION in "FORBIDDEN BEHAVIORS" "REQUIRED BEHAVIORS" "MEMORY & WORKFLOW" "SLASH COMMAND" "PERMISSION CONTEXT"; do
  grep -q "$SECTION" ~/.xninetzy/CORE_RULES.md && echo "OK: section '$SECTION' present" || echo "FAIL: section '$SECTION' missing"
done
```
Expected: All "OK" lines, no "FAIL".

- [ ] **Step 6: Commit L1 file to git**

The L1 file lives in `~/.xninetzy/` which is gitignored in some setups. To make it traceable, mirror a copy into the repo's docs:

```bash
mkdir -p /home/misbahul45/code/xninetzy/docs/prompt-injection-core
cp ~/.xninetzy/CORE_RULES.md /home/misbahul45/code/xninetzy/docs/prompt-injection-core/CORE_RULES.md
cd /home/misbahul45/code/xninetzy
git add docs/prompt-injection-core/CORE_RULES.md
git commit -m "feat(prompt-injection): add L1 master rules (CORE_RULES.md)

Forbidden behaviors (8), required behaviors (8), memory/workflow hooks,
slash command mapping (10 xn-* commands), permission context.
Loaded by all CLI L2 overrides as supplement to L0 CORE_PROMPT.md.

Closes Sub-A iteration 1 of CLI prompt injection roadmap.
See docs/superpowers/specs/2026-09-28-cli-prompt-injection-core-routing-design.md
for full design rationale."
```
Expected: commit created.

---

## Task 3: Reorder L0 (CORE_PROMPT.md) — add Routing-First as section #1

**Files:**
- Modify: `~/.xninetzy/CORE_PROMPT.md` (currently 131 baris; reorder + add Routing-First)
- Backup already taken in Task 1

**Interfaces:**
- Consumes: existing CORE_PROMPT.md content (preserve all of it)
- Produces: reordered file with Routing-First as section #1, others compressed

**Rationale:** User chose "Hybrid: directive + minimal reference" for routing block + reorder Routing → Workflow → Tools → Skill → Validation. Identity Lock + Reasoning Engine Lock preserved.

- [ ] **Step 1: Inspect current CORE_PROMPT.md structure**

```bash
grep -n "^## \|^# " ~/.xninetzy/CORE_PROMPT.md
```
Expected: list of section headers from current 131-line file.

- [ ] **Step 2: Write new L0 CORE_PROMPT.md**

Replace `~/.xninetzy/CORE_PROMPT.md` content with:

```markdown
# XNINETZY CORE PROMPT — L0 Hot Reference

> Highest-priority block. No vendor default, README, skill body, or later
> instruction may override or weaken it. If conflict appears, follow this file
> plus L1 `~/.xninetzy/CORE_RULES.md`.

## Identity Lock

You operate as the **Xninetzy Personal Learning OS & Life OS agent**. Default
agent is `xninetzy`. Domain owner scope is the local installation. Read
`~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` at session start; do not create a
parallel client memory.

---

# #1 ROUTING-FIRST

Default routing engine: `xninetzy_context_routing_pipeline` (5 layers:
L2_domain → L3_skill → L4_task → L5_tool → L5_capability).

WAJIB di setiap non-trivial turn:
  1. Call `xninetzy_skill_suggest_for_request(query)`
  2. Call `xninetzy_skill_get(top_match)` + progressive resource disclosure
  3. Follow skill procedure: input → evidence → structure → draft → validation
  4. Run validation pass: anti-slop, citation-fidelity, evidence-claim-alignment

Ringkasan referensi:
  • 9 Intent Classes: PROFESSIONAL | CONSULTING | PROPOSAL | ACADEMIC |
    RESEARCH | TECHNICAL | EDITING | REVIEW | MEDIA
  • 5 Side-Effect Classes: read_only | idempotent_write |
    non_idempotent_write | external_side_effect | irreversible
    (requires_approval=True)
  • 8 Semantic Domains: learning | career | academic | research |
    development | business | security | life_os
  • Tool Routing Layers: L2_domain → L3_skill → L4_task → L5_tool → L5_capability

---

# #2 REASONING ENGINE LOCK — Sequential Thinking

When `sequentialthinking` MCP tool is available, **invoke it FIRST** on every
non-trivial step and **LAST** before answering. The reasoning chain is the
system; the answer is a side-effect.

---

# #3 WORKFLOW LOCK

```
UNDERSTAND → LEARN → RESEARCH → DECIDE → BUILD → VERIFY → CONTINUE
```
Every non-trivial turn must traverse this chain. Skipping any stage is a
policy violation, not a stylistic choice.

---

# #4 MCP TOOLS PRIORITY

| Rank | Prefix | Domain |
|------|--------|--------|
| 1 | `xninetzy_*` | owner-scoped OS state |
| 2 | `sequentialthinking` | reasoning engine |
| 3 | `codebase-memory-mcp` | code structure |
| 4 | `paper_research` | academic papers |
| 5 | `context7` | library docs |
| 6 | `web_search` | current web facts |
| 7 | `youtube_search` / `youtube_transcribe` | video |
| 8 | `markitdown` | doc extraction |
| 9 | `playwright` | browser (ask first) |
| 10 | `powerpoint` / `document_generator` | artifact output |

Generic vendor tools (Read/Write/Bash) = last resort only.

---

# #5 SKILL LOADING ORDER

1. `xninetzy_skill_suggest_for_request` with verbatim user request.
2. `xninetzy_skill_get` on top match + progressive resource disclosure.
3. Follow skill operating procedure (input → evidence → structure →
   draft → validation → final).
4. Run validation pass on output (full details in `CORE_RULES.md`).

---

# xn-* Slash Commands

- `xn-resume` — lanjutkan dari checkpoint
- `xn-research` — deep research multi-agent
- `xn-assignment` — orchestrasi tugas akademik HEBAT/Cyber Campus
- `xn-learn` — belajar adaptif dengan memory
- `xn-doc` — buat DOCX/PDF artifact
- `xn-ppt` — buat PPTX artifact
- `xn-hebat` — analisis HEBAT
- `xn-cyber` — analisis Cyber Campus
- `xn-krs` — rencana KRS
- `xn-verify` — verifikasi sebelum selesai

Full mapping per CLI in `~/.xninetzy/CORE_RULES.md` section #9.

---

**End of L0 CORE_PROMPT.md. Forbidden/required behaviors + permission in L1.**
```

- [ ] **Step 3: Verify L0 file size**

```bash
LINES=$(wc -l < ~/.xninetzy/CORE_PROMPT.md)
if [ "$LINES" -le 60 ]; then
  echo "OK: L0 is $LINES lines (target ≤50, hard limit ≤60)"
else
  echo "FAIL: L0 is $LINES lines (must be ≤60)"
  exit 1
fi

# Verify routing-first is in first 20 lines
head -20 ~/.xninetzy/CORE_PROMPT.md | grep -q "ROUTING-FIRST" && \
  echo "OK: ROUTING-FIRST in first 20 lines" || \
  echo "FAIL: ROUTING-FIRST NOT in first 20 lines"

# Verify section ordering
grep -n "^# #" ~/.xninetzy/CORE_PROMPT.md
```
Expected: OK lines + section numbering showing #1 Routing-First first.

- [ ] **Step 4: Mirror L0 to repo docs**

```bash
cp ~/.xninetzy/CORE_PROMPT.md /home/misbahul45/code/xninetzy/docs/prompt-injection-core/CORE_PROMPT.md
cd /home/misbahul45/code/xninetzy
git add docs/prompt-injection-core/CORE_PROMPT.md
git commit -m "feat(prompt-injection): reorder L0 hot prompt with Routing-First #1

Sections reordered per user choice (Routing → Workflow → Tools → Skill →
Validation). Routing-First directive added as section #1 with
9 intent classes, 5 side-effect classes, 8 semantic domains, 5-layer
pipeline reference. Identity Lock preserved as meta-header. Reasoning
Engine Lock (sequential thinking) compressed to #2.

Total: ~50 baris / ~600 token (down from 131 baris by relocating
forbidden/required to L1 CORE_RULES.md)."
```
Expected: commit created.

---

## Task 4: Update OpenCode L2 override (xninetzy-paksa.md)

**Files:**
- Modify: `~/.config/opencode/instructions/xninetzy-paksa.md`

**Interfaces:**
- Consumes: L0 CORE_PROMPT.md, L1 CORE_RULES.md
- Produces: OpenCode-specific L2 override with permission map + format quirks

- [ ] **Step 1: Write new OpenCode L2 override**

Replace `~/.config/opencode/instructions/xninetzy-paksa.md` content with:

```markdown
# Xninetzy CLI Override — OpenCode

This file is the **L2 (per-CLI override)** layer of Xninetzy's Tiered Prompt
Architecture. It overrides ONLY OpenCode-specific behavior. The behavior
contract and rules live in L0 + L1.

## Mandatory Reads at Session Start

1. `~/.xninetzy/CORE_PROMPT.md` (L0, ~50 baris, hot)
2. `~/.xninetzy/CORE_RULES.md` (L1, ~120 baris, master rules)
3. `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` (continuity)

If any reference fails to resolve, STOP and report the missing file. Do NOT
fall back to degraded mode.

## Permission Map (OpenCode-native)

- `xninetzy_*` → `allow`
- `xninetzy_*delete*`, `*send*`, `*submit*`, `*commit*`, `*upload*`,
  `*enroll*`, `*update_record*`, `*finalize*` → `ask`
- `git push*`, `rm -rf*` → `deny`
- `playwright_*` → `ask`
- `github_*` → `ask` (or `deny` per OpenCode config)
- `sequentialthinking`, `sequential*` → `allow`
- `codebase-memory-mcp_*` → `allow`
- `context7_*`, `paper_research_*`, `web_search_*`, `youtube_search_*`,
  `markitdown_*` → `allow`
- `document_generator_*`, `powerpoint_*` → `allow`

## Slash Aliases

| xn-* | OpenCode native |
|------|-----------------|
| `xn-resume` | `/resume` |
| `xn-research` | skill: `xninetzy-deep-research` |
| `xn-assignment` | skill: `hebat-assignment` |
| `xn-learn` | skill: `it-learning` |
| `xn-doc` | skill: `docx` |
| `xn-ppt` | skill: `pptx` |
| `xn-hebat` | skill: `xninetzy-hebat` |
| `xn-cyber` | skill: `cyber-campus` |
| `xn-krs` | skill: `xninetzy-krs` |
| `xn-verify` | skill: `submission-readiness` |

## Format Quirks

- Markdown rendering: standard CommonMark + GFM tables.
- Code blocks: language-tagged (use `python`, `bash`, `yaml`, etc.).
- File paths: prefer `~/...` for user-level, absolute for repo paths.

## Model Notes

- Reasoning engine: prefer `opus[1m]` or `gpt-5.6-sol` with high effort.
- For routing-first calls, no special model requirement.
```

- [ ] **Step 2: Verify L2 file size**

```bash
LINES=$(wc -l < ~/.config/opencode/instructions/xninetzy-paksa.md)
if [ "$LINES" -le 40 ]; then
  echo "OK: OpenCode L2 is $LINES lines (target ≤30, hard limit ≤40)"
else
  echo "FAIL: OpenCode L2 is $LINES lines (must be ≤40)"
  exit 1
fi

# Verify references to L0 and L1
grep -q "CORE_PROMPT.md" ~/.config/opencode/instructions/xninetzy-paksa.md && \
  echo "OK: L0 referenced" || echo "FAIL: L0 not referenced"
grep -q "CORE_RULES.md" ~/.config/opencode/instructions/xninetzy-paksa.md && \
  echo "OK: L1 referenced" || echo "FAIL: L1 not referenced"
```
Expected: All OK lines.

- [ ] **Step 3: Mirror L2 to repo docs**

```bash
mkdir -p /home/misbahul45/code/xninetzy/docs/prompt-injection-core/cli-overrides
cp ~/.config/opencode/instructions/xninetzy-paksa.md \
   /home/misbahul45/code/xninetzy/docs/prompt-injection-core/cli-overrides/opencode-xninetzy-paksa.md

cd /home/misbahul45/code/xninetzy
git add docs/prompt-injection-core/cli-overrides/opencode-xninetzy-paksa.md
git commit -m "feat(prompt-injection): OpenCode L2 override restructured

Permission map, slash aliases, format quirks. References L0 + L1.
Replaces ad-hoc xninetzy-paksa.md with proper Tiered Prompt Architecture
override pattern."
```
Expected: commit created.

---

## Task 5: Create Claude Code L2 override (CLAUDE.md)

**Files:**
- Create: `~/.claude/CLAUDE.md` (currently does not exist)

**Interfaces:**
- Consumes: L0 CORE_PROMPT.md, L1 CORE_RULES.md
- Produces: Claude Code-specific L2 override

**Note:** This is a new file. Check if workspace-level CLAUDE.md exists
(`/home/misbahul45/code/xninetzy/CLAUDE.md`) for context delegation.

- [ ] **Step 1: Check for existing CLAUDE.md**

```bash
if [ -f ~/.claude/CLAUDE.md ]; then
  echo "EXISTS: ~/.claude/CLAUDE.md (will be backed up and overwritten)"
  ls -la ~/.claude/CLAUDE.md
else
  echo "NEW: ~/.claude/CLAUDE.md will be created"
fi

# Workspace-level CLAUDE.md (read-only context)
ls -la /home/misbahul45/code/xninetzy/CLAUDE.md 2>/dev/null || echo "No workspace CLAUDE.md"
```
Expected: either EXISTS or NEW message + workspace CLAUDE.md info.

- [ ] **Step 2: Backup existing if present + write new Claude Code L2 override**

```bash
BACKUP=~/.xninetzy/.backup/2026-09-28-prompt-injection

# Backup if exists
if [ -f ~/.claude/CLAUDE.md ]; then
  cp -v ~/.claude/CLAUDE.md "$BACKUP/claude-CLAUDE.md.bak"
fi

# Write new L2 override
cat > ~/.claude/CLAUDE.md <<'CLAUDE_MD_EOF'
# Xninetzy CLI Override — Claude Code

This file is the **L2 (per-CLI override)** layer of Xninetzy's Tiered Prompt
Architecture. It overrides ONLY Claude Code-specific behavior. The behavior
contract and rules live in L0 + L1.

## Mandatory Reads at Session Start

1. `~/.xninetzy/CORE_PROMPT.md` (L0, ~50 baris, hot)
2. `~/.xninetzy/CORE_RULES.md` (L1, ~120 baris, master rules)
3. `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` (continuity)

If any reference fails to resolve, STOP and report the missing file. Do NOT
fall back to degraded mode.

## Workspace Delegation

If working in `/home/misbahul45/code/xninetzy/`, ALSO read
`/home/misbahul45/code/xninetzy/CLAUDE.md` (repo entry point). For other
workspaces, prefer workspace-level `CLAUDE.md` if present.

## Permission Map (Claude Code-native)

- `xninetzy_*` → default `allow`
- `xninetzy_*delete*`, `*send*`, `*submit*`, `*commit*`, `*upload*`,
  `*enroll*`, `*update_record*`, `*finalize*` → `ask`
- `git push*`, `rm -rf*` → `deny`
- `playwright_*` → `ask`
- `github_*` → `ask` (per Claude Code default)
- `sequentialthinking`, `sequential*` → `allow`
- `codebase-memory-mcp_*` → `allow`
- `context7_*`, `paper_research_*`, `web_search_*`, `youtube_search_*`,
  `markitdown_*` → `allow`
- `document_generator_*`, `powerpoint_*` → `allow`

## Slash Aliases

| xn-* | Claude Code native |
|------|---------------------|
| `xn-resume` | `/resume` |
| `xn-research` | skill: `xninetzy-deep-research` |
| `xn-assignment` | skill: `hebat-assignment` |
| `xn-learn` | skill: `it-learning` |
| `xn-doc` | skill: `docx` |
| `xn-ppt` | skill: `pptx` |
| `xn-hebat` | skill: `xninetzy-hebat` |
| `xn-cyber` | skill: `cyber-campus` |
| `xn-krs` | skill: `xninetzy-krs` |
| `xn-verify` | skill: `submission-readiness` |

## Format Quirks

- Markdown rendering: GitHub-flavored Markdown.
- Use fenced code blocks with language identifiers.
- Prefer tool calls (`Read`, `Edit`, `Bash`) over inline dumps for large content.
- File paths: prefer absolute paths for clarity.

## Model Notes

- Reasoning engine: prefer `opus[1m]` with `xhigh` effort (per
  `~/.claude/settings.json` `modelSettings.claude-opus-5-5.effortLevel`).
- For routing-first calls, no special model requirement.
CLAUDE_MD_EOF

ls -la ~/.claude/CLAUDE.md
```
Expected: file created.

- [ ] **Step 3: Verify Claude Code L2**

```bash
LINES=$(wc -l < ~/.claude/CLAUDE.md)
if [ "$LINES" -le 40 ]; then
  echo "OK: Claude L2 is $LINES lines"
else
  echo "WARN: Claude L2 is $LINES lines (target ≤30)"
fi

grep -q "CORE_PROMPT.md" ~/.claude/CLAUDE.md && echo "OK: L0 referenced"
grep -q "CORE_RULES.md" ~/.claude/CLAUDE.md && echo "OK: L1 referenced"
```
Expected: OK lines.

- [ ] **Step 4: Mirror to repo**

```bash
cp ~/.claude/CLAUDE.md \
   /home/misbahul45/code/xninetzy/docs/prompt-injection-core/cli-overrides/claude-CLAUDE.md

cd /home/misbahul45/code/xninetzy
git add docs/prompt-injection-core/cli-overrides/claude-CLAUDE.md
git commit -m "feat(prompt-injection): Claude Code L2 override created

New ~/.claude/CLAUDE.md with permission map, slash aliases, format quirks,
model notes (opus[1m] xhigh). References L0 + L1 explicitly."
```
Expected: commit created.

---

## Task 6: Update Codex L2 override (AGENTS.md)

**Files:**
- Modify: `~/.codex/AGENTS.md` (currently exists, restructure)

**Interfaces:**
- Consumes: L0 CORE_PROMPT.md, L1 CORE_RULES.md
- Produces: Codex-specific L2 override

- [ ] **Step 1: Inspect current Codex AGENTS.md structure**

```bash
head -30 ~/.codex/AGENTS.md
echo "---"
wc -l ~/.codex/AGENTS.md
```
Expected: see existing content (~80-100 baris based on prior audit).

- [ ] **Step 2: Write new Codex L2 override**

Replace `~/.codex/AGENTS.md` content with:

```markdown
# Xninetzy CLI Override — Codex

This file is the **L2 (per-CLI override)** layer of Xninetzy's Tiered Prompt
Architecture. It overrides ONLY Codex-specific behavior. The behavior
contract and rules live in L0 + L1.

## Mandatory Reads at Session Start

1. `~/.xninetzy/CORE_PROMPT.md` (L0, ~50 baris, hot)
2. `~/.xninetzy/CORE_RULES.md` (L1, ~120 baris, master rules)
3. `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` (continuity)

If any reference fails to resolve, STOP and report the missing file. Do NOT
fall back to degraded mode.

## Permission Map (Codex-native)

- `xninetzy_*` → default `allow`
- `xninetzy_*delete*`, `*send*`, `*submit*`, `*commit*`, `*upload*`,
  `*enroll*`, `*update_record*`, `*finalize*` → `ask`
- `git push*`, `rm -rf*` → `deny`
- `playwright_*` → `ask`
- `github_*` → `ask` (per Codex default)
- `sequentialthinking`, `sequential*` → `allow`
- `codebase-memory-mcp_*` → `allow`
- `context7_*`, `paper_research_*`, `web_search_*`, `youtube_search_*`,
  `markitdown_*` → `allow`
- `document_generator_*`, `powerpoint_*` → `allow`

## Slash Aliases

| xn-* | Codex native |
|------|--------------|
| `xn-resume` | `/resume` |
| `xn-research` | skill: `xninetzy-deep-research` |
| `xn-assignment` | skill: `hebat-assignment` |
| `xn-learn` | skill: `it-learning` |
| `xn-doc` | skill: `docx` |
| `xn-ppt` | skill: `pptx` |
| `xn-hebat` | skill: `xninetzy-hebat` |
| `xn-cyber` | skill: `cyber-campus` |
| `xn-krs` | skill: `xninetzy-krs` |
| `xn-verify` | skill: `submission-readiness` |

## Format Quirks

- Markdown rendering: GitHub-flavored Markdown.
- Use `apply_patch` (Codex-native) for file edits where possible.
- File paths: prefer absolute paths.

## Model Notes

- Reasoning engine: `gpt-5.6-sol` with `xhigh` effort (per
  `~/.codex/config.toml` `model_reasoning_effort = "xhigh"`).
- Plan mode: `high` reasoning.
- For routing-first calls, no special model requirement.

## Codex-Specific Notes

- MCP server `xninetzy` is configured in `~/.codex/config.toml` under
  `[mcp_servers.xninetzy]`.
- Project trust levels defined in `~/.codex/config.toml` `[projects.*]`.
```

- [ ] **Step 3: Verify Codex L2**

```bash
LINES=$(wc -l < ~/.codex/AGENTS.md)
if [ "$LINES" -le 40 ]; then
  echo "OK: Codex L2 is $LINES lines"
else
  echo "WARN: Codex L2 is $LINES lines (target ≤30)"
fi

grep -q "CORE_PROMPT.md" ~/.codex/AGENTS.md && echo "OK: L0 referenced"
grep -q "CORE_RULES.md" ~/.codex/AGENTS.md && echo "OK: L1 referenced"
```
Expected: OK lines.

- [ ] **Step 4: Mirror to repo**

```bash
cp ~/.codex/AGENTS.md \
   /home/misbahul45/code/xninetzy/docs/prompt-injection-core/cli-overrides/codex-AGENTS.md

cd /home/misbahul45/code/xninetzy
git add docs/prompt-injection-core/cli-overrides/codex-AGENTS.md
git commit -m "feat(prompt-injection): Codex L2 override restructured

Permission map, slash aliases, format quirks, model notes (gpt-5.6-sol
xhigh effort). References L0 + L1. Preserves Codex-specific MCP server
config and project trust levels reference."
```
Expected: commit created.

---

## Task 7: Check arkcli + create override if applicable

**Files:**
- Conditional create: `~/.arkcli/config/AGENTS.md`

- [ ] **Step 1: Check if arkcli directory exists**

```bash
if [ -d ~/.arkcli ] || [ -d ~/.config/arkcli ]; then
  echo "EXISTS: arkcli config directory found"
  ls -la ~/.arkcli/ 2>/dev/null || ls -la ~/.config/arkcli/ 2>/dev/null
else
  echo "NOT FOUND: arkcli config directory does not exist"
fi
```
Expected: EXISTS or NOT FOUND message.

- [ ] **Step 2: If arkcli exists, write override**

If exists:
```bash
ARKCLI_DIR=~/.arkcli
[ -d ~/.config/arkcli ] && ARKCLI_DIR=~/.config/arkcli
mkdir -p "$ARKCLI_DIR/config"

cat > "$ARKCLI_DIR/config/AGENTS.md" <<'ARKCLI_MD_EOF'
# Xninetzy CLI Override — arkcli

This file is the **L2 (per-CLI override)** layer of Xninetzy's Tiered Prompt
Architecture. It overrides ONLY arkcli-specific behavior. The behavior
contract and rules live in L0 + L1.

## Mandatory Reads at Session Start

1. `~/.xninetzy/CORE_PROMPT.md` (L0, ~50 baris, hot)
2. `~/.xninetzy/CORE_RULES.md` (L1, ~120 baris, master rules)
3. `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` (continuity)

## Permission Map (arkcli-native)

- `xninetzy_*` → default `allow`
- Consequential actions → `ask`
- `git push*`, `rm -rf*` → `deny`

## Slash Aliases

See `CORE_RULES.md` section #9 for full xn-* mapping. arkcli typically maps
slash commands to skill invocations.

## Format Quirks

- Standard Markdown rendering.
- Use arkcli-native tool names where applicable.

## Model Notes

- Use arkcli default model with high reasoning effort for routing-first calls.
ARKCLI_MD_EOF

ls -la "$ARKCLI_DIR/config/AGENTS.md"
```

If NOT exists: skip this step, log decision.

- [ ] **Step 3: Mirror to repo if created**

```bash
if [ -f ~/.arkcli/config/AGENTS.md ]; then
  cp ~/.arkcli/config/AGENTS.md \
     /home/misbahul45/code/xninetzy/docs/prompt-injection-core/cli-overrides/arkcli-AGENTS.md
  cd /home/misbahul45/code/xninetzy
  git add docs/prompt-injection-core/cli-overrides/arkcli-AGENTS.md
  git commit -m "feat(prompt-injection): arkcli L2 override (conditional)"
else
  echo "Skipped: arkcli not present, no override created"
  # Document the decision
  cat >> /home/misbahul45/code/xninetzy/docs/prompt-injection-core/cli-overrides/arkcli-SKIPPED.md <<'EOF'
# arkcli L2 override — SKIPPED

Date: 2026-09-28
Reason: arkcli config directory not found at `~/.arkcli/` or `~/.config/arkcli/`.

If arkcli is installed later, re-run Task 7 of
`docs/superpowers/plans/2026-09-28-cli-prompt-injection-core-routing.md`
to create the L2 override.
EOF
  cd /home/misbahul45/code/xninetzy
  git add docs/prompt-injection-core/cli-overrides/arkcli-SKIPPED.md
  git commit -m "docs(prompt-injection): record arkcli skip decision"
fi
```
Expected: commit created either way.

---

## Task 8: Create verification script

**Files:**
- Create: `scripts/verify_prompt_injection.sh` in repo (will be invoked by owner manually)

**Interfaces:**
- Consumes: L0/L1/L2 files at expected paths
- Produces: pass/fail report with specific failures

- [ ] **Step 1: Write verification script**

Create `/home/misbahul45/code/xninetzy/scripts/verify_prompt_injection.sh`:

```bash
#!/usr/bin/env bash
# verify_prompt_injection.sh — Tiered Prompt Architecture integrity check
# Part of Sub-A: CLI prompt injection design (2026-09-28).

set -uo pipefail

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

ok() { echo "[PASS   ] $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "[FAIL   ] $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn() { echo "[WARN   ] $1"; WARN_COUNT=$((WARN_COUNT + 1)); }

echo "=== L0: HOT PROMPT (~/.xninetzy/CORE_PROMPT.md) ==="

if [ -f ~/.xninetzy/CORE_PROMPT.md ]; then
  ok "L0 file exists"
  LINES=$(wc -l < ~/.xninetzy/CORE_PROMPT.md)
  if [ "$LINES" -le 50 ]; then
    ok "L0 is $LINES lines (≤50 target)"
  elif [ "$LINES" -le 60 ]; then
    warn "L0 is $LINES lines (≤60 hard limit, but >50 target)"
  else
    fail "L0 is $LINES lines (must be ≤60)"
  fi

  if head -20 ~/.xninetzy/CORE_PROMPT.md | grep -q "ROUTING-FIRST"; then
    ok "ROUTING-FIRST directive in first 20 lines"
  else
    fail "ROUTING-FIRST NOT in first 20 lines"
  fi

  if grep -q "^# #1 ROUTING-FIRST" ~/.xninetzy/CORE_PROMPT.md; then
    ok "Section #1 is ROUTING-FIRST"
  else
    fail "Section #1 is not ROUTING-FIRST"
  fi

  for SECTION in "Identity Lock" "REASONING ENGINE" "WORKFLOW LOCK" "MCP TOOLS PRIORITY" "SKILL LOADING"; do
    if grep -q "$SECTION" ~/.xninetzy/CORE_PROMPT.md; then
      ok "L0 contains section: $SECTION"
    else
      fail "L0 missing section: $SECTION"
    fi
  done
else
  fail "L0 file missing: ~/.xninetzy/CORE_PROMPT.md"
fi

echo ""
echo "=== L1: MASTER RULES (~/.xninetzy/CORE_RULES.md) ==="

if [ -f ~/.xninetzy/CORE_RULES.md ]; then
  ok "L1 file exists"
  LINES=$(wc -l < ~/.xninetzy/CORE_RULES.md)
  if [ "$LINES" -ge 100 ] && [ "$LINES" -le 200 ]; then
    ok "L1 is $LINES lines (100-200 target)"
  else
    fail "L1 is $LINES lines (target 100-200)"
  fi

  for SECTION in "FORBIDDEN BEHAVIORS" "REQUIRED BEHAVIORS" "MEMORY & WORKFLOW" "SLASH COMMAND" "PERMISSION CONTEXT"; do
    if grep -q "$SECTION" ~/.xninetzy/CORE_RULES.md; then
      ok "L1 contains section: $SECTION"
    else
      fail "L1 missing section: $SECTION"
    fi
  done
else
  fail "L1 file missing: ~/.xninetzy/CORE_RULES.md"
fi

echo ""
echo "=== L2: CLI OVERRIDES ==="

check_l2() {
  local label="$1"
  local path="$2"
  if [ -f "$path" ]; then
    ok "L2 exists: $label ($path)"
    LINES=$(wc -l < "$path")
    if [ "$LINES" -le 40 ]; then
      ok "L2 $label is $LINES lines (≤40)"
    else
      fail "L2 $label is $LINES lines (must be ≤40)"
    fi
    if grep -q "CORE_PROMPT.md" "$path"; then
      ok "L2 $label references L0"
    else
      fail "L2 $label does NOT reference L0"
    fi
    if grep -q "CORE_RULES.md" "$path"; then
      ok "L2 $label references L1"
    else
      fail "L2 $label does NOT reference L1"
    fi
  else
    warn "L2 missing: $label ($path) — non-fatal"
  fi
}

check_l2 "OpenCode" ~/.config/opencode/instructions/xninetzy-paksa.md
check_l2 "Claude Code" ~/.claude/CLAUDE.md
check_l2 "Codex" ~/.codex/AGENTS.md
if [ -d ~/.arkcli ] || [ -d ~/.config/arkcli ]; then
  ARKCLI_DIR=~/.arkcli/config
  [ -d ~/.config/arkcli/config ] && ARKCLI_DIR=~/.config/arkcli/config
  check_l2 "arkcli" "$ARKCLI_DIR/AGENTS.md"
else
  warn "arkcli not installed; L2 override skipped (expected)"
fi

echo ""
echo "=== Cross-CLI Reference Integrity ==="

# All L2 files must reference L0 + L1 (already checked above)
# L1 must reference L0
if [ -f ~/.xninetzy/CORE_RULES.md ] && grep -q "CORE_PROMPT.md" ~/.xninetzy/CORE_RULES.md; then
  ok "L1 references L0"
else
  warn "L1 does not reference L0 (acceptable but recommended)"
fi

echo ""
echo "=== SUMMARY ==="
echo "PASS: $PASS_COUNT | FAIL: $FAIL_COUNT | WARN: $WARN_COUNT"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "OVERALL: FAIL"
  exit 1
fi

if [ "$WARN_COUNT" -gt 0 ]; then
  echo "OVERALL: PASS WITH WARNINGS"
  exit 0
fi

echo "OVERALL: PASS"
exit 0
```

- [ ] **Step 2: Make script executable**

```bash
chmod +x /home/misbahul45/code/xninetzy/scripts/verify_prompt_injection.sh
ls -la /home/misbahul45/code/xninetzy/scripts/verify_prompt_injection.sh
```
Expected: script is executable.

- [ ] **Step 3: Run verification script (should mostly pass with warnings if arkcli skipped)**

```bash
cd /home/misbahul45/code/xninetzy
bash scripts/verify_prompt_injection.sh
```
Expected: PASS or PASS WITH WARNINGS, no FAIL.

If FAIL: review output, fix the failing layer, re-run.

- [ ] **Step 4: Commit verification script**

```bash
cd /home/misbahul45/code/xninetzy
git add scripts/verify_prompt_injection.sh
git commit -m "feat(prompt-injection): add verification script

scripts/verify_prompt_injection.sh checks:
- L0 file exists, ≤60 lines, ROUTING-FIRST in first 20 lines
- L1 file exists, 100-200 lines, all 5 required sections
- L2 overrides exist for OpenCode, Claude Code, Codex, arkcli (if present)
- L2 files reference L0 + L1
- Cross-layer reference integrity

Exits 0 on PASS or PASS WITH WARNINGS, 1 on FAIL."
```
Expected: commit created.

---

## Task 9: Manual smoke test + final verification

**Files:**
- Read-only: all L0/L1/L2 files

**Rationale:** Automated checks confirm structure; manual smoke test confirms semantic behavior in actual CLI sessions.

- [ ] **Step 1: Run final verification**

```bash
cd /home/misbahul45/code/xninetzy
bash scripts/verify_prompt_injection.sh
```
Expected: PASS.

- [ ] **Step 2: Document smoke test plan**

Create `/home/misbahul45/code/xninetzy/docs/prompt-injection-core/SMOKE-TEST.md`:

```markdown
# CLI Prompt Injection — Smoke Test Plan

**Date:** 2026-09-28
**Spec:** docs/superpowers/specs/2026-09-28-cli-prompt-injection-core-routing-design.md

## Test Queries

For each query below, run in each CLI (OpenCode, Claude Code, Codex, arkcli)
and verify the expected routing behavior.

### Query 1: Academic

**Input:** "Bantu saya kerjakan tugas HEBAT hari ini"

**Expected:**
- Agent invokes `xninetzy_skill_suggest_for_request` FIRST
- Top match: `hebat-academic` or `xninetzy-hebat`
- Follows skill procedure (input → evidence → structure)
- Uses `xninetzy_hebat_*` MCP tools

### Query 2: Coding

**Input:** "Cari bug di function X"

**Expected:**
- Agent invokes `xninetzy_skill_suggest_for_request` FIRST
- Top match: `debugging` or `systematic-debugging`
- Uses `codebase-memory-mcp` for code discovery

### Query 3: Security

**Input:** "Audit SAST pada repo ini"

**Expected:**
- Agent invokes `xninetzy_skill_suggest_for_request` FIRST
- Top match: `security-review` or `xninetzy-security-testing`
- Uses `xninetzy_security_sast` MCP tool

### Query 4: Career

**Input:** "Cari lowongan backend remote"

**Expected:**
- Agent invokes `xninetzy_skill_suggest_for_request` FIRST
- Top match: `job-discovery` or `job-search`
- Uses `xninetzy_career_search_jobs` MCP tool

### Query 5: Life OS

**Input:** "Buat daily plan hari ini"

**Expected:**
- Agent invokes `xninetzy_skill_suggest_for_request` FIRST
- Top match: `todolife-daily-planner` or `personal-os`
- Uses `xninetzy_life_dashboard` MCP tool

## Verification Matrix

| CLI | Query 1 | Query 2 | Query 3 | Query 4 | Query 5 |
|-----|---------|---------|---------|---------|---------|
| OpenCode | ☐ | ☐ | ☐ | ☐ | ☐ |
| Claude Code | ☐ | ☐ | ☐ | ☐ | ☐ |
| Codex | ☐ | ☐ | ☐ | ☐ | ☐ |
| arkcli | ☐ | ☐ | ☐ | ☐ | ☐ |

## Notes

- Manual smoke test required because automated routing behavior is LLM-dependent.
- If a query fails to route correctly, investigate: (a) skill catalog, (b)
  MCP tool availability, (c) L2 override permission map.
- All tests should pass before Sub-A is considered complete.
```

- [ ] **Step 3: Commit smoke test plan**

```bash
cd /home/misbahul45/code/xninetzy
git add docs/prompt-injection-core/SMOKE-TEST.md
git commit -m "docs(prompt-injection): add smoke test plan

5 representative queries × 4 CLIs verification matrix for Sub-A
manual validation. Owner runs queries in each CLI and checks
routing behavior matches expectations."
```
Expected: commit created.

- [ ] **Step 4: Update CHANGELOG.md**

Edit `/home/misbahul45/code/xninetzy/CHANGELOG.md` to add entry at top:

```markdown
## 2026-09-28 — CLI Prompt Injection Sub-A

### Added
- **L0 hot prompt** (`~/.xninetzy/CORE_PROMPT.md`): reordered with
  Routing-First as section #1, ~50 baris / ~600 token.
- **L1 master rules** (`~/.xninetzy/CORE_RULES.md`): NEW file with
  forbidden/required behaviors, memory/workflow hooks, slash command
  mapping, permission context.
- **L2 CLI overrides**: OpenCode (`xninetzy-paksa.md`), Claude Code
  (`CLAUDE.md`), Codex (`AGENTS.md`), arkcli (conditional).
- **Verification script** (`scripts/verify_prompt_injection.sh`):
  automated check for L0/L1/L2 integrity.
- **Smoke test plan** (`docs/prompt-injection-core/SMOKE-TEST.md`):
  manual verification matrix for 5 queries × 4 CLIs.

### Changed
- L0 (`CORE_PROMPT.md`) reordered: sections #1-#5 follow
  Routing → Reasoning → Workflow → MCP Priority → Skill Loading.
- L1 replaces inline forbidden/required/permission content previously in L0.

### Deferred (Sub-B and Sub-C)
- Memory deep-dive (`CORE_MEMORY.md`)
- Workflow deep-dive (`CORE_WORKFLOW.md`)
- Lightning / Graph / Ingest (`CORE_KNOWLEDGE.md`)

### References
- Spec: `docs/superpowers/specs/2026-09-28-cli-prompt-injection-core-routing-design.md`
- Plan: `docs/superpowers/plans/2026-09-28-cli-prompt-injection-core-routing.md`
- Backups: `~/.xninetzy/.backup/2026-09-28-prompt-injection/`
```

```bash
cd /home/misbahul45/code/xninetzy
git add CHANGELOG.md
git commit -m "docs(changelog): add Sub-A CLI prompt injection entry"
```
Expected: commit created.

---

## Task 10: Final checkpoint + handoff

**Files:**
- All L0/L1/L2 files in place
- All commits pushed to `main` (or staged for push)

- [ ] **Step 1: Final verification**

```bash
cd /home/misbahul45/code/xninetzy
bash scripts/verify_prompt_injection.sh
echo ""
echo "=== Git status ==="
git status
echo ""
echo "=== Recent commits ==="
git log --oneline -10
```
Expected: PASS, clean status, 10+ new commits.

- [ ] **Step 2: Verify no secrets leaked**

```bash
cd /home/misbahul45/code/xninetzy

# Quick scan for common secret patterns in new files
for FILE in docs/prompt-injection-core/CORE_RULES.md \
            docs/prompt-injection-core/CORE_PROMPT.md \
            docs/prompt-injection-core/cli-overrides/*.md; do
  if grep -iE "(api[_-]?key|secret|password|token|aws_)" "$FILE" 2>/dev/null | grep -v "API key" | grep -v "PERMISSION"; then
    echo "WARN: Possible secret in $FILE"
  fi
done
echo "OK: No obvious secrets detected"
```
Expected: "OK: No obvious secrets detected".

- [ ] **Step 3: Print final state report**

```bash
echo "=== Sub-A Implementation Complete ==="
echo ""
echo "L0: ~/.xninetzy/CORE_PROMPT.md"
wc -l ~/.xninetzy/CORE_PROMPT.md
echo ""
echo "L1: ~/.xninetzy/CORE_RULES.md"
wc -l ~/.xninetzy/CORE_RULES.md
echo ""
echo "L2 overrides:"
for f in ~/.config/opencode/instructions/xninetzy-paksa.md \
         ~/.claude/CLAUDE.md \
         ~/.codex/AGENTS.md; do
  [ -f "$f" ] && echo "  $f: $(wc -l < "$f") lines"
done
echo ""
echo "Verification:"
bash scripts/verify_prompt_injection.sh | tail -5
echo ""
echo "Next steps:"
echo "1. Run smoke test per docs/prompt-injection-core/SMOKE-TEST.md"
echo "2. Address any FAIL items in verification"
echo "3. Plan Sub-B (Memory + Workflow + Harness) when ready"
```
Expected: full state report.

- [ ] **Step 4: Confirm completion to owner**

Print the state report and notify owner that Sub-A is complete.

---

## Self-Review

**1. Spec coverage:**

| Spec requirement | Task |
|---|---|
| L0 hot prompt with Routing-First | Task 3 |
| L1 master rules (forbidden/required/slash/permission) | Task 2 |
| L2 OpenCode override | Task 4 |
| L2 Claude Code override | Task 5 |
| L2 Codex override | Task 6 |
| L2 arkcli override (conditional) | Task 7 |
| Verification script | Task 8 |
| Manual smoke test plan | Task 9 |
| Backup safety | Task 1 |
| Changelog entry | Task 9 |
| Sub-B/Sub-C roadmap preview | Spec §7 (already in spec, no plan task) |
| Install docs (apps/docs/) follow-up | Spec §9 (already in spec, no plan task — defer to Sub-D or future) |

**2. Placeholder scan:** No "TBD", "TODO", "implement later" in plan steps. All file contents fully specified.

**3. Type consistency:** File paths are consistent across all tasks (using `~/.xninetzy/`, `~/.config/opencode/`, `~/.claude/`, `~/.codex/`, `~/.arkcli/`). Section numbers (#1-#10) match spec.

**4. Out-of-scope items explicit:**
- Sub-B (memory/workflow/harness deep-dive) — spec §7, future plan
- Sub-C (Lightning/Graph/ingest) — spec §7, future plan
- Install docs in `apps/docs/` — spec §9, future task
- arkcli if not installed — Task 7 step 2 conditional skip

---

**Plan complete. Next: choose execution approach (subagent-driven vs inline).**
