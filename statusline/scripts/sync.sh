#!/usr/bin/env bash
# SessionStart hook: re-pin the statusLine to the current absolute plugin path,
# but ONLY if the existing entry is one we previously wrote. Never adds a
# statusLine when none exists; never overwrites a foreign one.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$DIR/lib-settings.sh"

command -v jq >/dev/null 2>&1 || exit 0

computed=$(build_command "$(plugin_root)")
current=$(read_statusline_command)
owned=$(owned_get_command)

# Nothing configured -> never silently add one.
if [ -z "$current" ]; then exit 0; fi
# Already correct.
if [ "$current" = "$computed" ]; then exit 0; fi
# Ours but stale (plugin path changed after an update) -> re-pin.
if [ -n "$owned" ] && [ "$current" = "$owned" ]; then
  write_statusline_command "$computed"
  owned_write "$computed"
fi
exit 0
