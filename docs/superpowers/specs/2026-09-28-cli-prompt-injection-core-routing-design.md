# CLI Prompt Injection — CORE + Routing Engine

**Date:** 2026-09-28
**Author:** Xninetzy (brainstorming → design)
**Status:** Draft → awaiting user review
**Scope:** Sub-A (CORE + Routing) of 3-sub-project decomposition

---

## 1. Problem Statement

Owner wants to inject the Xninetzy routing engine capabilities (domain routing, skills routing, tools routing engine layer) plus harness context, memory, workflow, self-improving, Lightning, Graph, ingest, and sequential thinking into ALL AI CLIs on the system (OpenCode, Claude Code, Codex, arkcli).

The codebase already exposes 508 MCP tools via the `xninetzy` MCP server, with a sophisticated 5-layer routing pipeline (`xninetzy/context/routing/`), skill registry (`xninetzy/skills/`), and tool registry (`xninetzy/tools/registry.py`). However, the system prompts injected into each CLI are generic — they mention "xninetzy" but do not explicitly call out the routing engine structure, intent classes, side-effect classification, or the layered L0/L1/L2 contract that maximizes context efficiency.

**Goal:** Create a Tiered Prompt Architecture (L0 hot, L1 rules, L2 CLI override) that:
1. Places routing-first at the top of every CLI session context
2. Minimizes per-session token cost (~500 token hot prompt)
3. Preserves single source of truth for behavior contract
4. Maintains CLI-specific permissions, slash commands, and format quirks per CLI

**Non-Goal (this spec):** Sub-B (memory/workflow deep-dive) and Sub-C (Lightning/Graph/ingest) — these are decomposed as follow-on sub-projects in §7.

---

## 2. Audit Findings (Current State)

### Existing prompt infrastructure

| File | Location | Lines | Purpose |
|---|---|---|---|
| `CORE_PROMPT.md` | `~/.xninetzy/` | 131 | Master mandatory injection (identity, sequential thinking, workflow, MCP priority, skill loading, slash, forbidden/required, permission) |
| `CLI_SHARED_INSTRUCTIONS.md` | `~/.xninetzy/` | 139 | Shared continuity, context across sessions, Paksa Mode instructions |
| `AGENTS.md` | `~/.codex/` | (existing) | Codex session-start instructions, references CORE_PROMPT.md and CLI_SHARED_INSTRUCTIONS.md |
| `opencode.jsonc` | `~/.config/opencode/` | (config) | Has `instructions[]` = `[AGENTS.md, README.md, instructions/xninetzy-paksa.md]` |
| `xninetzy-paksa.md` | `~/.config/opencode/instructions/` | (existing) | Local injection for OpenCode Paksa Mode |
| `CLAUDE.md` | `/home/misbahul45/code/xninetzy/` | (existing) | Repo entry point for Claude Code in xninetzy repo |
| `settings.json` | `~/.claude/` | (existing) | Claude Code global settings, model selection |

### Code modules available but NOT explicitly covered in prompts

| Subsystem | Code path | Current prompt coverage |
|---|---|---|
| Domain routing | `xninetzy/domains/`, `xninetzy/context/registry/taxonomy.py` (SEMANTIC_DOMAINS) | Generic only |
| Skills routing | `xninetzy/skills/router.py` (INTENT_CLASSES, INTENT_KEYWORDS) | Generic only |
| Tools routing | `xninetzy/context/routing/` (5-layer pipeline) | Generic only |
| Engine layer | `xninetzy/context/intake/`, `xninetzy/context/orchestrator/` | Not mentioned |
| Harness | `xninetzy/context/invocation/` | Not mentioned |
| Memory | `xninetzy/os/memory/` | Lifecycle mentioned generically |
| Workflow | `xninetzy/workflow/` | Not mentioned |
| Lightning | `xninetzy/os/lightning/` | Not mentioned |
| Graph (RAG) | `xninetzy/os/graph/`, `xninetzy/skills/graph_rag/` | Mentioned vaguely |
| Ingest | `xninetzy/os/knowledge/` | Not mentioned |
| Sequential thinking | (external MCP) | Explicit ✅ |

