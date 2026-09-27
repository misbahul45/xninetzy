---
layout: ../../layouts/DocsLayout.astro
title: Host CLI Agent Injection Contract
description: Mandatory xninetzy operating-layer prompt injected into host CLI agents (Cursor, Claude Code, Codex, Gemini CLI, Vibe, Copilot, OpenClaw, Qwen, Kilo, Trae, OpenCode).
section: AI & developer tools
---

Xninetzy is an MCP layer, not an agent. Host CLI agents (Cursor, Claude Code,
Codex, Gemini CLI, Vibe, Copilot, OpenClaw, Qwen, Kilo, Trae, OpenCode) own the
reasoning loop. xninetzy extends them with tools, skills, memory, graph,
security, and Lightning self-improvement.

The injection contract below forces the host agent to use xninetzy
**diagnostically** — when the user intent actually maps to an xninetzy
capability — instead of as a generic MCP spam layer.

## Purpose

Convert 12 host CLI prompt files into xninetzy-aware agents that:

- use `xninetzy_*` MCP tools for owner-data tasks (Obsidian, knowledge,
  memory, learning, HEBAT, Cyber Campus, KRS, UACC, career, etc.)
- skip MCP overhead on trivial tasks
- invoke Sequential Thinking (if available) for multi-step /
  cross-domain / debugging / research / security work
- route via intent → domain → cluster → skill, not keyword match
- honor HITL for destructive / external / high-impact actions
- preserve evidence chain, provenance, and audit trail

## 8-Stage Operating Layer

Every task flows through these stages. Each stage may skip if the
diagnostic finds it unnecessary.

```text
USER TASK
  ↓ L0 CAPTURE — parse intent + side-effect class + risk
L0 Intent class ∈ {trivial, read_only, multi_step, cross_domain, destructive}
   Side effect ∈ {read_only, reversible, state_changing, external, destructive}
   Risk ∈ {low, medium, high, final}
  ↓ L1 UNDERSTAND — Sequential Thinking MCP if available + non-trivial
L1 Decompose → constraint → uncertainty → required tools/skills
   Trivial? skip ST. Cross-domain / debugging / research / security
   / multi-step / costly-mistake? INVOKE ST first + last.
  ↓ L2 CONTEXT RETRIEVAL — graph / memory / codebase
L2 xninetzy_graph_v3_search + memory_get_context + codebase-memory search_graph
   Skip if task already self-contained.
  ↓ L3 SKILL ROUTING — diagnostic, not keyword match
L3 Intent → domain → task type → cluster → xninetzy_skill_*
   See trigger matrix.
   Not every task needs a skill. CHECK FIRST.
  ↓ L4 EXECUTE — xninetzy_* MCP tools + xninetzy_skill_get + resource
L4 Skill body via xninetzy_skill_get(name) if L3 matches.
   Resource lazy-load via xninetzy_skill_resource_list + read.
  ↓ L5 VERIFY — validator cluster + check result
L5 xninetzy_skill_validate_output / anti_slop / submission_readiness
   or evidence + citation + freshness + contradiction checks.
  ↓ L6 LEARN — proportional, not lecture
L6 Explain WHY when user asks / concept is new / pattern is reusable.
  ↓ L7 ADAPT — memory + graph update for stable decisions only
```

## Domain → Cluster Map

xninetzy serves 15 domains. Each domain has 2–6 clusters. Each cluster
maps to one or more skills. The full trigger matrix lives in
[CLI injection tutorial](/docs/cli-injection-tutorial/).

| Domain | Clusters |
|--------|----------|
| ACADEMIC | research, writing, citation, anti-slop, assignment, orchestrate-academic |
| SECURITY | code-review, threat, pentest, safety |
| CODE | repo, review, test, mcp-build, orchestration, ci |
| RESEARCH | plan, collect, grade, write, critic |
| DATA | profile, analyze, viz, doc |
| KNOWLEDGE | knowledge, vault-ops, memory, helper |
| LEARNING | coach, session, recall, evolve |
| ARTIFACT | doc, slide, report, ship |
| PERSONAL-OS | goal, habit, finance, review, capture |
| CAREER | search, match, research, ops |
| BUSINESS | analyze, propose, write, present |
| WEB | browse, capture, extract |
| MEDIA | audio, image, doc, video |
| SELF-IMPROVE | episode, proposal, evaluate, safety |
| DOCS / PROCESS | techdoc, process |

