#!/usr/bin/env bash
# Tests for session_context.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/session_context.sh"
fail=0
assert(){ if [ "$2" -ne 0 ]; then echo "FAIL: $1"; fail=1; else echo "ok: $1"; fi; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export CLAUDE_CONFIG_DIR="$TMP/config"
mkdir -p "$CLAUDE_CONFIG_DIR"

# --- Case 1: no wiki linked -> silent no-op ---
out="$(bash "$SCRIPT")"; rc=$?
[ "$rc" -eq 0 ]; assert "exit 0 when unlinked" $?
[ -z "$out" ]; assert "no stdout when unlinked" $?

# --- Case 2: linked wiki with index -> JSON context ---
WIKIREPO="$TMP/mywiki"; mkdir -p "$WIKIREPO"
printf '# Wiki Index\n\n## Concepts\n- [Foo](concepts/foo.md) — bar\n' > "$WIKIREPO/index.md"
ln -s "$WIKIREPO" "$CLAUDE_CONFIG_DIR/wiki"
out="$(bash "$SCRIPT")"; rc=$?
[ "$rc" -eq 0 ]; assert "exit 0 when linked" $?
printf '%s' "$out" | jq -e '.hookSpecificOutput.hookEventName=="SessionStart"' >/dev/null 2>&1; assert "hookEventName set" $?
printf '%s' "$out" | jq -e '.hookSpecificOutput.additionalContext | contains("Wiki Index")' >/dev/null 2>&1; assert "index content included" $?
printf '%s' "$out" | jq -e '.hookSpecificOutput.additionalContext | contains("must live")' >/dev/null 2>&1; assert "reminder included" $?

# --- Case 3: symlink present but index missing -> silent ---
rm "$CLAUDE_CONFIG_DIR/wiki"; EMPTY="$TMP/empty"; mkdir -p "$EMPTY"
ln -s "$EMPTY" "$CLAUDE_CONFIG_DIR/wiki"
out="$(bash "$SCRIPT")"; rc=$?
[ "$rc" -eq 0 ] && [ -z "$out" ]; assert "silent when index.md missing" $?

[ "$fail" -eq 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
