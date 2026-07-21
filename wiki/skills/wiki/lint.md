---
name: wiki-lint
description: Wiki health check — structural + semantic lint
---

# Wiki Lint

Detects and fixes structural and semantic problems in the wiki. Fixes and the semantic lint pass are delegated to a subagent so they don't pollute Claude's main context.

## Workflow

### Phase 1: Structural Lint (Python CLI, Claude)

Run in order. Each command prints a JSON report and exits with code 1 when problems are found:

```bash
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py validate-frontmatter <wiki_path>
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py lint-links <wiki_path>
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py sync-index <wiki_path> --check
python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py check-raw <wiki_path>
```

Collect each JSON report. If they are all empty and the wiki is very small (<5 pages), Phase 2 may be skipped — go straight to Phase 3. Otherwise proceed to Phase 2.

### Phase 2: Delegate to a subagent (Agent)

Invoke a `general-purpose` subagent via the `Agent` tool. Attach the Phase 1 reports to the prompt verbatim.

**Important**: `${CLAUDE_SKILL_DIR}` inside the prompt may not resolve in the subagent context, so substitute it with the absolute path before sending.

~~~
This is a wiki lint task. Perform structural fixes + semantic lint.

- Wiki path: <wiki_path>
- Tools CLI: python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py

Phase 1 Python reports (structural issues):
<validate-frontmatter JSON or "none">
<lint-links JSON or "none">
<sync-index --check JSON or "none">
<check-raw JSON or "none">

Perform the following in order.

A) Structural fixes (driven by the reports above)
- Missing frontmatter fields: `<Tools CLI> update-frontmatter <file_path> --<field> <value>`
- Index mismatches: `<Tools CLI> sync-index <wiki_path> --add <page_path> --summary "..."` or `--remove <page_path>`
- Broken `[[link]]`: fix the reference, or create the page if needed (`create-page`)
- Orphan pages: add a `[[]]` cross-reference from the most relevant page
- raw file changes detected (check-raw): investigate the cause and report (do NOT modify raw)

B) Semantic lint (scan wiki pages)
Read the entire wiki and judge:
- **Contradictions**: pages disagreeing on the same fact → keep both with a `> [!conflict]` callout
- **Stale claims**: content superseded by a newer source → conflict callout + `[[source-page]]` link
- **Missing cross-references**: a page mentions another page without a `[[]]` link → add the link
- **Uncreated entities/concepts**: mentioned in body but no dedicated page → judge importance, then `create-page` or skip

C) Append a log entry:
`<Tools CLI> log-append <wiki_path> lint "Routine check" --note "found N / fixed M / unresolved K"`

Output rules:
- Print only the list of fixes (path + one-line summary) and **unresolved issues**.
- Do not copy or quote wiki page content.
- Do not print intermediate reasoning.
~~~

### Phase 3: Confirmation (Claude)

Pass the subagent output to the user. If unresolved issues remain, surface only those that need user judgment.

## Rules

- **Do not load wiki page contents into Claude's main context.** Only handle the Phase 1 JSON reports and the subagent summary.
- Never modify files under `raw/` (this also applies to the subagent).
- The subagent must not delete pages on its own. The prompt must require contradictions and stale claims to be **kept side by side**.
