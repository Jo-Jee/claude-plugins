---
title: Claude Code plugin command naming convention
date: 2026-07-13
tags: [claude-code, plugins, convention]
type: note
---

# Plugin command files must not repeat the plugin name

Claude Code namespaces a plugin's slash commands as `/<plugin>:<command>`, where
`<command>` is the command file's basename (without `.md`). So a command file that
already starts with the plugin name produces a doubled, redundant invocation.

**Rule:** name command files by the action only — `setup.md`, `uninstall.md`,
`stats.md`, `train.md` — never `<plugin>-<action>.md`.

## Examples

| Plugin | Bad file name | Bad command | Good file name | Good command |
|--------|---------------|-------------|----------------|--------------|
| `english-coach` | `english-coach-stats.md` | `/english-coach:english-coach-stats` | `stats.md` | `/english-coach:stats` |
| `statusline` | `statusline-setup.md` | `/statusline:statusline-setup` | `setup.md` | `/statusline:setup` |

## Related gotcha (same session)

Slash commands expand `${CLAUDE_PLUGIN_ROOT}` **textually** into the command path
but do **not** export `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA` as environment
variables. Scripts run with `set -u` must therefore derive their own location
(e.g. `STATUSLINE_ROOT="$(cd "$DIR/.." && pwd)"`) rather than dereferencing those
vars, or they abort with "unbound variable".
