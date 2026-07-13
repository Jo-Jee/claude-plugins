---
description: Install (or re-pin) the statusline plugin into your Claude Code settings
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh:*)
---
Set up the `statusline` plugin. Optional `$ARGUMENTS`: `--ascii` (ASCII icons instead of Nerd Font) or `--force` (replace an existing foreign statusline).

Interpret the output below:
- If it reports a different statusline is already configured (exit note about `--force`) and the user did NOT pass `--force`, STOP: show them the `current:` line and ask whether to replace it (their original is backed up to `settings.json.bak`). Only after they confirm, run `"${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" install --force` (add `--ascii` if they wanted it) via the Bash tool.
- Otherwise, confirm what was installed and remind them it takes effect in new sessions.

!`"${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" install $ARGUMENTS`
