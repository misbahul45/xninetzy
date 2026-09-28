# Changelog — Xninetzy

Format: [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

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

## [2.2.0] — 2026-09-11 — MCP-only pivot

### Removed
- Baileys WhatsApp engine
- Ink CLI
- LangGraph conversational agent loop
- `services/ai`, `services/wa-enggine`, `services/cli` (compose stack)
- Pre-pivot OS implementation progress doc (archived to `docs/archive/2026-09-11/`)

### Added
- Lightning RL bandit service (`xninetzy/os/lightning/`, 15 `lightning_*` tools)
- MCP resources and prompts (`xninetzy/interfaces/mcp_server.py`: 2 resources + 1 prompt)
- `redact_secrets` taxonomy (`xninetzy/core/security.py`, 8 patterns)
- `<memory_quarantine>` fence in `format_memories_for_prompt` (`xninetzy/os/memory/memory_store.py`)
- PyPI Trusted Publishing via OIDC (`.github/workflows/publish.yml`)
- Career Intelligence domain (17 tools in `xninetzy/tools/ecosystem/career_tools.py`, 19 skill bodies)
- Governance tests: `tests/governance/test_no_comments.py`,
  `tests/governance/test_skill_frontmatter.py`,
  `tests/governance/test_mcp_surface.py`

### Changed
- Architecture boundary: domain modules must never import `httpx`, `fastapi`, or MCP primitives
- RiskClass taxonomy: READ/DRAFT/WRITE/FINAL enforced via `xninetzy/os/policy/action_policy.py`
- FINAL tool whitelist: `hebat_upload_submission`, `portal_krs_war_arm`, `qa_fill_kuesioner`
  (drift detection in `tests/governance/test_mcp_surface.py`)

### Known issues
- ISS-20260919-01: SKILL.md YAML damage (CRITICAL, BLOCKED by hook — see `KNOWN_ISSUES.md`)

## [Unreleased]

### Documentation
- New: `KNOWN_ISSUES.md`, `CHANGELOG.md`, `ISSUE_TEMPLATE.md`
- New: `docs/runbooks/skill-repair.md`, `docs/SKILLS_INDEX.md`
- Archived: `docs/progress/XNINETZY_OS_IMPLEMENTATION_PROGRESS.md`,
  `docs/plan/phase_1_shared_contracts_goal.md`
- Banner-stripped: `docs/AI_PROVIDERS_CODING_AGENTS_MCP.md`
- Fixed: `CLAUDE.md` count drift (§6: 36→70, §7f: 14→19)
- Fixed: `CLAUDE.md` domain-creep contradiction (L22-23)
