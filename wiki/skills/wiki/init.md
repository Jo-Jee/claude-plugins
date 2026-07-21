---
name: wiki-init
description: Initialize a wiki directory structure in a project
---

# Wiki Init

## Workflow

The wiki is a **standalone repository**. `init` scaffolds it, links it into this
project's Claude config dir, and adds a delegating pointer to the root `CLAUDE.md`.

1. Determine the target directory for the wiki repo:
   - If `$ARGUMENTS` gives a path, use it.
   - Otherwise use the current directory (`$PWD`) — assume the user is inside the
     intended wiki repo. Confirm the path with the user before proceeding.

2. Scaffold the structure at the target root (no `wiki/` wrapper):
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py init <target>
   ```

3. Link it so every session can see it:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py link <target>
   ```

4. Add the delegating pointer to `$CLAUDE_CONFIG_DIR/CLAUDE.md`:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py ensure-root-pointer
   ```

5. Tell the user: the wiki is initialized at `<target>`, linked at
   `$CLAUDE_CONFIG_DIR/wiki`, and its catalog will appear at the start of every
   session. All wiki rules live in `<target>/CLAUDE.md`.

The Python CLI creates the directory structure, the `CLAUDE.md` template, `index.md`,
`log.md`, and the `.obsidian/` config; `link` and `ensure-root-pointer` are idempotent.
