#!/usr/bin/env bash
# Shared helpers: read/patch ~/.claude/settings.json and track whether THIS
# plugin owns the current statusLine entry. Source this file; do not execute.
# Test overrides: STATUSLINE_SETTINGS, STATUSLINE_DATA, STATUSLINE_ROOT.

settings_path() { printf '%s' "${STATUSLINE_SETTINGS:-$HOME/.claude/settings.json}"; }
# CLAUDE_PLUGIN_DATA/ROOT are not exported into a slash command's shell, so we
# never dereference them bare (set -u would abort). owned.json lives in a stable
# location independent of invocation context; the plugin root is supplied by the
# caller (setup.sh/sync.sh export STATUSLINE_ROOT from their own path).
owned_path()    { printf '%s' "${STATUSLINE_DATA:-$HOME/.claude/statusline}/owned.json"; }
plugin_root()   { printf '%s' "${STATUSLINE_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}"; }

build_command() {
  # $1 root
  printf '"%s/scripts/statusline.sh"' "$1"
}

read_statusline_command() {
  _sp=$(settings_path)
  [ -f "$_sp" ] || return 0
  jq -r '.statusLine.command // empty' "$_sp" 2>/dev/null
}

write_statusline_command() {
  _sp=$(settings_path)
  mkdir -p "$(dirname "$_sp")"
  [ -f "$_sp" ] || printf '{}\n' > "$_sp"
  _tmp="${_sp}.tmp.$$"
  jq --arg cmd "$1" '.statusLine = {type:"command", command:$cmd}' "$_sp" > "$_tmp" && mv "$_tmp" "$_sp"
}

remove_statusline() {
  _sp=$(settings_path)
  [ -f "$_sp" ] || return 0
  _tmp="${_sp}.tmp.$$"
  jq 'del(.statusLine)' "$_sp" > "$_tmp" && mv "$_tmp" "$_sp"
}

backup_settings() {
  _sp=$(settings_path)
  [ -f "$_sp" ] && cp "$_sp" "${_sp}.bak"
  return 0
}

restore_settings_backup() {
  _sp=$(settings_path)
  [ -f "${_sp}.bak" ] && mv "${_sp}.bak" "$_sp"
  return 0
}

owned_get_command() {
  _op=$(owned_path)
  [ -f "$_op" ] || return 0
  jq -r '.command // empty' "$_op" 2>/dev/null
}

owned_write() {
  _op=$(owned_path)
  mkdir -p "$(dirname "$_op")"
  jq -n --arg cmd "$1" '{command:$cmd}' > "$_op"
}

owned_clear() {
  rm -f "$(owned_path)"
}
