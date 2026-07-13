---
description: Show your English mistake history and trends captured by english-coach
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/stats.sh:*)
---
The output below comes from the english-coach mistake log.

Optional argument (`$ARGUMENTS`): `summary` (default), `recent [N]`, `category <name>`, or `since <YYYY-MM-DD>`.

Present the results clearly, and if it's a full summary, call out my most frequent mistake categories and whether I appear to be improving over time.

!`"${CLAUDE_PLUGIN_ROOT}/scripts/stats.sh" $ARGUMENTS`
