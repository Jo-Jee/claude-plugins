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
out=$(printf '%s' "$FULL" | sh "$REND")
assert_contains "~/proj" "$out" "full: cwd shown with ~"
assert_contains "Opus 4.8" "$out" "full: model shown"
assert_contains "42%" "$out" "full: context percent shown"
assert_contains "5h 30%" "$out" "full: rate-limit percent shown"
assert_contains "high" "$out" "full: effort shown"

NOGIT='{"cwd":"/tmp/nowhere-xyz","model":{"display_name":"Haiku"}}'
out=$(printf '%s' "$NOGIT" | sh "$REND")
assert_contains "Haiku" "$out" "no-git: model still shown"

# Branch renders only inside a real git repo, so use the repo root as cwd.
GITFIX='{"cwd":"'"$ROOT"'","model":{"display_name":"Opus 4.8"}}'
out=$(printf '%s' "$GITFIX" | sh "$REND")
BR=$(git -C "$ROOT" symbolic-ref --short HEAD 2>/dev/null || git -C "$ROOT" rev-parse --short HEAD)
assert_contains "$BR" "$out" "git: branch name shown"

out=$(PATH= /bin/sh "$REND" </dev/null)
assert_contains "jq not found" "$out" "no-jq: prints hint"

echo "== lib-settings =="
TMP=$(mktemp -d)
export STATUSLINE_SETTINGS="$TMP/settings.json"
export STATUSLINE_DATA="$TMP/data"
export STATUSLINE_ROOT="/opt/plugins/statusline"
# shellcheck source=/dev/null
. "$ROOT/scripts/lib-settings.sh"

assert_equals '"/opt/plugins/statusline/scripts/statusline.sh"' \
  "$(build_command "$(plugin_root)")" "build_command formats path"

write_statusline_command 'CMD_A'
assert_equals "CMD_A" "$(read_statusline_command)" "write/read roundtrip"
assert_equals "command" "$(jq -r '.statusLine.type' "$STATUSLINE_SETTINGS")" "write sets type=command"

owned_write "CMD_A"
assert_equals "CMD_A" "$(owned_get_command)" "owned command recorded"

backup_settings
remove_statusline
assert_equals "" "$(read_statusline_command)" "remove_statusline clears entry"
restore_settings_backup
assert_equals "CMD_A" "$(read_statusline_command)" "restore brings back entry"

owned_clear
assert_equals "" "$(owned_get_command)" "owned_clear removes record"
rm -rf "$TMP"
unset STATUSLINE_SETTINGS STATUSLINE_DATA STATUSLINE_ROOT

echo "== sync =="
run_sync() {
  TMP=$(mktemp -d)
  SET="$TMP/settings.json"; DATA="$TMP/data"; NEWROOT="/opt/plugins/statusline-v2"
  NEWCMD='"/opt/plugins/statusline-v2/scripts/statusline.sh"'
  OLDCMD='"/opt/plugins/statusline-v1/scripts/statusline.sh"'
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
jq -n --arg c "$OLDCMD" '{command:$c}' > "$DATA/owned.json"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$NEWROOT" bash "$ROOT/scripts/sync.sh"
assert_equals "$NEWCMD" "$(jq -r '.statusLine.command' "$SET")" "sync: stale ours re-pinned"
assert_equals "$NEWCMD" "$(jq -r '.command' "$DATA/owned.json")" "sync: owned.json updated"
rm -rf "$TMP"

# Case C: foreign statusLine -> untouched
run_sync
mkdir -p "$DATA"
jq -n '{statusLine:{type:"command",command:"~/my/other.sh"}}' > "$SET"
jq -n --arg c "$OLDCMD" '{command:$c}' > "$DATA/owned.json"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$NEWROOT" bash "$ROOT/scripts/sync.sh"
assert_equals "~/my/other.sh" "$(jq -r '.statusLine.command' "$SET")" "sync: foreign untouched"
rm -rf "$TMP"

echo "== setup =="
S="$ROOT/scripts/setup.sh"

# Regression: slash commands do NOT export CLAUDE_PLUGIN_ROOT/DATA into the shell.
# With those and STATUSLINE_ROOT all unset, setup.sh must derive its own root from
# the script location and must NOT crash under set -u (unbound variable).
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"
printf '{}\n' > "$SET"
env -u STATUSLINE_ROOT -u CLAUDE_PLUGIN_ROOT -u CLAUDE_PLUGIN_DATA \
  STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" bash "$S" install >/dev/null 2>&1
rc=$?
assert_equals "0" "$rc" "setup: no unbound-variable crash without plugin env vars"
assert_contains "statusline/scripts/statusline.sh" "$(jq -r '.statusLine.command' "$SET")" \
  "setup: derives plugin root from script location"
rm -rf "$TMP"

# install onto empty
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
printf '{}\n' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install >/dev/null
assert_equals '"/opt/plugins/statusline/scripts/statusline.sh"' \
  "$(jq -r '.statusLine.command' "$SET")" "setup: install onto empty"
st=$(STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" status)
assert_contains "state: ours" "$st" "setup: status reports ours"
rm -rf "$TMP"

# install refuses foreign without --force
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
jq -n '{statusLine:{type:"command",command:"~/foreign.sh"}}' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install >/dev/null 2>&1
rc=$?
assert_equals "2" "$rc" "setup: install refuses foreign (exit 2)"
assert_equals "~/foreign.sh" "$(jq -r '.statusLine.command' "$SET")" "setup: foreign untouched without force"
rm -rf "$TMP"

# install --force replaces foreign and backs up
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
jq -n '{statusLine:{type:"command",command:"~/foreign.sh"}}' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install --force >/dev/null
assert_contains "statusline.sh" "$(jq -r '.statusLine.command' "$SET")" "setup: --force replaced foreign"
assert_equals "~/foreign.sh" "$(jq -r '.statusLine.command' "$SET.bak")" "setup: --force backed up original"
rm -rf "$TMP"

# uninstall removes ours
TMP=$(mktemp -d); SET="$TMP/settings.json"; DATA="$TMP/data"; RT="/opt/plugins/statusline"
printf '{}\n' > "$SET"
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" install >/dev/null
STATUSLINE_SETTINGS="$SET" STATUSLINE_DATA="$DATA" STATUSLINE_ROOT="$RT" bash "$S" uninstall >/dev/null
assert_equals "" "$(jq -r '.statusLine.command // empty' "$SET")" "setup: uninstall removed ours"
rm -rf "$TMP"

echo
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