### AI CLIs identified in system

1. **OpenCode** (`~/.config/opencode/`) — has MCP server `xninetzy` connected, has `xninetzy-paksa.md`
2. **Claude Code** (`~/.claude/`) — has skills synced from `xninetzy` (in `~/.claude/skills/`), has plugins (in `~/.claude/plugins/`), `settings.json` exists
3. **Codex** (`~/.codex/`) — has MCP server `xninetzy` configured, has `AGENTS.md`
4. **arkcli-related** (skill catalog found) — needs verification

### Existing prompt content already covers (must be preserved)

- Identity Lock: Xninetzy Personal Learning OS & Life OS agent
- Sequential Thinking engine lock (first/last on every non-trivial step)
- Workflow lock: UNDERSTAND → LEARN → RESEARCH → DECIDE → BUILD → VERIFY → CONTINUE
- MCP Tools Priority Table (10 ranks)
- Skill Loading Order (5 steps)
- Slash commands (xn-* prefix)
- Forbidden behaviors (8 absolute)
- Required behaviors (8 absolute)
- Permission context (`xninetzy_*` allow, consequential ask)

---

## 3. Design — Tiered Prompt Architecture (Approach C)

### 3.1 Three-Layer Structure

```
┌──────────────────────────────────────────────────────────┐
│ L0: HOT PROMPT (~50 baris, ~600 token, SELALU di-load)  │
│ ~/.xninetzy/CORE_PROMPT.md                               │
│ ──────────────────────────────────────────────────────── │
│ Identity Lock          (meta, top)                       │
│ #1 ROUTING-FIRST       ← directive + minimal reference  │
│ #2 Reasoning Engine Lock (sequential thinking)            │
│ #3 WORKFLOW LOCK       UNDERSTAND→VERIFY                 │
│ #4 MCP TOOL PRIORITY   tabel 10 rank                     │
│ #5 SKILL LOADING ORDER 3 baris                           │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼ (@-reference dari L2)
┌──────────────────────────────────────────────────────────┐
│ L1: MASTER RULES (~120 baris, ~1.5K token)               │
│ ~/.xninetzy/CORE_RULES.md   (NEW FILE)                   │
│ ──────────────────────────────────────────────────────── │
│ #6 Forbidden behaviors (8 rules)                         │
│ #7 Required behaviors (8 rules)                          │
│ #8 Memory & Workflow hooks (basic)                       │
│ #9 Slash command mapping (xn-* → CLI-native)             │
│ #10 Permission context                                   │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼ (CLI config: 3+ lokasi)
┌──────────────────────────────────────────────────────────┐
│ L2: CLI OVERRIDE (~25 baris per CLI)                     │
│ ~/.config/opencode/instructions/xninetzy-paksa.md        │
│ ~/.claude/CLAUDE.md                                      │
│ ~/.codex/AGENTS.md                                       │
│ ~/.arkcli/config/AGENTS.md (jika ada)                    │
│ ──────────────────────────────────────────────────────── │
│ • Permission map (xninetzy_* allow, *delete* ask)        │
│ • Slash command aliases                                  │
│ • Format quirks (markdown render, etc.)                  │
│ • Trust level / model-specific notes                     │
└──────────────────────────────────────────────────────────┘
```

### 3.2 L0 — Hot Prompt (reorder + expand existing `CORE_PROMPT.md`)

The existing `~/.xninetzy/CORE_PROMPT.md` becomes L0. Sections are **reordered** per user's chosen sequence: **Routing → Workflow → Tools → Skill → Validation**, with Identity Lock as a meta-header at the top and Reasoning Engine Lock between Routing and Workflow.

**Identity Lock (meta, top, ~3 baris)** — preserved from existing `CORE_PROMPT.md`:
```markdown
You operate as the Xninetzy Personal Learning OS & Life OS agent.
Default agent is `xninetzy`. Domain owner scope is the local installation.
```

