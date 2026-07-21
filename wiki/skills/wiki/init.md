---
name: wiki-init
description: Initialize a wiki directory structure in a project
---

# Wiki Init

## Workflow

1. Confirm the project root (git root)
2. Run:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py init <project_root>
   ```
3. Print the completion message

No LLM work required. The Python CLI handles everything:
- Creates the `wiki/` directory structure
- Copies the `CLAUDE.md` template
- Initializes `index.md` and `log.md`
- Creates the `.obsidian/` config
- Automatically appends an init entry to `log.md`
