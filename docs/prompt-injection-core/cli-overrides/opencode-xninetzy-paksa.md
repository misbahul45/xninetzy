# Xninetzy CLI Override — OpenCode

**L2 (per-CLI override)** layer of Tiered Prompt Architecture. Overrides ONLY OpenCode-specific behavior; contract + rules live in L0 + L1.

## Mandatory Reads at Session Start

1. `~/.xninetzy/CORE_PROMPT.md` (L0, ~50 baris, hot)
2. `~/.xninetzy/CORE_RULES.md` (L1, ~120 baris, master rules)
3. `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` (continuity)

If any reference fails to resolve, STOP and report. Do NOT fall back to degraded mode.

## Permission Map (OpenCode-native)

- `xninetzy_*` → `allow`; destructive (`*delete*`, `*send*`, `*submit*`, `*commit*`, `*upload*`, `*enroll*`, `*update_record*`, `*finalize*`) → `ask`; `git push*`, `rm -rf*` → `deny`
- `playwright_*`, `github_*` → `ask`
- `sequentialthinking`, `codebase-memory-mcp_*` → `allow`
- `context7_*`, `paper_research_*`, `web_search_*`, `youtube_search_*`, `markitdown_*` → `allow`
- `document_generator_*`, `powerpoint_*` → `allow`

## Slash Aliases

- `xn-resume` → `/resume`; `xn-research` → `xninetzy-deep-research`
- `xn-assignment` → `hebat-assignment`; `xn-learn` → `it-learning`
- `xn-doc` → `docx`; `xn-ppt` → `pptx`
- `xn-hebat` → `xninetzy-hebat`; `xn-cyber` → `cyber-campus`
- `xn-krs` → `xninetzy-krs`; `xn-verify` → `submission-readiness`

## Format Quirks

- CommonMark + GFM tables; lang-tagged code blocks (`python`/`bash`/`yaml`); `~/...` for user paths, absolute for repo.

## Model Notes

- Prefer `opus[1m]` or `gpt-5.6-sol` with high effort; routing-first calls have no special model requirement.