**Required new section #1 (Routing-First, ~15 baris):**

```markdown
# #1 ROUTING-FIRST  (Place at top of every non-trivial turn)

Default routing engine: xninetzy_context_routing_pipeline (5 layers).

WAJIB di setiap non-trivial turn:
  1. Call `xninetzy_skill_suggest_for_request(query)`
  2. Call `xninetzy_skill_get(top_match)`
  3. Follow skill procedure: input → evidence → structure → draft → validation
  4. Run validation pass: anti-slop, citation-fidelity, evidence-claim-alignment

Ringkasan referensi:
  • 9 Intent Classes: PROFESSIONAL | CONSULTING | PROPOSAL | ACADEMIC |
    RESEARCH | TECHNICAL | EDITING | REVIEW | MEDIA
  • 5 Side-Effect Classes: read_only | idempotent_write | non_idempotent_write |
    external_side_effect | irreversible (requires_approval=True)
  • 8 Semantic Domains: learning | career | academic | research | development |
    business | security | life_os
  • Tool Routing Layers: L2_domain → L3_skill → L4_task → L5_tool → L5_capability
```

**Section #2 (Reasoning Engine Lock, ~3 baris)** — preserved, compressed:
```markdown
# #2 REASONING ENGINE LOCK
When `sequentialthinking` MCP is available, invoke it FIRST and LAST on every
non-trivial step. Reasoning chain = the system; answer = side-effect.
```

**Section #3 (Workflow Lock, ~3 baris)** — preserved:
```markdown
# #3 WORKFLOW LOCK
UNDERSTAND → LEARN → RESEARCH → DECIDE → BUILD → VERIFY → CONTINUE.
Every non-trivial turn must traverse this chain.
```

**Section #4 (MCP Tools Priority, ~12 baris)** — preserved, compressed:
```markdown
# #4 MCP TOOLS PRIORITY
| Rank | Prefix | Domain |
| 1 | xninetzy_* | owner-scoped OS |
| 2 | sequentialthinking | reasoning |
| 3 | codebase-memory-mcp | code structure |
| 4-9 | paper_research, context7, web_search, youtube_search, markitdown, playwright | (see CORE_RULES) |
| 10 | powerpoint / document_generator | artifact output |
Generic vendor tools (Read/Write/Bash) = last resort.
```

**Section #5 (Skill Loading Order, ~3 baris)** — compressed to 3 baris in L0, full version in L1:
```markdown
# #5 SKILL LOADING ORDER
1. xninetzy_skill_suggest_for_request(query)
2. xninetzy_skill_get(top_match) + progressive resource disclosure
3. Follow procedure → run validation pass (full details in CORE_RULES.md)
```

### 3.3 L1 — Master Rules (new file `~/.xninetzy/CORE_RULES.md`)

New file, ~120 baris. Contents:

