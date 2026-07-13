#!/usr/bin/env bash
# Test harness for the statusline plugin. Run: bash scripts/test.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  ok   - %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL - %s\n' "$1"; }
assert_contains() { case "$2" in *"$1"*) ok "$3" ;; *) bad "$3 (missing: $1)"; printf '      got: %s\n' "$2" ;; esac; }
assert_equals()   { if [ "$1" = "$2" ]; then ok "$3"; else bad "$3 (want '$1' got '$2')"; fi; }

REND="$ROOT/scripts/statusline.sh"

FULL='{"cwd":"'"$HOME"'/proj","model":{"display_name":"Opus 4.8"},"context_window":{"used_percentage":42},"rate_limits":{"five_hour":{"used_percentage":30,"resets_at":0}},"effort":{"level":"high"}}'

echo "== renderer =="
out=$(printf '%s' "$FULL" | STATUSLINE_ICONS=nerd sh "$REND")
assert_contains "~/proj" "$out" "full: cwd shown with ~"
assert_contains "Opus 4.8" "$out" "full: model shown"
assert_contains "42%" "$out" "full: context percent shown"
assert_contains "5h 30%" "$out" "full: rate-limit percent shown"
assert_contains "high" "$out" "full: effort shown"

NOGIT='{"cwd":"/tmp/nowhere-xyz","model":{"display_name":"Haiku"}}'
out=$(printf '%s' "$NOGIT" | STATUSLINE_ICONS=nerd sh "$REND")
assert_contains "Haiku" "$out" "no-git: model still shown"

out=$(printf '%s' "$FULL" | STATUSLINE_ICONS=ascii sh "$REND")
assert_contains "ctx" "$out" "ascii: context label"

# Branch label only renders inside a real git repo, so use the repo root as cwd.
GITFIX='{"cwd":"'"$ROOT"'","model":{"display_name":"Opus 4.8"}}'
out=$(printf '%s' "$GITFIX" | STATUSLINE_ICONS=ascii sh "$REND")
assert_contains "git" "$out" "ascii: branch label"

out=$(PATH= /bin/sh "$REND" </dev/null)
assert_contains "jq not found" "$out" "no-jq: prints hint"

echo
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
