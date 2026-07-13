# statusline

A polished Claude Code statusline: current directory, git branch (with dirty marker),
model, reasoning effort, an 8-segment context-window bar, and a 5-hour rate-limit bar
with reset time. Nerd Font icons by default, with an ASCII fallback.

## Requirements

- `jq` (required). Without it the statusline prints a one-line hint instead of rendering.
- A Nerd Font in your terminal for the default icons — or use `--ascii`.

## Install

```
/plugin marketplace add Jo-Jee/claude-plugins
/plugin install statusline@jojee-tools
/statusline-setup           # or: /statusline-setup --ascii
```

`/statusline-setup` writes a `statusLine` entry into `~/.claude/settings.json`. It never
overwrites an existing statusline without asking (your original is backed up to
`settings.json.bak`). A SessionStart hook re-pins the path automatically after plugin
updates. The statusline appears in new sessions.

## Uninstall

```
/statusline-uninstall       # run this FIRST — removes our settings.json entry
/plugin uninstall statusline@jojee-tools
```

`/statusline-uninstall` removes the entry only if this plugin owns it, restoring any
statusline it previously replaced.

## Notes

Claude Code plugins cannot declare a main `statusLine` directly, and
`${CLAUDE_PLUGIN_ROOT}` does not expand in the statusline execution context — so this
plugin writes an absolute path into your settings and re-pins it each session.
