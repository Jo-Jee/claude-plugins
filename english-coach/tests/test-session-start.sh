#!/usr/bin/env bash
# Tests for session-start.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/session-start.sh"
fail=0
assert() { # desc, condition already evaluated -> $1 desc, $2 = 0/1 result
  if [ "$2" -ne 0 ]; then echo "FAIL: $1"; fail=1; else echo "ok: $1"; fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export CHECK_ENGLISH_SENTINEL="$TMP/ec/.session-active"
export CHECK_ENGLISH_PROFILE="$TMP/ec/profile.md"
export CHECK_ENGLISH_SESSIONS="$TMP/ec/sessions.jsonl"
export CHECK_ENGLISH_MISTAKE_LOG="$TMP/mistakes.jsonl"

# --- Case 1: first run, no memory files exist ---
out="$(bash "$SCRIPT")"
[ -f "$CHECK_ENGLISH_SENTINEL" ]; assert "sentinel created" $?
grep -Eq '^[0-9]+$' "$CHECK_ENGLISH_SENTINEL"; assert "sentinel holds epoch seconds" $?
printf '%s' "$out" | grep -q "## Your learner profile"; assert "profile section printed" $?
printf '%s' "$out" | grep -q "## Recent sessions"; assert "sessions section printed" $?
printf '%s' "$out" | grep -q "## Top mistake categories"; assert "mistakes section printed" $?
printf '%s' "$out" | grep -qi "first session"; assert "first-run note shown" $?

# --- Case 2: with memory present ---
mkdir -p "$TMP/ec"
printf 'George is a Korean SWE. Weak on articles.\n' > "$CHECK_ENGLISH_PROFILE"
printf '{"ts":"2026-07-10T00:00:00Z","topics":["weekend"],"summary":"good flow","focus_next":["articles"],"highlights":[]}\n' > "$CHECK_ENGLISH_SESSIONS"
printf '{"ts":"2026-07-10T00:00:00Z","category":"articles","original":"a","corrected":"the","reason":"x","context":"y"}\n' > "$CHECK_ENGLISH_MISTAKE_LOG"
printf '{"ts":"2026-07-10T00:01:00Z","category":"articles","original":"b","corrected":"c","reason":"x","context":"y"}\n' >> "$CHECK_ENGLISH_MISTAKE_LOG"
out="$(bash "$SCRIPT")"
printf '%s' "$out" | grep -q "Korean SWE"; assert "profile contents printed" $?
printf '%s' "$out" | grep -q "good flow"; assert "recent session summary printed" $?
printf '%s' "$out" | grep -Eq "articles.*2|2.*articles"; assert "category count printed" $?

[ "$fail" -eq 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
