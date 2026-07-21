---
name: wiki
description: Per-project LLM Wiki management — init, ingest, query, lint, status
argument-hint: [init|ingest|query|lint|status] [args...]
allowed-tools: Read Edit Write Grep Glob Bash(python3 *)
---

# Wiki Skill

Manages a per-project LLM Wiki. Based on Karpathy's LLM Wiki pattern.

## Usage

```
/wiki init          — initialize a wiki in the current project
/wiki ingest        — integrate a raw/ source into the wiki
/wiki query <q>     — search the wiki and synthesize an answer
/wiki lint          — wiki health check
/wiki status        — wiki status summary
```

## Setup

Python CLI path: `${CLAUDE_SKILL_DIR}/bin/wiki_tools.py`

Wiki path resolution:
1. Find the git root from cwd: `git rev-parse --show-toplevel`
2. `{git_root}/wiki/` is the wiki path
3. If `wiki/` does not exist → guide the user to run `/wiki init`

## Routing

Use the first argument of `$ARGUMENTS` to determine the subcommand, then read and follow the matching guide:

| Argument | Guide |
|----------|-------|
| `init` | Read `${CLAUDE_SKILL_DIR}/init.md` |
| `ingest` | Read `${CLAUDE_SKILL_DIR}/ingest.md` |
| `query` | Read `${CLAUDE_SKILL_DIR}/query.md` |
| `lint` | Read `${CLAUDE_SKILL_DIR}/lint.md` |
| `status` | Run directly: `python3 ${CLAUDE_SKILL_DIR}/bin/wiki_tools.py status <wiki_path>` |

## Rules

1. Never modify files under `raw/`.
2. Every wiki page must include frontmatter.
3. When new information conflicts with existing content, do not delete — keep both side by side using a `> [!conflict]` callout.
4. Keep `index.md` up to date whenever the wiki changes.
5. `log.md` is append-only.
6. Use cross-references aggressively. Format: `[[page-name]]`.
7. The user curates; the LLM organizes.
8. When ingesting sources, proceed step by step with user confirmation.