```yaml
# #5 FORBIDDEN BEHAVIORS (Absolute)
- ❌ Claim tool/skill used when not invoked
- ❌ Fabricate URLs, citations, deadlines, file contents
- ❌ Bypass CAPTCHA/OTP/MFA
- ❌ Submit academic deliverables without owner approval
- ❌ Replace existing submission without confirmation
- ❌ Skip validation pass on submit-bound artifacts
- ❌ Skip grounding for assignment/task
- ❌ Lose cross-session state by not persisting checkpoint

# #6 REQUIRED BEHAVIORS (Absolute)
- ✅ Verify via tools before claiming success
- ✅ Save checkpoint after every milestone
- ✅ Run validation pass before final delivery
- ✅ Preserve evidence chain (claim → source → artifact)
- ✅ Honor freshness rule: re-check external state before consequential action
- ✅ Use memory lifecycle: working → episodic → semantic → procedure
- ✅ End every non-trivial turn with checkpoint OR explicit next_action
- ✅ Call sequentialthinking FIRST and LAST on every non-trivial step

# #7 MEMORY & WORKFLOW HOOKS (basic, expand in Sub-B)
- After milestone → `memory_add` concise decision/blocker/artifact-state
- Before consequential action → `harness_checkpoint_commit`
- After artifact → record path, hash, verification
- On resume/pivot → `memory_get_context` with narrow query

# #8 SLASH COMMAND MAPPING (xn-* → CLI-native)
| xn-* | OpenCode | Claude Code | Codex | Purpose |
|------|----------|-------------|-------|---------|
| xn-resume | /resume | /resume | (native: /resume) | Resume from checkpoint |
| xn-research | /deep-research | /deep-research | (none — fall back to MCP) | Deep research multi-agent |
| xn-assignment | (skill: hebat-assignment) | (skill: hebat-assignment) | (skill) | Academic orchestration |
| xn-learn | (skill: it-learning) | (skill: it-learning) | (skill) | Adaptive learning |
| xn-doc | /doc | (skill: docx) | (skill: docx) | DOCX/PDF artifact |
| xn-ppt | /ppt | (skill: pptx) | (skill: pptx) | PPTX artifact |
| xn-hebat | (skill: xninetzy-hebat) | (skill) | (skill) | HEBAT analysis |
| xn-cyber | (skill: cyber-campus) | (skill) | (skill) | Cyber Campus |
| xn-krs | (skill: xninetzy-krs) | (skill) | (skill) | KRS planning |
| xn-verify | /verify | (skill: submission-readiness) | (skill) | Verify before done |

# #9 PERMISSION CONTEXT
- `xninetzy_*` tools → default `allow`
- Consequential actions (`*delete*`, `*send*`, `*submit*`, `*commit*`,
  `*upload*`, `*enroll*`, `*update_record*`, `*finalize*`) → `ask`
- `git push` and `rm -rf` → `deny`
```

### 3.4 L2 — CLI Override (per-CLI files, ~25 baris each)

Each CLI gets a minimal override file containing ONLY CLI-specific quirks, not behavior contract (which lives in L0/L1).

**Pattern (uniform across CLIs):**

```markdown
# Xninetzy CLI Override — <CLI_NAME>

Read `~/.xninetzy/CORE_PROMPT.md` (L0) and `~/.xninetzy/CORE_RULES.md` (L1)
at session start. This file overrides ONLY CLI-specific behavior.

## Permission Map (CLI-native)
- xninetzy_* → allow
- *delete* / *send* / *submit* / *commit* / *upload* / *enroll* / *update_record* / *finalize* → ask
- github_* → ask / deny (per CLI config)
- playwright_* → ask
- sequentialthinking → allow

## Slash Aliases
| xn-* | This CLI |
|------|----------|
| xn-resume | /resume (native) |
| xn-research | (skill: xninetzy-deep-research) |
| ... |

## Model Notes
- Preferred model: <MODEL>
- Reasoning effort: <EFFORT>

## Format Quirks
- <CLI-SPECIFIC FORMATTING NOTES>
```

**OpenCode-specific (`~/.config/opencode/instructions/xninetzy-paksa.md`):**
- Already exists, restructure to match L2 pattern
- Add explicit references to L0 + L1

**Claude Code-specific (`~/.claude/CLAUDE.md`):**
- New file (currently does not exist)
- Reference project `CLAUDE.md` at `/home/misbahul45/code/xninetzy/CLAUDE.md` if in that workspace

**Codex-specific (`~/.codex/AGENTS.md`):**
- Already exists, restructure to match L2 pattern
- Keep existing CORE_PROMPT.md reference

**arkcli-specific (verify existence):**
- Check `~/.arkcli/` or `~/.config/arkcli/` directory
- Create if missing

---

## 4. Data Flow & Side-Effect Decision Tree

### 4.1 Per-User-Request Flow

