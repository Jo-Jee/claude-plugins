# Design: `statusline` plugin

**Date:** 2026-07-13
**Marketplace:** `jojee-tools`
**Plugin name:** `statusline`
**Setup command:** `/statusline-setup`
**Status:** Approved (design)

## Purpose

Package the author's existing Claude Code statusline (`~/.claude/statusline-command.sh`)
as a **publishable** plugin in the `jojee-tools` marketplace, so anyone can install it via
`/plugin install`. Publishing raises the bar on install UX, collision safety, dependency
robustness, and clean uninstall.

## Key constraint

Claude Code plugins **cannot declare a main `statusLine`**. Plugin `settings.json` only honors
`agent` and `subagentStatusLine`. Additionally, `${CLAUDE_PLUGIN_ROOT}` **does not expand** in the
statusline execution context (it does expand in hooks). Therefore a statusline plugin must:

1. Ship the renderer script inside the plugin, and
2. Programmatically write an **absolute-path** `statusLine` entry into the user's
   `~/.claude/settings.json` via a hook / command.

This is the pattern used by the only clean real-world example, `z80020100/claude-code-statusline`.

Refs: https://code.claude.com/docs/en/statusline ,
https://code.claude.com/docs/en/plugins-reference.md ,
https://github.com/anthropics/claude-code/issues/64074 ,
https://github.com/z80020100/claude-code-statusline

## Decisions

| Area | Decision |
|------|----------|
| Purpose | Publish for others |
| Install | SessionStart hook (re-pins absolute path) **+** `/statusline-setup` for first run |
| Collision | Never clobber a foreign statusline; hook re-pins only entries this plugin wrote (ownership marker); `/setup` prompts before replacing a foreign entry, backing it up |
| Script | Hardened: jq-missing hint + ASCII icon fallback when no Nerd Font |
| Name | `statusline` (command `/statusline-setup`) |

## Architecture & file layout

```
statusline/
├── .claude-plugin/
│   └── plugin.json                 # name, version, author
├── hooks/
│   └── hooks.json                  # SessionStart → scripts/sync.sh
├── scripts/
│   ├── statusline.sh               # renderer: pure stdin JSON -> stdout text
│   ├── sync.sh                     # SessionStart: re-pin absolute path (ownership-checked)
│   ├── lib-settings.sh             # shared jq helpers to read/patch ~/.claude/settings.json
│   └── test.sh                     # golden-case tests for renderer + settings mutation
└── commands/
    ├── statusline-setup.md         # /statusline-setup    -> first-run install + collision prompt
    └── statusline-uninstall.md     # /statusline-uninstall -> clean removal
```

Marketplace: add a second entry to `.claude-plugin/marketplace.json`.

**Unit boundaries.** The renderer (`statusline.sh`) stays a pure `stdin -> stdout` formatter —
that is all Claude Code invokes per frame, so it must have no side effects. The install / re-pin
logic (`sync.sh`, the command handlers) is a distinct job — it mutates `settings.json` and runs on
a different trigger (SessionStart / explicit command). Shared settings-file read/patch helpers live
in `lib-settings.sh` so both the sync hook and both commands use one tested code path.

## Install & collision logic (core)

Ownership state is kept in `${CLAUDE_PLUGIN_DATA}/owned.json`, recording that this plugin wrote the
current `statusLine` and the exact command string it wrote.

**`/statusline-setup`** reads `~/.claude/settings.json`:

- No `statusLine` present -> write ours, record ownership. Done.
- `statusLine` present **and matches our recorded command** -> already ours; re-pin the absolute path.
- `statusLine` present **and foreign** -> STOP and ask the user:
  *"You already have a statusline: `<cmd>`. Replace it? The original will be backed up to
  `settings.json.bak`."* Replace only on explicit yes; record ownership; keep backup.

**SessionStart `sync.sh`** (silent, non-interactive) re-pins the absolute `statusLine` path **only
if** the current `statusLine` still matches our ownership record. If the entry is foreign or absent,
it does nothing — it never steals ownership silently. This is what survives plugin updates (install
directory path changes) and works around `${CLAUDE_PLUGIN_ROOT}` not expanding in the statusline
context.

## Script hardening

- **jq missing** -> statusline prints one clear line
  (`⚠ statusline: jq not found — install jq`) instead of erroring or rendering blank.
- **Nerd Font fallback** -> icon set selected by an env var baked into the written command at setup
  time: `STATUSLINE_ICONS=nerd|ascii` (default `nerd`; `/setup` offers ascii). ASCII map:
  dir `▸`, branch `git:`, ctx `ctx`, 5h `5h`, model `»`, effort `fx`.
- Everything else ports over from the current script unchanged: context-window bar (green/yellow/red
  thresholds), 5h rate-limit bar with reset time + remaining, worktree-path handling, `$HOME`->`~`
  display, git branch + dirty marker.

## Uninstall / cleanup

Claude Code has **no uninstall hook**, so uninstalling a plugin leaves a "zombie" `statusLine` entry
behind. Mitigation: ship **`/statusline-uninstall`**, which removes our `statusLine` entry from
`settings.json` **only if we own it** (restoring `settings.json.bak` if present) and clears the
ownership record. README documents: run `/statusline-uninstall` *before* `/plugin uninstall`.

## Testing

- **Renderer** (`test.sh` golden cases): feed recorded stdin JSON fixtures and assert stdout —
  full payload; no-git; worktree present; missing `rate_limits`; jq missing (simulated via `PATH`);
  `STATUSLINE_ICONS=ascii`.
- **Settings mutation:** run `sync.sh` / setup against a temp `HOME` with crafted `settings.json`
  states (empty / ours / foreign) and assert correct write / skip / backup behavior. This is the
  risky part and gets the most coverage.

## Out of scope (YAGNI)

- Rewriting the renderer to be jq-free (portability nice-to-have; not needed now).
- Configurable segments / theming beyond the nerd/ascii icon toggle.
- `subagentStatusLine` support (separate feature; not requested).
