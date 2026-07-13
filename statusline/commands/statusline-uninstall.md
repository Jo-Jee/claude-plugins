---
description: Remove the statusline plugin's entry from your Claude Code settings
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh:*)
---
Remove the `statusline` plugin's statusLine entry from settings.json. It is removed only if this plugin owns it (a previously backed-up statusline is restored). Run this BEFORE `/plugin uninstall` to avoid leaving a dangling statusLine command. Relay the result below to the user.

!`"${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh" uninstall`