```
[USER PROMPT]
     │
     ▼
[L0: ROUTING-FIRST]  ← ALWAYS injected first (~500 token)
  ├─ xninetzy_skill_suggest_for_request(query)
  ├─ xninetzy_skill_get(top_match)
     │
     ▼
[L0: WORKFLOW LOCK]
  UNDERSTAND → LEARN → RESEARCH → DECIDE → BUILD → VERIFY → CONTINUE
     │
     ▼
[L0: MCP PRIORITY]   ← xninetzy_* (1) → sequentialthinking (2) → context7/paper/web (3-9)
     │
     ▼
[SKILL EXECUTION]
  • Load skill resources progressively
  • Follow operating procedure
  • Run validation pass
     │
     ▼
[L1: RULES ENFORCEMENT]
  • Check forbidden behaviors (8)
  • Verify required behaviors (8)
  • Update memory if milestone
  • Persist checkpoint if external action
     │
     ▼
[L2: CLI-SPECIFIC]
  • Apply permission gates
  • Execute slash command mapping (jika slash)
  • Render dengan CLI-specific format
     │
     ▼
[FINAL RESPONSE]
```

### 4.2 Side-Effect Decision Tree (Routing Component)

```
side_effect = classify(query)
  │
  ├── read_only          → execute immediately
  │                         (e.g., knowledge_search, obsidian_read)
  │
  ├── idempotent_write   → execute + idempotency_key
  │                         (e.g., obsidian_create, task_capture)
  │
  ├── non_idempotent_write → ASK before execute
  │                           (e.g., task_complete, money_add)
  │
  ├── external_side_effect → ASK + idempotency_key
  │                           (e.g., hebat_upload, cyber_portal_call)
  │
  └── irreversible       → MANDATORY HITL approval
                            (e.g., submission, payment, krs_commit)
```

This decision tree is reflected in L0 routing-first block so agent classifies before acting.

---

## 5. Error Handling

| Failure mode | Detection | Response |
|---|---|---|
| Routing abstain (confidence < 0.4) | `xninetzy_routing_inspect` returns low confidence | Fall back to `sequentialthinking`, explicit step-by-step reasoning |
| Skill not found | `skill_suggest_for_request` returns empty | Skip skill loading, continue with bare workflow + manual reasoning |
| MCP server unavailable | Tool call returns 503 / connection error | Show actionable config error, NOT degraded mode (per AGENTS.md invariant) |
| Context budget exceeded | Token counter approach threshold | Compact older sections, preserve L0 routing-first + identity lock |
| Permission denied | CLI gate refuses | Respect CLI decision, log ke `memory_failure_store`, escalate ke owner |
| Forbidden behavior triggered | Rule violation detected | STOP immediately, log ke `memory_failure_store`, return error |
| Reference resolution failure | `@-reference` to L0/L1 broken | Re-read CORE_PROMPT.md and CORE_RULES.md before failing |
| arkcli CLI not present | File/directory check fails | Skip arkcli injection, log warning, do not fail other CLIs |

---

## 6. Testing & Verification Strategy

### 6.1 Automated checks (`scripts/verify_prompt_injection.sh`)

```bash
#!/usr/bin/env bash
# Verify Tiered Prompt Architecture integrity

set -euo pipefail

# L0 checks
test -f ~/.xninetzy/CORE_PROMPT.md || { echo "FAIL: L0 missing"; exit 1; }
LINES=$(wc -l < ~/.xninetzy/CORE_PROMPT.md)
test "$LINES" -le 60 || { echo "WARN: L0 too long ($LINES > 60, target ≤50)"; }

# L1 checks
test -f ~/.xninetzy/CORE_RULES.md || { echo "FAIL: L1 missing"; exit 1; }
LINES=$(wc -l < ~/.xninetzy/CORE_RULES.md)
test "$LINES" -ge 100 && test "$LINES" -le 200 || { echo "WARN: L1 unexpected length ($LINES)"; }

# Section ordering check
head -20 ~/.xninetzy/CORE_PROMPT.md | grep -qi "routing" || { echo "FAIL: routing not in L0 top 20 lines"; exit 1; }

# CLI overrides
for CLI_DIR in ~/.config/opencode ~/.claude ~/.codex; do
  test -d "$CLI_DIR" || continue
  echo "WARN: check $CLI_DIR manually for override file"
done

# Reference integrity
grep -q "@.*CORE_PROMPT\|Read.*CORE_PROMPT" ~/.xninetzy/CORE_RULES.md || { echo "WARN: L1 doesn't reference L0"; }

echo "OK: prompt injection verification passed"
```

