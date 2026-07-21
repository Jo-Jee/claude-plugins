#!/usr/bin/env bash
# SessionStart hook: surface the linked project wiki's catalog.
# Reads the $CLAUDE_CONFIG_DIR/wiki symlink and prints JSON with additionalContext.
# Silent (exit 0, no stdout) when no wiki is linked or the catalog is missing.
set -u

CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
WIKI="$CONFIG_DIR/wiki"
INDEX="$WIKI/index.md"

# No linked wiki (missing / broken symlink) or no catalog -> silent no-op.
[ -e "$WIKI" ] || exit 0
[ -f "$INDEX" ] || exit 0

CTX="$(printf 'Project documentation lives in the wiki (%s). Follow its CLAUDE.md; every document must live there.\n\n%s' \
  "$WIKI" "$(cat "$INDEX")")"

jq -n --arg ctx "$CTX" \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
