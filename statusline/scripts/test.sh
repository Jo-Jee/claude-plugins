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

echo "== lib-settings =="
TMP=$(mktemp -d)
export STATUSLINE_SETTINGS="$TMP/settings.json"
export STATUSLINE_DATA="$TMP/data"
export STATUSLINE_ROOT="/opt/plugins/statusline"
# shellcheck source=/dev/null
. "$ROOT/scripts/lib-settings.sh"

assert_equals 'STATUSLINE_ICONS=nerd "/opt/plugins/statusline/scripts/statusline.sh"' \
  "$(build_command "$(plugin_root)" nerd)" "build_command formats nerd"

write_statusline_command 'CMD_A'
assert_equals "CMD_A" "$(read_statusline_command)" "write/read roundtrip"
assert_equals "command" "$(jq -r '.statusLine.type' "$STATUSLINE_SETTINGS")" "write sets type=command"

owned_write "CMD_A" "ascii"
assert_equals "CMD_A" "$(owned_get_command)" "owned command recorded"
assert_equals "ascii" "$(owned_get_icons)" "owned icons recorded"

backup_settings
remove_statusline
assert_equals "" "$(read_statusline_command)" "remove_statusline clears entry"
restore_settings_backup
assert_equals "CMD_A" "$(read_statusline_command)" "restore brings back entry"

owned_clear
assert_equals "nerd" "$(owned_get_icons)" "owned_get_icons defaults to nerd after clear"
rm -rf "$TMP"
unset STATUSLINE_SETTINGS STATUSLINE_DATA STATUSLINE_ROOT

echo "== sync =="
run_sync() {
  TMP=$(mktemp -d)
  SET="$TMP/settings.json"; DATA="$TMP/data"; NEWROOT="/opt/plugins/statusline-v2"
  NEWCMD='STATUSLINE_ICONS=nerd "/opt/plugins/statusline-v2/scripts/statusline.sh"'
  OLDCMD='STATUSLINE_ICONS=nerd "/opt/plugins/statusline-v1/scripts/statusline.sh"'
}

# Case A: no statusLine present -> stays empty
run_sync
printf '{}\n' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$NEWROOT" bash "$ROOT/scripts/sync.sh"
assert_equals "" "$(jq -r '.statusLine.command // empty' "$SET")" "sync: empty stays empty"
rm -rf "$TMP"

# Case B: ours but stale path -> re-pinned to new root
run_sync
mkdir -p "$DATA"
jq -n --arg c "$OLDCMD" '{statusLine:{type:"command",command:$c}}' > "$SET"
jq -n --arg c "$OLDCMD" '{command:$c, icons:"nerd"}' > "$DATA/owned.json"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$NEWROOT" bash "$ROOT/scripts/sync.sh"
assert_equals "$NEWCMD" "$(jq -r '.statusLine.command' "$SET")" "sync: stale ours re-pinned"
assert_equals "$NEWCMD" "$(jq -r '.command' "$DATA/owned.json")" "sync: owned.json updated"
rm -rf "$TMP"

# Case C: foreign statusLine -> untouched
run_sync
mkdir -p "$DATA"
jq -n '{statusLine:{type:"command",command:"~/my/other.sh"}}' > "$SET"
jq -n --arg c "$OLDCMD" '{command:$c, icons:"nerd"}' > "$DATA/owned.json"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$NEWROOT" bash "$ROOT/scripts/sync.sh"
assert_equals "~/my/other.sh" "$(jq -r '.statusLine.command' "$SET")" "sync: foreign untouched"
rm -rf "$TMP"

echo
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
