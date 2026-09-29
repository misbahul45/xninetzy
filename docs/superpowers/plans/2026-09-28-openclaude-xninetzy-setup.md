# OpenClaude xninetzy Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure OpenClaude CLI to use MiniMax as primary provider with all 8 host MCPs and the host AGENTS.md prompt injected, while removing the Moonshot/Kimi-K3 override.

**Architecture:** Pure local config edits — no code changes. Backup each file with timestamped `.bak.*` before edit, then write new content, then verify with CLI commands.

**Tech Stack:** OpenClaude v0.27.0 (`@gitlawb/openclaude`), JSON config at `~/.openclaude.json`, env file at `~/.config/tokenrouter/openclaude.env`, Markdown at `~/.openclaude/CLAUDE.md`.

## Global Constraints

- **Never echo the MiniMax API key in chat output** — refer to it as `<REDACTED>` or "the MiniMax key"
- **All file edits are local config** — no project source code is modified
- **Backups are timestamped** with format `.bak.20260928-*` (single backup per file, not multiple)
- **MCP servers are added with `--scope user`** (global, not project)
- **Markitdown MCP is skipped** (currently fails/timeout in host OpenCode)
- **Spec:** `/home/misbahul45/code/xninetzy/docs/superpowers/specs/2026-09-28-openclaude-xninetzy-setup-design.md`

---

## Task 1: Backup critical config files

**Files:**
- Read: `~/.config/tokenrouter/openclaude.env`
- Read: `~/.openclaude.json`
- Read: `~/.openclaude/CLAUDE.md`

**Interfaces:**
- Produces: 3 timestamped backup files for rollback

- [ ] **Step 1: Create timestamped backups**

```bash
TS=$(date +%Y%m%d-%H%M%S)
cp /home/misbahul45/.config/tokenrouter/openclaude.env \
   /home/misbahul45/.config/tokenrouter/openclaude.env.bak.${TS}
cp /home/misbahul45/.openclaude.json \
   /home/misbahul45/.openclaude.json.bak.${TS}
cp /home/misbahul45/.openclaude/CLAUDE.md \
   /home/misbahul45/.openclaude/CLAUDE.md.bak.${TS}
echo "TS=${TS}" > /tmp/openclaude_setup_ts
```

- [ ] **Step 2: Verify backups exist and match originals**

```bash
TS=$(cat /tmp/openclaude_setup_ts | cut -d= -f2)
diff /home/misbahul45/.config/tokenrouter/openclaude.env \
     /home/misbahul45/.config/tokenrouter/openclaude.env.bak.${TS} \
     && echo "env backup OK"
diff /home/misbahul45/.openclaude.json \
     /home/misbahul45/.openclaude.json.bak.${TS} \
     && echo "openclaude.json backup OK"
diff /home/misbahul45/.openclaude/CLAUDE.md \
     /home/misbahul45/.openclaude/CLAUDE.md.bak.${TS} \
     && echo "CLAUDE.md backup OK"
```

Expected: 3 "backup OK" lines.

- [ ] **Step 3: Commit (no git tracking for these paths; backup itself is the audit trail)**

No commit. Just record `$TS` for rollback steps later.

---

## Task 2: Remove Moonshot / Kimi-K3 env override

**Files:**
- Modify: `/home/misbahul45/.config/tokenrouter/openclaude.env` (delete or empty)

**Interfaces:**
- Consumes: backup from Task 1
- Produces: OpenClaude falls back to persistent provider profile

- [ ] **Step 1: Delete the env file**

```bash
rm /home/misbahul45/.config/tokenrouter/openclaude.env
```

- [ ] **Step 2: Verify removal**

```bash
test ! -f /home/misbahul45/.config/tokenrouter/openclaude.env \
  && echo "env file removed (expected)"
```

Expected: prints "env file removed (expected)".

- [ ] **Step 3: Smoke test — launch OpenClaude and check banner**

```bash
timeout 10 openclaude --print "exit immediately" 2>&1 | head -15
```

Expected: banner no longer shows "Moonshot AI — moonshotai/kimi-k3-free". May show "Custom OpenAI-compatible — claude-opus-4-6" (the persistent fallback) or whatever the active profile says.