## Human Control Tiers

| Tier | Examples | Action |
|------|----------|--------|
| INFORMATIONAL | explain / define / describe | proceed |
| READ_ONLY | search / list / inspect | proceed if safe |
| REVERSIBLE | create draft / add note / write file | proceed per policy |
| STATE_CHANGING | update DB / submit form / sync portal | evaluate; HITL if FINAL |
| DESTRUCTIVE | delete / drop / rm / push / finalize | HITL required |
| EXTERNAL_HIGH_IMPACT | submit assignment / send message / pay | HITL required |

## Auditability

Every skill invocation must answer:

```
WHY triggered?
  → Intent class → L0
  → Domain + cluster → L3 (trigger matrix match)
  → Skill → xninetzy_skill_get result
  → Action → xninetzy_* tools
  → Result + validator → L5
```

Evidence: `xninetzy_observability_query(subject=<plan_id>)` +
`xninetzy_evaluation_audit_skill_catalog` +
`xninetzy_skill_healthcheck`.

## Target Files

| CLI | Path |
|-----|------|
| Claude Code | `~/.claude/CLAUDE.md` |
| Codex | `~/.codex/AGENTS.md` |
| Cursor | `~/.cursor/rules/xninetzy.mdc` |
| Gemini CLI | `~/.gemini/GEMINI.md` |
| Vibe | `~/.vibe/AGENTS.md` |
| Copilot | `~/.copilot/AGENTS.md` |
| OpenClaw | `~/.openclaude/CLAUDE.md` |
| Qwen | `~/.qwen/QWEN.md` |
| Kilo | `~/.config/kilo/AGENTS.md` |
| Trae | `~/.trae/AGENTS.md` |
| Agents | `~/.agents/AGENTS.md` |
| OpenCode | `~/.config/opencode/AGENTS.md` |

## Block Structure

Each injected file receives the same five sections:

1. **Mandatory File Handler** — owner-data tasks must use `xninetzy_*`
   MCP (memory, knowledge, obsidian, learning, etc.). Never vendor
   `Read` / `Write` / `Edit` on vault / knowledge base.
2. **Mandatory Skill / Capability Handler** — owner-data extends to
   harness, lightning, security, personal OS, HEBAT, career, web,
   media, observability, HITL.
3. **Mandatory Skill Maximize** — every task must use
   `xninetzy_skill_*` (discover → suggest → load → validate →
   execute). 100+ skills in the catalog.
4. **Trigger Matrix** — diagnostic table per domain / cluster.
5. **XNINETZY OPERATING LAYER** — 8-stage flow + Sequential Thinking
   integration + Human Control Tiers.

OpenCode is appended after the existing v2.0.0 Operating Rules to
preserve governance hierarchy.

## Behavioral Test Coverage

12 synthetic tests verify routing:

1. Trivial lookup → no MCP overhead
2. Complex debugging → Sequential Thinking + CODE.test
3. Research request → RESEARCH.collect + research-critic
4. Academic assignment → ACADEMIC.assignment + submission-readiness
5. Security audit → SECURITY.code-review + regression-analysis
6. Multi-domain research + code + artifact → RESEARCH → CODE → ARTIFACT
7. Existing-code modification → CODE.repo + CODE.test
8. Learning task → LEARNING.coach + recall
9. Automation request → AUTOMATION + structured-project-execution
10. Ambiguous task → clarify, not invoke
11. Destructive operation → HALT + HITL
12. Trivial JSON format → no MCP overhead

See the [CLI injection tutorial](/docs/cli-injection-tutorial/) for
the test results and routing failures.
