# statusline

A polished Claude Code statusline: current directory, git branch (with dirty marker),
model, reasoning effort, an 8-segment context-window bar, and a 5-hour rate-limit bar
with reset time, rendered with Nerd Font icons.

## Requirements

- **A Nerd Font** in your terminal — required for the icons. Without one, the icon
  glyphs render as tofu (□) boxes. Install one from [nerdfonts.com](https://www.nerdfonts.com)
  and set it as your terminal font.
- `jq` — required. Without it the statusline prints a one-line hint instead of rendering.

## Install

```
/plugin marketplace add Jo-Jee/claude-plugins
/plugin install statusline@jojee-tools
/statusline:setup
```

`/statusline:setup` writes a `statusLine` entry into your Claude Code `settings.json`
(under `$CLAUDE_CONFIG_DIR` if set, otherwise `~/.claude`). It never overwrites an
existing statusline without asking (your original is backed up to `settings.json.bak`).
A SessionStart hook re-pins the path automatically after plugin updates. The statusline
appears in new sessions.

## Uninstall

```
/statusline:uninstall       # run this FIRST — removes our settings.json entry
/plugin uninstall statusline@jojee-tools
```

`/statusline:uninstall` removes the entry only if this plugin owns it, restoring any
statusline it previously replaced.

## Notes

Claude Code plugins cannot declare a main `statusLine` directly, and
`${CLAUDE_PLUGIN_ROOT}` does not expand in the statusline execution context — so this
plugin writes an absolute path into your settings and re-pins it each session.
