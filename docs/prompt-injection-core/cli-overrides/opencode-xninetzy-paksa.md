# Xninetzy CLI Override — OpenCode

**L2 (per-CLI override)** layer of Tiered Prompt Architecture. Overrides ONLY OpenCode-specific behavior; contract + rules live in L0 + L1.

## Mandatory Reads at Session Start

1. `~/.xninetzy/CORE_PROMPT.md` (L0, ~50 baris, hot)
2. `~/.xninetzy/CORE_RULES.md` (L1, ~120 baris, master rules)
3. `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` (continuity)

If any reference fails to resolve, STOP and report. Do NOT fall back to degraded mode.

## Permission Map (OpenCode-native)

- `xninetzy_*` → `allow`
- `xninetzy_*delete*`, `*send*`, `*submit*`, `*commit*`, `*upload*`, `*enroll*`, `*update_record*`, `*finalize*` → `ask`
- `git push*`, `rm -rf*` → `deny`
- `playwright_*` → `ask`
- `github_*` → `ask` (or `deny` per OpenCode config)
- `sequentialthinking`, `sequential*` → `allow`
- `codebase-memory-mcp_*` → `allow`
- `context7_*`, `paper_research_*`, `web_search_*`, `youtube_search_*`, `markitdown_*` → `allow`
- `document_generator_*`, `powerpoint_*` → `allow`

## Slash Aliases

- `xn-resume` → `/resume`; `xn-research` → skill `xninetzy-deep-research`
- `xn-assignment` → skill `hebat-assignment`; `xn-learn` → skill `it-learning`
- `xn-doc` → skill `docx`; `xn-ppt` → skill `pptx`
- `xn-hebat` → skill `xninetzy-hebat`; `xn-cyber` → skill `cyber-campus`
- `xn-krs` → skill `xninetzy-krs`; `xn-verify` → skill `submission-readiness`

## Format Quirks

- Markdown: CommonMark + GFM tables; language-tagged code blocks (`python`/`bash`/`yaml`); prefer `~/...` for user-level paths, absolute for repo.

## Model Notes

- Prefer `opus[1m]` or `gpt-5.6-sol` with high effort; routing-first calls have no special model requirement.