- [ ] **Step 4: Rollback ready**

If smoke test shows unexpected output, restore:

```bash
TS=$(cat /tmp/openclaude_setup_ts | cut -d= -f2)
cp /home/misbahul45/.config/tokenrouter/openclaude.env.bak.${TS} \
   /home/misbahul45/.config/tokenrouter/openclaude.env
```

---

## Task 3: Add MiniMax provider entry

**Files:**
- Modify: `/home/misbahul45/.openclaude.json`

**Interfaces:**
- Consumes: the MiniMax API key (provided in chat 2026-09-28, never echoed again)
- Produces: new entry in `providerProfiles` array, `activeProviderProfileId` updated

- [ ] **Step 1: Verify the file is valid JSON before edit**

```bash
python3 -c "import json; json.load(open('/home/misbahul45/.openclaude.json'))" \
  && echo "valid JSON"
```

Expected: "valid JSON".

- [ ] **Step 2: Build the new provider entry via Python (avoids manual JSON editing)**

The MiniMax API key was provided by the owner in chat on 2026-09-28. The executor reads it from chat context (not from this file) and substitutes it into the `KEY` variable. The key is **never** written to the plan file, log files, or echoed in any output.

```python
import json
from pathlib import Path
import secrets

# Executor: substitute the literal string from the owner's 2026-09-28 chat
# message — the value starting with "sk-api-" and matching the format shown
# in chat. Do NOT print this variable. Do NOT log it.
KEY = "<REDACTED — from chat 2026-09-28>"

BASE = "/home/misbahul45/.openclaude.json"
data = json.loads(Path(BASE).read_text())
new_id = "provider_minimax_" + secrets.token_hex(6)
entry = {
    "id": new_id,
    "name": "MiniMax (minimax.io)",
    "provider": "custom",
    "baseUrl": "https://api.minimax.io/v1",
    "model": "MiniMax-M3",
    "apiFormat": "chat_completions",
    "authHeader": KEY,
    "authScheme": "raw",
}
data["providerProfiles"].append(entry)
data["openaiAdditionalModelOptionsCacheByProfile"][new_id] = [
    {"value": "MiniMax-M3", "label": "MiniMax-M3", "description": "Provider: MiniMax (minimax.io)"}
]
data["openaiAdditionalModelOptionsCache"] = [
    {"value": "MiniMax-M3", "label": "MiniMax-M3", "description": "Provider: MiniMax (minimax.io)"}
]
data["activeProviderProfileId"] = new_id
Path(BASE).write_text(json.dumps(data, indent=2))
# Confirm by id only — never print key or full entry
print("NEW_ID=" + new_id)
```

Executor instruction: replace `KEY = "<REDACTED ...>"` with the actual value from chat. The script only prints `NEW_ID=...`.

- [ ] **Step 3: Verify the new entry was written and is active**

```bash
python3 -c "
import json
d = json.load(open('/home/misbahul45/.openclaude.json'))
active = d['activeProviderProfileId']
match = [p for p in d['providerProfiles'] if p['id'] == active]
assert len(match) == 1, 'active profile not found'
p = match[0]
assert p['name'].startswith('MiniMax'), 'wrong active provider: ' + p['name']
assert p['model'] == 'MiniMax-M3', 'wrong model'
assert 'minimax.io' in p['baseUrl'], 'wrong baseUrl'
print('active provider OK; id=', active[:24] + '...')  # truncate id in logs
"
```

Expected: prints "active provider OK; id=provider_minimax_xxxxxx..." (id truncated).

- [ ] **Step 4: Smoke test — launch OpenClaude with MiniMax-M3**

```bash
timeout 15 openclaude --model MiniMax-M3 --print "exit immediately" 2>&1 | head -15
```

Expected: banner shows "MiniMax" provider and model "MiniMax-M3". If it shows "auth failed" or "401", the key is invalid — restore from Task 1 backup and stop.

- [ ] **Step 5: Rollback ready**

If smoke test fails on auth, restore `~/.openclaude.json` from backup:

