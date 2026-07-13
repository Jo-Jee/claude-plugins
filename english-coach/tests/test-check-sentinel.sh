#!/usr/bin/env bash
# Tests for the sentinel guard in check.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/check.sh"
fail=0
assert() { if [ "$2" -ne 0 ]; then echo "FAIL: $1"; fail=1; else echo "ok: $1"; fi; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Stub `claude` so the non-paused path returns quickly with "OK".
STUB="$TMP/claude"
printf '#!/usr/bin/env bash\necho OK\n' > "$STUB"
chmod +x "$STUB"

export CHECK_ENGLISH_CLAUDE_BIN="$STUB"
export CHECK_ENGLISH_MISTAKE_LOG="$TMP/mistakes.jsonl"
export CHECK_ENGLISH_LOG="$TMP/debug.log"
export CHECK_ENGLISH_SENTINEL="$TMP/.session-active"

PROMPT_JSON='{"prompt":"i has a apple"}'

# --- Case 1: fresh sentinel -> silent, sentinel preserved ---
date +%s > "$CHECK_ENGLISH_SENTINEL"
out="$(printf '%s' "$PROMPT_JSON" | bash "$SCRIPT")"
[ -z "$out" ]; assert "fresh sentinel -> no output" $?
[ -f "$CHECK_ENGLISH_SENTINEL" ]; assert "fresh sentinel preserved" $?

# --- Case 2: stale sentinel (>2h) -> proceeds, sentinel removed ---
echo $(( $(date +%s) - 8000 )) > "$CHECK_ENGLISH_SENTINEL"
out="$(printf '%s' "$PROMPT_JSON" | bash "$SCRIPT")"
[ -n "$out" ]; assert "stale sentinel -> produces output" $?
[ ! -f "$CHECK_ENGLISH_SENTINEL" ]; assert "stale sentinel removed" $?

# --- Case 3: no sentinel -> normal behavior ---
rm -f "$CHECK_ENGLISH_SENTINEL"
out="$(printf '%s' "$PROMPT_JSON" | bash "$SCRIPT")"
[ -n "$out" ]; assert "no sentinel -> produces output" $?

[ "$fail" -eq 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
