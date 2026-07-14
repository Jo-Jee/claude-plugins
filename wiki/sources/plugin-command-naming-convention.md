---
title: Claude Code Plugin Command Naming Convention
type: source
created: 2026-07-14
updated: 2026-07-14
sources: [raw/notes/2026-07-13-plugin-command-naming-convention.md]
tags: [claude-code, plugins, convention]
---

# Claude Code Plugin Command Naming Convention

Source note capturing a general Claude Code plugin convention. The reusable rule
lives in [[plugin-command-naming]].

## The rule

Claude Code namespaces a plugin's slash commands as `/<plugin>:<command>`, where
`<command>` is the command file's basename (without `.md`). A command file whose name
already starts with the plugin name therefore produces a doubled, redundant invocation.

**Name command files by the action only** — `setup.md`, `uninstall.md`, `stats.md`,
`train.md` — never `<plugin>-<action>.md`.

## Why

Because the plugin prefix is added automatically by the namespacing scheme, repeating it
in the filename yields awkward commands like `/statusline:statusline-setup`. Dropping the
prefix keeps invocations clean (`/statusline:setup`) with no loss of clarity.

## Examples

| Plugin | Bad file name | Bad command | Good file name | Good command |
|--------|---------------|-------------|----------------|--------------|
| `english-coach` | `english-coach-stats.md` | `/english-coach:english-coach-stats` | `stats.md` | `/english-coach:stats` |
| `statusline` | `statusline-setup.md` | `/statusline:statusline-setup` | `setup.md` | `/statusline:setup` |

## Related gotcha (same source)

Slash commands expand `${CLAUDE_PLUGIN_ROOT}` **textually** into the command path but do
**not** export `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA` as environment variables.
Scripts run with `set -u` must derive their own location (e.g.
`STATUSLINE_ROOT="$(cd "$DIR/.." && pwd)"`) rather than dereferencing those vars, or they
abort with "unbound variable".

## See Also
- [[plugin-command-naming]]
- [[english-coach]]