```bash
TS=$(cat /tmp/openclaude_setup_ts | cut -d= -f2)
cp /home/misbahul45/.openclaude.json.bak.${TS} \
   /home/misbahul45/.openclaude.json
echo "rolled back openclaude.json"
```

---

## Task 4: Add 8 MCP servers to OpenClaude

**Files:**
- Modify: `~/.openclaude.json` → `mcpServers` (per user scope)

**Interfaces:**
- Consumes: command/transport for each server (from host OpenCode config)
- Produces: 8 MCP entries registered globally

- [ ] **Step 1: Add xninetzy MCP**

```bash
openclaude mcp add --scope user xninetzy -- \
  /home/misbahul45/.local/bin/uv run \
  --directory /home/misbahul45/code/xninetzy \
  python -m xninetzy.interfaces.mcp_server
```

- [ ] **Step 2: Add codebase-memory-mcp**

```bash
openclaude mcp add --scope user codebase-memory-mcp -- \
  /home/misbahul45/.local/bin/codebase-memory-mcp
```

- [ ] **Step 3: Add paper_research**

```bash
openclaude mcp add --scope user paper_research -- \
  uvx --with "mcp<2" paper-search-mcp
```

- [ ] **Step 4: Add sequential-thinking**

```bash
openclaude mcp add --scope user sequential-thinking -- \
  npx -y @modelcontextprotocol/server-sequential-thinking
```

- [ ] **Step 5: Add web_search**

```bash
openclaude mcp add --scope user web_search -- \
  npx -y open-websearch@latest
```

- [ ] **Step 6: Add youtube_search**

```bash
openclaude mcp add --scope user youtube_search -- \
  npx -y @kevinwatt/yt-dlp-mcp@latest
```

- [ ] **Step 7: Add context7 (HTTP transport)**

```bash
openclaude mcp add --transport http --scope user context7 \
  https://mcp.context7.com/mcp
```

- [ ] **Step 8: Add playwright**

```bash
openclaude mcp add --scope user playwright -- \
  npx -y @playwright/mcp@latest
```

- [ ] **Step 9: Verify all 8 are connected**

```bash
openclaude mcp list
```

Expected: 8 servers listed with `connected` status. `markitdown` is intentionally skipped.

- [ ] **Step 10: Rollback ready**

To remove a single failed MCP:

```bash
openclaude mcp remove <name>
```

To wipe ALL OpenClaude MCPs (project + user scope) and reset:

```bash
# Inspect storage paths used by OpenClaude
openclaude mcp list 2>&1 | grep -E "\.json|Config"
# Typical locations:
#   ~/.openclaude/mcp-servers.json   (user scope, file-based)
#   ~/.openclaude.json              (user scope, embedded)
#   <project>/.mcp.json             (project scope)
# To wipe user-scope MCPs only:
rm -f /home/misbahul45/.openclaude/mcp-servers.json
# Then verify
openclaude mcp list
# Expected: "No MCP servers configured" or only project-scope entries
```

---

## Task 5: Inject prompts into CLAUDE.md

**Files:**
- Read: `/home/misbahul45/.config/opencode/AGENTS.md` (32KB)
- Modify: `/home/misbahul45/.openclaude/CLAUDE.md` (append, do not replace)

**Interfaces:**
- Produces: extended CLAUDE.md with host orchestration layer

- [ ] **Step 1: Check current CLAUDE.md size and capture marker**

```bash
wc -l /home/misbahul45/.openclaude/CLAUDE.md
echo "---"
grep -n "<!-- BEGIN HOST OPENCODE AGENTS.md -->" /home/misbahul45/.openclaude/CLAUDE.md \
  || echo "marker not yet present (expected)"
```

Expected: line count for existing 29KB file (~600 lines). Marker not yet present.

- [ ] **Step 2: Append AGENTS.md content with delimiter**

```bash
{
  echo ""
  echo "<!-- BEGIN HOST OPENCODE AGENTS.md -->"
  echo "<!-- Injected 2026-09-28 from /home/misbahul45/.config/opencode/AGENTS.md -->"
  echo "<!-- Source: host OpenCode orchestration layer (32KB). Do not edit here; -->"
  echo "<!-- edit the host AGENTS.md and re-run the injection script instead. -->"
  echo ""
  cat /home/misbahul45/.config/opencode/AGENTS.md
  echo ""
  echo "<!-- END HOST OPENCODE AGENTS.md -->"
} >> /home/misbahul45/.openclaude/CLAUDE.md
```

