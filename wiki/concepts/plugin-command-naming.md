---
title: Plugin Command Naming (no redundant prefix)
type: concept
created: 2026-07-14
updated: 2026-07-14
sources: []
tags: [claude-code, plugins, convention]
sources: [raw/notes/2026-07-13-plugin-command-naming-convention.md]
---

# Plugin Command Naming (no redundant prefix)

Claude Code namespaces every plugin slash command as `/<plugin>:<command>`, where
`<command>` is the command file's basename (minus `.md`). The plugin prefix is added
automatically, so **a command filename must not repeat the plugin name** — otherwise the
invocation doubles up (`/statusline:statusline-setup`).

**Rule:** name command files by the action alone — `setup.md`, `uninstall.md`,
`stats.md`, `train.md` — never `<plugin>-<action>.md`.

| Good file | Invocation | Bad file | Bad invocation |
|-----------|------------|----------|----------------|
| `setup.md` | `/statusline:setup` | `statusline-setup.md` | `/statusline:statusline-setup` |
| `stats.md` | `/english-coach:stats` | `english-coach-stats.md` | `/english-coach:english-coach-stats` |

## Concrete application

The [[english-coach]] plugin follows this rule: its command files are `stats.md` (renamed
from `english-coach-stats.md`) and `train.md`, invoked as `/english-coach:stats` and
`/english-coach:train`.

## See Also
- [[plugin-command-naming-convention]] — source note
- [[english-coach]] — applies the rule
