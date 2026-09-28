#!/usr/bin/env bash
# verify_prompt_injection.sh — Tiered Prompt Architecture integrity check
# Part of Sub-A: CLI prompt injection design (2026-09-28).

set -uo pipefail

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

ok() { echo "[PASS   ] $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "[FAIL   ] $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn() { echo "[WARN   ] $1"; WARN_COUNT=$((WARN_COUNT + 1)); }

echo "=== L0: HOT PROMPT (~/.xninetzy/CORE_PROMPT.md) ==="

if [ -f ~/.xninetzy/CORE_PROMPT.md ]; then
  ok "L0 file exists"
  LINES=$(wc -l < ~/.xninetzy/CORE_PROMPT.md)
  if [ "$LINES" -le 50 ]; then
    ok "L0 is $LINES lines (≤50 target)"
  elif [ "$LINES" -le 60 ]; then
    warn "L0 is $LINES lines (≤60 hard limit, but >50 target)"
  else
    fail "L0 is $LINES lines (must be ≤60)"
  fi

  if head -20 ~/.xninetzy/CORE_PROMPT.md | grep -q "ROUTING-FIRST"; then
    ok "ROUTING-FIRST directive in first 20 lines"
  else
    fail "ROUTING-FIRST NOT in first 20 lines"
  fi

  if grep -q "^# #1 ROUTING-FIRST" ~/.xninetzy/CORE_PROMPT.md; then
    ok "Section #1 is ROUTING-FIRST"
  else
    fail "Section #1 is not ROUTING-FIRST"
  fi

  for SECTION in "Identity Lock" "REASONING ENGINE" "WORKFLOW LOCK" "MCP TOOLS PRIORITY" "SKILL LOADING"; do
    if grep -q "$SECTION" ~/.xninetzy/CORE_PROMPT.md; then
      ok "L0 contains section: $SECTION"
    else
      fail "L0 missing section: $SECTION"
    fi
  done
else
  fail "L0 file missing: ~/.xninetzy/CORE_PROMPT.md"
fi

echo ""
echo "=== L1: MASTER RULES (~/.xninetzy/CORE_RULES.md) ==="

if [ -f ~/.xninetzy/CORE_RULES.md ]; then
  ok "L1 file exists"
  LINES=$(wc -l < ~/.xninetzy/CORE_RULES.md)
  if [ "$LINES" -ge 100 ] && [ "$LINES" -le 200 ]; then
    ok "L1 is $LINES lines (100-200 target)"
  else
    fail "L1 is $LINES lines (target 100-200)"
  fi

  for SECTION in "FORBIDDEN BEHAVIORS" "REQUIRED BEHAVIORS" "MEMORY & WORKFLOW" "SLASH COMMAND" "PERMISSION CONTEXT"; do
    if grep -q "$SECTION" ~/.xninetzy/CORE_RULES.md; then
      ok "L1 contains section: $SECTION"
    else
      fail "L1 missing section: $SECTION"
    fi
  done
else
  fail "L1 file missing: ~/.xninetzy/CORE_RULES.md"
fi

echo ""
echo "=== L2: CLI OVERRIDES ==="

check_l2() {
  local label="$1"
  local path="$2"
  if [ -f "$path" ]; then
    ok "L2 exists: $label ($path)"
    LINES=$(wc -l < "$path")
    if [ "$LINES" -le 40 ]; then
      ok "L2 $label is $LINES lines (≤40)"
    else
      fail "L2 $label is $LINES lines (must be ≤40)"
    fi
    if grep -q "CORE_PROMPT.md" "$path"; then
      ok "L2 $label references L0"
    else
      fail "L2 $label does NOT reference L0"
    fi
    if grep -q "CORE_RULES.md" "$path"; then
      ok "L2 $label references L1"
    else
      fail "L2 $label does NOT reference L1"
    fi
  else
    warn "L2 missing: $label ($path) — non-fatal"
  fi
}

check_l2 "OpenCode" ~/.config/opencode/instructions/xninetzy-paksa.md
check_l2 "Claude Code" ~/.claude/CLAUDE.md
check_l2 "Codex" ~/.codex/AGENTS.md
if [ -d ~/.arkcli ] || [ -d ~/.config/arkcli ]; then
  ARKCLI_DIR=~/.arkcli/config
  [ -d ~/.config/arkcli/config ] && ARKCLI_DIR=~/.config/arkcli/config
  check_l2 "arkcli" "$ARKCLI_DIR/AGENTS.md"
else
  warn "arkcli not installed; L2 override skipped (expected)"
fi

echo ""
echo "=== Cross-CLI Reference Integrity ==="

# All L2 files must reference L0 + L1 (already checked above)
# L1 must reference L0
if [ -f ~/.xninetzy/CORE_RULES.md ] && grep -q "CORE_PROMPT.md" ~/.xninetzy/CORE_RULES.md; then
  ok "L1 references L0"
else
  warn "L1 does not reference L0 (acceptable but recommended)"
fi

echo ""
echo "=== SUMMARY ==="
echo "PASS: $PASS_COUNT | FAIL: $FAIL_COUNT | WARN: $WARN_COUNT"

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo "OVERALL: FAIL"
  exit 1
fi

if [ "$WARN_COUNT" -gt 0 ]; then
  echo "OVERALL: PASS WITH WARNINGS"
  exit 0
fi

echo "OVERALL: PASS"
exit 0