- [ ] **Step 3: Verify size and marker**

```bash
wc -l /home/misbahul45/.openclaude/CLAUDE.md
echo "---"
grep -c "<!-- BEGIN HOST OPENCODE AGENTS.md -->" \
  /home/misbahul45/.openclaude/CLAUDE.md
grep -c "<!-- END HOST OPENCODE AGENTS.md -->" \
  /home/misbahul45/.openclaude/CLAUDE.md
```

Expected: line count roughly = original + AGENTS.md lines (~600 + ~700 ≈ 1300 lines). Both markers present exactly once.

- [ ] **Step 4: If CLAUDE.md > 100KB, fall back to summary mode**

```bash
SIZE=$(wc -c < /home/misbahul45/.openclaude/CLAUDE.md)
if [ "$SIZE" -gt 102400 ]; then
  TS=$(cat /tmp/openclaude_setup_ts | cut -d= -f2)
  echo "CLAUDE.md is $SIZE bytes (>100KB) — restoring backup and using summary mode"
  cp /home/misbahul45/.openclaude/CLAUDE.md.bak.${TS} \
     /home/misbahul45/.openclaude/CLAUDE.md
  echo "" >> /home/misbahul45/.openclaude/CLAUDE.md
  echo "<!-- BEGIN HOST OPENCODE AGENTS.md (SUMMARY) -->" >> /home/misbahul45/.openclaude/CLAUDE.md
  # Summary: keep only section headings + first paragraph of each section
  awk '/^#+ /{h=$0; print "\n## " h; next} {if(h) print}' \
    /home/misbahul45/.config/opencode/AGENTS.md \
    | head -200 \
    >> /home/misbahul45/.openclaude/CLAUDE.md
  echo "<!-- END HOST OPENCODE AGENTS.md (SUMMARY) -->" >> /home/misbahul45/.openclaude/CLAUDE.md
fi
```

Expected: either skipped (file is OK size) or replaced with a summary block.

- [ ] **Step 5: Smoke test — launch OpenClaude and check it loads prompts**

```bash
timeout 15 openclaude --print "echo the first system directive you see" 2>&1 | head -30
```

Expected: response references either the original xninetzy CLAUDE.md content or the new AGENTS.md orchestration layer (or both).

- [ ] **Step 6: Rollback ready**

```bash
TS=$(cat /tmp/openclaude_setup_ts | cut -d= -f2)
cp /home/misbahul45/.openclaude/CLAUDE.md.bak.${TS} \
   /home/misbahul45/.openclaude/CLAUDE.md
echo "rolled back CLAUDE.md"
```

---

## Task 6: Final verification + report

**Files:**
- Read: `/home/misbahul45/.openclaude.json` (verify active provider)
- Read: `~/.openclaude.json mcpServers` (verify 8 entries)

- [ ] **Step 1: Active provider + MCP count summary**

```bash
echo "=== Active provider ==="
python3 -c "
import json
d = json.load(open('/home/misbahul45/.openclaude.json'))
for p in d['providerProfiles']:
    if p['id'] == d['activeProviderProfileId']:
        print('  name:', p['name'])
        print('  model:', p['model'])
        print('  baseUrl:', p['baseUrl'])
        print('  authHeader: <REDACTED>')
"
echo ""
echo "=== MCP servers ==="
openclaude mcp list
echo ""
echo "=== Moonshot env override ==="
test -f /home/misbahul45/.config/tokenrouter/openclaude.env \
  && echo "  STILL PRESENT (unexpected)" \
  || echo "  removed (expected)"
echo ""
echo "=== CLAUDE.md size ==="
wc -lc /home/misbahul45/.openclaude/CLAUDE.md
```

- [ ] **Step 2: Inform user + recommend key rotation**

Final reply must:
- Confirm 4 phases completed
- Remind user to rotate the MiniMax API key (it was exposed in chat history)
- Note backup locations for rollback

**End of plan.**