# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this wiki.

## Project

{{PROJECT_NAME}} — A knowledge base based on Karpathy's LLM Wiki pattern. The LLM reads original sources and incrementally builds and maintains a structured Markdown wiki. Unlike RAG, which re-extracts information every time, the goal here is to compile and accumulate knowledge.

## Directory Structure

```
wiki/
├── CLAUDE.md              # Schema — wiki rules & workflows
├── index.md               # Catalog of all wiki pages
├── log.md                 # Chronological activity log (append-only)
│
├── raw/                   # Original sources (immutable, no LLM edits)
│   ├── articles/          # Web articles, blog posts
│   ├── papers/            # Papers, technical documents
│   ├── notes/             # Meeting notes, memos
│   └── assets/            # Images, attachments
│
├── sources/               # Per-source summary pages (1 source = 1 page)
├── entities/              # Entities (people, tools, services, companies, etc.)
├── concepts/              # Concepts, topics, techniques
├── analyses/              # Analyses derived from queries
└── comparisons/           # Comparison analyses (A vs B)
```

## Three Layers

| Layer | Description | Owner |
|-------|-------------|-------|
| **Raw Sources** (`raw/`) | Original documents. Immutable. Never modify. | Human |
| **Wiki** (`sources/`, `entities/`, `concepts/`, `analyses/`, `comparisons/`) | Markdown pages created and maintained by the LLM. | LLM |
| **Schema** (`CLAUDE.md`) | Defines wiki structure, rules, and workflows. | Human + LLM |

## Page Format

Every wiki page must include YAML frontmatter.

```markdown
---
title: Page title
type: source | entity | concept | analysis | comparison
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
tags: []
---

# Page title

Body...

## See Also
- [[related-page]]
```

- Cross-references use `[[page-name]]` (Obsidian compatible)
- File names are kebab-case: `some-topic.md`
- Default content language follows the project; keep proper nouns in their original form

## Operations

### Ingest

Workflow for integrating a new source into the wiki.

1. Verify the source file exists under `raw/`
2. Read the source and discuss the key content with the user
3. Write a `sources/{slug}.md` summary page
4. Update or create related entity/concept pages
5. When new info contradicts existing content, do not delete — keep both side by side (use a `> [!conflict]` callout)
6. Update `index.md`
7. Append an entry to `log.md`

Ingest one source at a time, confirming with the user as you go.

### Query

Workflow for searching the wiki and synthesizing an answer.

1. Read `index.md` to find relevant pages
2. Read those pages and synthesize an answer (always cite sources)
3. Save high-reuse answers under `analyses/` or `comparisons/`
4. Append to `log.md`

### Lint

Wiki health check. Run on user request or periodically.

- Detect contradictions between pages
- Flag stale claims that have been superseded by newer sources
- Find orphan pages with no inbound links
- Identify mentioned-but-uncreated concepts
- Add missing cross-references
- Record results in `log.md`

## Indexing

### index.md

The wiki-wide catalog. Organize by category; each entry is a link plus a one-line summary.

```markdown
# Wiki Index

## Sources
- [Title](sources/slug.md) — one-line summary

## Entities
- [Name](entities/name.md) — one-line description

## Concepts
- [Concept](concepts/name.md) — one-line description

## Analyses
- [Title](analyses/title.md) — one-line description

## Comparisons
- [A vs B](comparisons/a-vs-b.md) — one-line description
```

### log.md

Chronological, append-only record. Use a consistent, grep-friendly format.

```markdown
## [YYYY-MM-DD] ingest | Source title
- source: raw/articles/file.md
- created: sources/slug.md
- modified: entities/x.md, concepts/y.md
- note: anything noteworthy

## [YYYY-MM-DD] query | Question summary
- refs: concepts/a.md, entities/b.md
- result: analyses/answer.md

## [YYYY-MM-DD] lint
- found: 2 orphan pages, 3 missing cross-references
- fixed: entities/x.md, concepts/y.md
```

## Rules

1. **Never modify files under `raw/`.** Original sources are immutable.
2. **Every wiki page must include frontmatter.**
3. **When new information conflicts with existing content, do not delete — keep both side by side.** Mark with a `> [!conflict]` callout.
4. **Keep `index.md` up to date whenever the wiki changes.**
5. **`log.md` is append-only.** Do not edit existing entries.
6. **Use cross-references aggressively.** Connect related pages with `[[]]`.
7. **The user curates; the LLM organizes.** Humans choose sources and direction; the LLM handles summaries, cross-references, and cleanup.
8. **When ingesting sources, proceed step by step with user confirmation.** Never bulk-process automatically.
