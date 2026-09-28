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
