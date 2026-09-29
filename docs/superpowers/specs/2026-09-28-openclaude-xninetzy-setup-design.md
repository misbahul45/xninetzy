# OpenClaude Setup with MiniMax Provider + MCPs + Prompts

**Date:** 2026-09-28
**Status:** Proposed → Pending user review
**Scope:** Local OpenClaude CLI v0.27.0 configuration at `/home/misbahul45/.openclaude/`

## 1. Objective

Replicate the host-agent setup (MiniMax token plan via `minimax.io`, MCP systems, prompts) inside OpenClaude so the user can run an equivalent session through OpenClaude's CLI.

## 2. Current State (Verified)

| Component | Current | Location |
|---|---|---|
| OpenClaude CLI | v0.27.0 (`@gitlawb/openclaude`) | `/home/misbahul45/.local/bin/openclaude` |
| Active provider | Moonshot AI via TokenRouter (kimi-k3-free) | `~/.config/tokenrouter/openclaude.env` |
| Persistent profile (fallback) | Custom OpenAI-compatible (agentrouter.org / claude-opus-4-6) | `~/.openclaude.json` |
| MCP servers | **None configured** in OpenClaude | — |
| Plugins | `superpowers@claude-plugins-official` (enabled) | `~/.openclaude/plugins/` |
| Skills | 100+ already loaded (incl. superpowers) | `~/.openclaude/skills/` |
| `CLAUDE.md` | 29KB xninetzy-themed already exists | `~/.openclaude/CLAUDE.md` |
| Source for prompts to inject | `~/.config/opencode/AGENTS.md` (32KB) | host OpenCode config |

OpenCode (host) currently has **9 MCPs connected**: `xninetzy`, `codebase-memory-mcp`, `paper_research`, `sequential-thinking`, `web_search`, `youtube_search`, `context7`, `playwright`, `markitdown` (failing/timeout — skip).

## 3. Design (4 phases)

### Phase A — Remove Moonshot / Kimi-K3 provider env

**Action:** Delete `/home/misbahul45/.config/tokenrouter/openclaude.env` (4 env vars that override the persistent profile and show the "Moonshot AI — moonshotai/kimi-k3-free" banner).

**Effect:** OpenClaude falls back to the persistent `provider_fcd2e2fc4440` (agentrouter.org / claude-opus-4-6) until MiniMax entry is added.

**Backup:** `cp openclaude.env openclaude.env.bak.20260928-*` before deletion.

### Phase B — Add MiniMax as primary provider

**Action:** Append a new entry to `~/.openclaude.json` → `providerProfiles` array:

```json
{
  "id": "provider_minimax_<auto>",
  "name": "MiniMax (minimax.io)",
  "provider": "custom",
  "baseUrl": "https://api.minimax.io/v1",
  "model": "MiniMax-M3",
  "apiFormat": "chat_completions",
  "authHeader": "<TO_BE_PASTED_BY_USER>",
  "authScheme": "raw"
}
```

**Status:** **Credentials received from owner** (2026-09-28 in chat — never echo in plain text again, only reference as `<REDACTED>`).

Confirmed values:
- `baseUrl`: `https://api.minimax.io/v1` (per user)
- `model`: `MiniMax-M3` (per system prompt + user)
- `authHeader`: `<REDACTED — see /home/misbahul45/.openclaude.json>` (raw API key)
- `apiFormat`: `chat_completions`

After write, set `activeProviderProfileId` to the new entry id.

**Important:** the key has been pasted in chat history. Recommend owner rotates it after this setup if it was meant to be private. The key is stored only in `~/.openclaude.json` (file mode 0600 assumed) and never logged or referenced in plain text by the agent.

### Phase C — Add 9 MCP servers to OpenClaude

**Action:** Run `openclaude mcp add` for each server currently in `opencode mcp list`. Use `--scope user` (global). Skipping `markitdown` (timeout).