### 6.2 Cross-CLI integration test (manual, 5 representative queries)

Test with each CLI to confirm routing-first triggers correctly:

1. **Academic**: "Bantu saya kerjakan tugas HEBAT hari ini"
   - Expected: routes to `hebat-academic` skill, then `xninetzy-hebat` MCP
2. **Coding**: "Cari bug di function X"
   - Expected: routes to `debugging` skill, then `codebase-memory-mcp`
3. **Security**: "Audit SAST pada repo ini"
   - Expected: routes to `security-review` skill, then `xninetzy_security_sast`
4. **Career**: "Cari lowongan backend remote"
   - Expected: routes to `job-discovery` skill, then `xninetzy_career_search_jobs`
5. **Life OS**: "Buat daily plan hari ini"
   - Expected: routes to `todolife-daily-planner` skill, then `xninetzy_life_dashboard`

For each: verify agent invokes `xninetzy_skill_suggest_for_request` FIRST, then loads correct skill, then uses correct MCP tool.

### 6.3 Visual inspection

- `cat ~/.xninetzy/CORE_PROMPT.md | head -20` should show routing-first directive
- `cat ~/.xninetzy/CORE_RULES.md | head -40` should show forbidden + required rules

---

## 7. Sub-B & Sub-C Roadmap (Decomposition Preview)

### Sub-A (THIS SPEC) — CORE + Routing
- **Files**: `~/.xninetzy/CORE_PROMPT.md` (L0 reorder), `~/.xninetzy/CORE_RULES.md` (L1 NEW), 3 CLI override files
- **Subsystems covered**: Domain routing, skills routing, tools routing engine, sequential thinking
- **Subsystems deferred**: Memory hooks (basic only), workflow hooks (basic only)
- **Estimated scope**: ~280 baris total (40 + 120 + 25×3), ~5 file changes

### Sub-B — Stateful Subsystems Deep-Dive (ITERATION 2)
- **Files**: `~/.xninetzy/CORE_MEMORY.md`, `~/.xninetzy/CORE_WORKFLOW.md` (L1.5)
- **Subsystems**: Memory lifecycle (working→episodic→semantic→procedure), harness context, workflow execution
- **MCP tools surface**: `xninetzy_memory_*`, `xninetzy_workflow_*`, `xninetzy_personal_*`, `xninetzy_reminder_*`, `xninetzy_harness_*`
- **Estimated scope**: ~200 baris tambahan, 2 file baru

### Sub-C — Knowledge & Learning Systems (ITERATION 3)
- **Files**: `~/.xninetzy/CORE_KNOWLEDGE.md` (L1.5)
- **Subsystems**: Lightning (RL episodic learning), Graph RAG (Neo4j+FAISS), Knowledge Ingest (FAISS chunks), Self-improving loop
- **MCP tools surface**: `xninetzy_lightning_*`, `xninetzy_graph_v3_*`, `xninetzy_knowledge_*`, `xninetzy_research_*`, `xninetzy_improvement_*`
- **Estimated scope**: ~250 baris, 1 file baru

### Dependency Graph
```
Sub-A (CORE + Routing)  ← Foundation, WAJIB duluan
    ↓
Sub-B (Memory + Workflow + Harness)  ← butuh routing context
    ↓
Sub-C (Lightning + Graph + Ingest)  ← butuh memory context
    ↓
[Future] Sub-D (per-domain specialization: video, tableau, career, dll)
```

---

## 8. Acceptance Criteria

**Definition of done for Sub-A:**

