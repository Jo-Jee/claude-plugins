---
name: wiki-ingest
description: Read raw/ sources and integrate them into wiki pages
---

# Wiki Ingest

Reads source documents and converts them into wiki pages. Body processing is delegated to a subagent so it doesn't pollute Claude's main context.

## Workflow

### 1. Find unprocessed sources (Claude)

```bash
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py list-raw <wiki_path> --unprocessed
```

Show the list to the user and confirm which source to ingest. **One at a time.**

### 2. Delegate to a subagent (Agent)

Invoke a `general-purpose` subagent via the `Agent` tool. Fill in the `<...>` placeholders in the prompt template below.

**Important**: `${CLAUDE_SKILL_DIR}` inside the prompt may not resolve in the subagent context, so substitute it with the absolute path before sending (e.g., `/Users/.../.claude/skills/wiki`).

~~~
This is a wiki ingest task. Perform the following in order.

- Wiki path: <wiki_path>
- Tools CLI: python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py
- Source file: <raw_relative_path>  (relative to wiki_path, e.g., raw/notes/foo.md)

Steps:

1. Read the source file and identify the key content.

2. Create the source page:
   `<Tools CLI> create-page <wiki_path> source <slug> --title "<title>" --sources "<raw_relative_path>"`
   Then fill in the generated skeleton file body with Edit (summary, key claims, quotations).

3. Extract entities/concepts from the source. For each:
   - New page: `<Tools CLI> create-page <wiki_path> entity|concept <slug> --title "<title>"`
     → write the body via Edit
   - Existing page update: edit the file directly, then
     `<Tools CLI> update-frontmatter <file_path> --updated today`

4. Conflict handling: when new info contradicts existing content, **keep both side by side, do not delete**:
   ```
   > [!conflict]
   > Previous: ...
   > Per new source (<source_slug>): ...
   ```

5. Cross-references: use `[[page-name]]` format. Use a See Also section on related pages.

6. Sync the index for each created/modified page:
   `<Tools CLI> sync-index <wiki_path> --add <page_relative_path> --summary "<one-line summary>"`

7. Append a log entry:
   `<Tools CLI> log-append <wiki_path> ingest "<source title>" --created "sources/x.md,entities/y.md" --modified "concepts/z.md"`

Output rules:
- Only print the list of created/modified files with a one-line summary each.
- Do not copy or quote raw file content (apart from minimal quotations stored on wiki pages).
- Do not print intermediate reasoning.
~~~

### 3. Confirm results (Claude)

Show the subagent output (created/modified list + summary) to the user and confirm whether to proceed to the next source.

## Rules

- **Do not load raw file contents into Claude's main context.** The subagent reads the full text.
- The subagent also runs Python CLI calls (`create-page`, `sync-index`, `log-append`, etc.) directly.
- Only one source at a time. Confirm with the user before continuing.
- Do not bundle multiple sources into a single subagent call — this preserves user curation.