| Server | Command |
|---|---|
| `xninetzy` | `/home/misbahul45/.local/bin/uv run --directory /home/misbahul45/code/xninetzy python -m xninetzy.interfaces.mcp_server` |
| `codebase-memory-mcp` | `/home/misbahul45/.local/bin/codebase-memory-mcp` |
| `paper_research` | `uvx --with mcp<2 paper-search-mcp` |
| `sequential-thinking` | `npx -y @modelcontextprotocol/server-sequential-thinking` |
| `web_search` | `npx -y open-websearch@latest` |
| `youtube_search` | `npx -y @kevinwatt/yt-dlp-mcp@latest` |
| `context7` | `https://mcp.context7.com/mcp` (HTTP) |
| `playwright` | `npx -y @playwright/mcp@latest` |

**Verification:** `openclaude mcp list` after — expect 8 connected, 0 failed.

### Phase D — Inject prompts

**Action:** Append (not replace) the OpenCode system-prompt content into `~/.openclaude/CLAUDE.md`:

1. `~/.config/opencode/AGENTS.md` (32KB) — full text appended at the end
2. `~/.config/opencode/AGENTS.md.orig` (10KB) — original ASCII-art version
3. Project-level `AGENTS.md` snippets (xninetzy repo root)

**Why append not replace:** OpenClaude already has a 29KB xninetzy-themed `CLAUDE.md` (user's existing work — preserve it). We are adding the host-level orchestration layer on top.

**Backup:** `cp ~/.openclaude/CLAUDE.md ~/.openclaude/CLAUDE.md.bak.20260928-*` before edit.

## 4. Components & Data Flow

```
┌────────────────────────────────────────────────────┐
│ User runs: openclaude (or openclaude -p "...")     │
└────────────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│ Provider resolution:                               │
│   1. TokenRouter env (DELETED in Phase A)          │
│   2. activeProviderProfileId → MiniMax entry       │
│      (if user pastes key)                          │
│   3. Fallback: agentrouter.org claude-opus-4-6     │
└────────────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│ System prompt assembly:                            │
│   ~/.openclaude/CLAUDE.md (29KB existing)          │
│   + ~/.config/opencode/AGENTS.md (32KB injected)   │
│   + skills/ (100+ loaded)                          │
│   + plugin: superpowers@claude-plugins-official    │
└────────────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│ MCP servers (8 connected, post-Phase C):           │
│   xninetzy, codebase-memory, paper_research,       │
│   sequential-thinking, web_search, youtube_search, │
│   context7, playwright                             │
└────────────────────────────────────────────────────┘
```

## 5. Error Handling

- **Phase A:** If `openclaude.env` deletion breaks the session, restore from `.bak.*` and stop.
- **Phase B:** Until user pastes MiniMax credentials, OpenClaude runs on the existing `provider_fcd2e2fc4440` (agentrouter.org / claude-opus-4-6). No silent degradation.
- **Phase C:** If `openclaude mcp add` fails for any server, capture the error per-server and continue. Final `openclaude mcp list` reports success/failure per server.
- **Phase D:** If `CLAUDE.md` write fails, abort and restore from `.bak.*`.

## 6. Testing / Verification

1. `openclaude mcp list` → 8 connected, 0 failed (or documented failures)
2. `cat ~/.config/tokenrouter/openclaude.env 2>/dev/null || echo "deleted (expected)"`
3. `openclaude --version` → still 0.27.0
4. After MiniMax credentials pasted: launch `openclaude --model MiniMax-M3` and confirm banner shows MiniMax provider
5. Smoke test: `openclaude -p "list your MCP servers"` → returns the 8 servers

## 7. Out of Scope

- MiniMax credentials (waiting on user paste)
- Modifying OpenCode's own `~/.config/opencode/opencode.jsonc`
- Changing OpenClaude's plugin set (superpowers already enabled)
- Touching the xninetzy MCP server itself
- Adding `markitdown` (currently failing in host — skip until fixed upstream)

## 8. Risks

| Risk | Mitigation |
|---|---|
| User pastes key in public chat | Recommend they paste via terminal, not chat. Log only key fingerprint, never the full key. |
| AGENTS.md inject makes CLAUDE.md too large (>100KB) | Verify size after; if too large, summarize key sections instead of full append. |
| MCP stdio servers have permission issues | Use `--scope user`; do not use `--dangerously-skip-permissions`. |
| Backups accumulate | Single timestamped `.bak.*` per file, not multiple. |