1. ✅ `~/.xninetzy/CORE_PROMPT.md` reordered with Routing-First as section #1 (Identity Lock as meta-header, Reasoning Engine as #2, Workflow as #3, MCP Priority as #4, Skill Loading as #5)
2. ✅ `~/.xninetzy/CORE_RULES.md` created with forbidden/required rules (sections #6-#7), memory/workflow hooks (#8), slash mapping (#9), permission context (#10)
3. ✅ OpenCode override updated at `~/.config/opencode/instructions/xninetzy-paksa.md`
4. ✅ Claude Code override created at `~/.claude/CLAUDE.md`
5. ✅ Codex override updated at `~/.codex/AGENTS.md`
6. ✅ arkcli override created if directory exists
7. ✅ `scripts/verify_prompt_injection.sh` passes
8. ✅ All 5 representative queries route correctly in each CLI (manual smoke test)
9. ✅ No regression: existing forbidden/required behaviors preserved
10. ✅ Token budget: L0 ≤ 50 baris (~600 token) — bumped from 40 due to Identity Lock + Reasoning Engine Lock inclusion

**Out of scope for Sub-A (will not implement):**
- Memory deep-dive (Sub-B)
- Workflow deep-dive (Sub-B)
- Lightning / Graph / Ingest (Sub-C)
- Per-domain specialization (Sub-D)
- Full L1.5 layer (only L0 + L1 + L2 in this iteration)

---

## 9. Future Work (Lampiran / Follow-up)

### 9.1 Complete Install Documentation (`apps/docs/`)

After Sub-A implementation, write **lengkap dokumentasi proses install Xninetzy** di `apps/docs/`:

- **Target audience**: New owner who clones `xninetzy` for first time
- **Coverage**:
  - OS prereqs (Linux/macOS/Windows PowerShell)
  - One-line installer scripts (Linux/macOS, Windows)
  - Manual install steps
  - MCP host configuration (Claude Code, Codex, OpenCode, arkcli)
  - First-time `supervisor init` walkthrough
  - Verification: `release-check`, `mcp list`, smoke test
  - Troubleshooting matrix (common errors → solutions)
  - Architecture overview with L0/L1/L2 prompt injection flow
- **Format**: Astro Starlight docs (consistent with `apps/docs/` existing structure)
- **Acceptance**: New owner can complete install in ≤15 minutes following the doc

This is a follow-up task and will be scheduled separately after Sub-A implementation.

### 9.2 Other follow-ups (lower priority)

- Sub-B implementation plan + spec
- Sub-C implementation plan + spec
- Sub-D per-domain vertical specialization

---

## 10. Risks & Open Questions

### Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| L0 prompt grows beyond 50 baris over time | Medium | High — defeats context efficiency goal | Add L0 length check to `verify_prompt_injection.sh`, warn at >60 baris |
| CLI override files drift from L0/L1 contract | Medium | Medium — silent behavior inconsistency | Single source of truth: forbid behavior contract in L2; L2 only references L0/L1 |
| arkcli CLI configuration unknown | Low | Low — skip if missing | Verify at audit, log warning, do not fail other CLIs |
| Existing CLI configs lose specific quirks during refactor | Medium | Medium — break CLI-specific features | Capture existing quirks BEFORE refactor; preserve in L2 |
| `@-reference` resolution breaks between L0/L1/L2 | Low | High — agent gets no injection | Add explicit `Read ~/.xninetzy/CORE_PROMPT.md` fallback in each L2 |

### Open Questions

1. **arkcli existence**: Does arkcli actually have a `~/.arkcli/config/` location? Need to verify.
2. **Token budget**: Is 500 token (L0) + 1500 token (L1) acceptable for OpenCode? Codex? Claude Code?
3. **Slashing command parity**: Do `xn-*` slash commands need to be registered in each CLI's slash command registry, or are they skill-invoked only?
4. **Cross-workspace CLAUDE.md**: Should `~/.claude/CLAUDE.md` delegate to workspace-level `CLAUDE.md` (in `code/xninetzy/`) when in that workspace?

---

## 11. Change Log

- 2026-09-28: Initial draft via brainstorming flow (audit → clarifying Q → 3-chunk design → spec write)
- Status: Draft, awaiting user review

---

**End of Sub-A spec. After user approval → invoke `writing-plans` skill for implementation plan.**
