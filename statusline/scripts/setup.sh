#!/usr/bin/env bash
# /statusline:setup and /statusline:uninstall helper.
# Usage: setup.sh <status|install|uninstall> [--force]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# Derive the plugin root from this script's own location. Slash commands expand
# ${CLAUDE_PLUGIN_ROOT} textually into the path but do NOT export it as an env
# var, so we cannot rely on $CLAUDE_PLUGIN_ROOT here.
: "${STATUSLINE_ROOT:=$(cd "$DIR/.." && pwd)}"
export STATUSLINE_ROOT
# shellcheck source=/dev/null
. "$DIR/lib-settings.sh"
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq not found — install jq first."; exit 1; }

force=""; cmd="status"
for a in "$@"; do
  case "$a" in
    --force) force="1" ;;
    status|install|uninstall) cmd="$a" ;;
    *) : ;;
  esac
done

computed=$(build_command "$(plugin_root)")
current=$(read_statusline_command)
owned=$(owned_get_command)

is_ours() { [ -n "$current" ] && { [ "$current" = "$owned" ] || [ "$current" = "$computed" ]; }; }

case "$cmd" in
  status)
    if [ -z "$current" ]; then echo "state: none";
    elif is_ours; then echo "state: ours";
    else echo "state: foreign"; echo "current: $current"; fi
    ;;
  install)
    if [ -z "$current" ] || is_ours; then
      write_statusline_command "$computed"; owned_write "$computed"
      echo "installed: $computed"
      echo "Takes effect in new sessions."
    elif [ -n "$force" ]; then
      backup_settings
      write_statusline_command "$computed"; owned_write "$computed"
      echo "replaced foreign statusline (backup: $(settings_path).bak)"
      echo "installed: $computed"
    else
      echo "A different statusline is already configured."
      echo "current: $current"
      echo "Re-run with --force to replace it (a backup will be made)."
      exit 2
    fi
    ;;
  uninstall)
    if [ -z "$current" ]; then
      owned_clear; echo "no statusline configured; nothing to remove."
    elif is_ours; then
      remove_statusline
      if [ -f "$(settings_path).bak" ]; then
        restore_settings_backup; echo "removed; restored previous statusline from backup."
      else
        echo "removed the statusline plugin's entry."
      fi
      owned_clear
    else
      echo "the current statusline is not ours; leaving it untouched."
      echo "current: $current"
    fi
    ;;
esac
