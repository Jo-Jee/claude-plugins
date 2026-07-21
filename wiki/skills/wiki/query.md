---
name: wiki-query
description: Search the wiki and synthesize an answer
---

# Wiki Query

Searches wiki pages and synthesizes an answer.

## Workflow

### 1. Verify index consistency

```bash
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py sync-index <wiki_path> --check
```

Fix any mismatches first.

### 2. Read the index

Read the wiki's `index.md` (`$WIKI/index.md`, i.e. `<wiki_path>/index.md`) and find pages relevant to the question.

### 3. Synthesize an answer

Read the relevant pages and synthesize an answer. Always cite the source:

```
Answer text... (source: [[page-name]])
```

### 4. Decide if reusable

If the answer has reuse value, save it under `analyses/` or `comparisons/`:

```bash
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py create-page <wiki_path> analysis <slug> --title "Title"
# or
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py create-page <wiki_path> comparison <slug> --title "A vs B"
```

Fill in the body via Edit, then update the index:
```bash
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py sync-index <wiki_path> --add <page_path> --summary "one-line summary"
```

### 5. Append a log entry

```bash
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py log-append <wiki_path> query "Question summary" --refs "concepts/a.md,entities/b.md"
```
