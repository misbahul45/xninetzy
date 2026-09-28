# Xninetzy CLI Override — Codex

L2 (per-CLI override) of Xninetzy's Tiered Prompt Architecture. Overrides
ONLY Codex-specific behavior; the contract and rules live in L0 + L1.
## Mandatory Reads at Session Start
1. `~/.xninetzy/CORE_PROMPT.md` (L0, ~50 baris, hot)
2. `~/.xninetzy/CORE_RULES.md` (L1, ~120 baris, master rules)
3. `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` (continuity)
If any fails to resolve, STOP and report the missing file — no degraded fallback.
## Permission Map (Codex-native)
- `xninetzy_*` → allow
- `xninetzy_*delete*`, `*send*`, `*submit*`, `*commit*`, `*upload*`, `*enroll*`, `*update_record*`, `*finalize*` → ask
- `git push*`, `rm -rf*` → deny
- `playwright_*`, `github_*` → ask (per Codex default)
- `sequentialthinking`, `sequential*`, `codebase-memory-mcp_*`, `context7_*`, `paper_research_*`, `web_search_*`, `youtube_search_*`, `markitdown_*`, `document_generator_*`, `powerpoint_*` → allow
## Slash Aliases
`xn-resume`→`/resume`; `xn-research`→`xninetzy-deep-research`; `xn-assignment`→`hebat-assignment`; `xn-learn`→`it-learning`; `xn-doc`→`docx`; `xn-ppt`→`pptx`; `xn-hebat`→`xninetzy-hebat`; `xn-cyber`→`cyber-campus`; `xn-krs`→`xninetzy-krs`; `xn-verify`→`submission-readiness`.
## Format Quirks
GitHub-flavored Markdown; prefer `apply_patch` (Codex-native) for file edits; prefer absolute paths.
## Model Notes
Reasoning: `gpt-5.6-sol` with `xhigh` effort per `~/.codex/config.toml` (`model_reasoning_effort = "xhigh"`). Plan mode: `high`. Routing-first calls: no special model requirement.
## Codex-Specific Notes
MCP server `xninetzy` registered in `~/.codex/config.toml` `[mcp_servers.xninetzy]`; project trust levels under `[projects.*]`.
