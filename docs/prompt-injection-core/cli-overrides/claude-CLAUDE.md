# Xninetzy CLI Override — Claude Code

L2 (per-CLI override) of Xninetzy's Tiered Prompt Architecture. Overrides
ONLY Claude Code-specific behavior; the contract and rules live in L0 + L1.
## Mandatory Reads at Session Start
1. `~/.xninetzy/CORE_PROMPT.md` (L0, ~50 baris, hot)
2. `~/.xninetzy/CORE_RULES.md` (L1, ~120 baris, master rules)
3. `~/.xninetzy/CLI_SHARED_INSTRUCTIONS.md` (continuity)
If any fails to resolve, STOP and report the missing file — no degraded fallback.
## Workspace Delegation
If working in `/home/misbahul45/code/xninetzy/`, ALSO read `/home/misbahul45/code/xninetzy/CLAUDE.md`. For other workspaces, prefer workspace-level `CLAUDE.md` if present.
## Permission Map (Claude Code-native)
- `xninetzy_*` → allow
- `xninetzy_*delete*`, `*send*`, `*submit*`, `*commit*`, `*upload*`, `*enroll*`, `*update_record*`, `*finalize*` → ask
- `git push*`, `rm -rf*` → deny
- `playwright_*`, `github_*` → ask (per Claude Code default)
- `sequentialthinking`, `sequential*`, `codebase-memory-mcp_*`, `context7_*`, `paper_research_*`, `web_search_*`, `youtube_search_*`, `markitdown_*`, `document_generator_*`, `powerpoint_*` → allow
## Slash Aliases
`xn-resume`→`/resume`; `xn-research`→`xninetzy-deep-research`; `xn-assignment`→`hebat-assignment`; `xn-learn`→`it-learning`; `xn-doc`→`docx`; `xn-ppt`→`pptx`; `xn-hebat`→`xninetzy-hebat`; `xn-cyber`→`cyber-campus`; `xn-krs`→`xninetzy-krs`; `xn-verify`→`submission-readiness`.
## Format Quirks
GitHub-flavored Markdown; fenced code blocks with language identifiers; prefer tool calls (`Read`, `Edit`, `Bash`) over inline dumps for large content; prefer absolute paths.
## Model Notes
Reasoning: prefer `opus[1m]` with `xhigh` effort per `~/.claude/settings.json` `modelSettings.claude-opus-5-5.effortLevel`. Routing-first calls: no special model requirement.
