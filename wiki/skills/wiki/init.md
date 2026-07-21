---
name: wiki-init
description: Initialize a wiki directory structure in a project
---

# Wiki Init

## Workflow

The wiki is a **standalone repository**. `init` scaffolds it, links it into this
project's Claude config dir, and adds a delegating pointer to the root `CLAUDE.md`.

Run these from **inside the intended wiki directory** — `init` and `link` default to
the current directory, so no path argument is needed. (You may still pass an explicit
path as `$ARGUMENTS` to target a different directory.)

1. Scaffold the structure at the current directory (no `wiki/` wrapper):
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py init
   ```
   If the directory is not already under git control, this also runs `git init`
   so the wiki starts as its own standalone repository. When the wiki lives
   inside an existing repo, no nested repo is created.

2. Link it so every session can see it:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py link
   ```

3. Add the delegating pointer to `$CLAUDE_CONFIG_DIR/CLAUDE.md`:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py ensure-root-pointer
   ```

4. Tell the user: the wiki is initialized at the current directory, linked at
   `$CLAUDE_CONFIG_DIR/wiki`, and its catalog will appear at the start of every
   session. All wiki rules live in the wiki's `CLAUDE.md`.

The Python CLI creates the directory structure, the `CLAUDE.md` template, `index.md`,
`log.md`, and the `.obsidian/` config; `link` and `ensure-root-pointer` are idempotent.
