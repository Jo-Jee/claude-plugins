# Wiki Plugin — Design

Date: 2026-07-20
Status: design (pending user review)
Branch: worktree-feat+wiki-plugin

## Goal

Migrate the standalone `wiki` skill (currently at `~/Workspace/pp/ai/.claude/skills/wiki`)
into a plugin in the `jojee-tools` marketplace, and rework it around a new usage model:

- The wiki is a **standalone git repository** — no longer a `wiki/` subdirectory nested
  inside a project.
- Scope is **per project**, achieved through Claude Code's already-per-project
  `$CLAUDE_CONFIG_DIR`: a single symlink `$CLAUDE_CONFIG_DIR/wiki` points at the active
  project's standalone wiki repo.
- The wiki must be **visible in every session** (SessionStart hook).
- The **root `CLAUDE.md`** just delegates to the wiki; **all wiki rules live in the
  wiki's own `CLAUDE.md`**.

## Background / current state

- The source skill is Python-CLI-backed (`bin/wiki_tools.py`, stdlib only) with a
  `SKILL.md` router and sub-guides (`init/ingest/query/lint`), a `templates/CLAUDE.md`,
  and a test suite under `tests/`.
- Current path resolution is **git-root based**: `git rev-parse --show-toplevel` →
  `<repo>/wiki` (one wiki per repository). This is what we are moving away from.
- `cmd_init` creates the structure under `<project_root>/wiki/` (a wrapper level we are
  removing).
- The target repo `jojee-tools` is a plugin marketplace; `english-coach` (ships hooks)
  and `statusline` (ships a setup command that edits settings) are structural templates.

## Decisions (from brainstorming)

1. Ship as a **plugin** containing the migrated skill (keep it a *skill*, not slash
   commands — preserves the SKILL.md router, sub-guides, CLI, and tests; minimal rework).
2. **Standalone-repo model, no `wiki/` wrapper**: the wiki repo's root *is* the wiki.
3. **Per-project via `$CLAUDE_CONFIG_DIR`**: a single symlink `$CLAUDE_CONFIG_DIR/wiki`
   → the standalone wiki repo. Because the config dir is already per-project, one symlink
   is inherently per-project. No registry, no filesystem walk-up.
4. **Requirement 2 (root CLAUDE.md)**: `$CLAUDE_CONFIG_DIR/CLAUDE.md` contains only a
   short pointer delegating to the wiki's `CLAUDE.md`. All actual wiki rules — including
   "every document must live in the wiki" — live in the wiki's own `CLAUDE.md`.
5. **Requirement 3 (visibility)**: a SessionStart hook, shipped in the plugin and active
   on install, surfaces the wiki catalog each session.
6. Fold the wiring (symlink + root-CLAUDE.md pointer) into `/wiki init` — no separate
   `/wiki:setup` command.
7. Hook injects the full `index.md` catalog (with a one-line reminder prefix); silent
   when no wiki is linked.
8. Leave this repo's existing `wiki/` in place — extracting existing content into a
   standalone repo is a separate data migration, out of scope here.

## Architecture

### Plugin layout

```
wiki/                              # plugin directory in jojee-tools
├── .claude-plugin/plugin.json     # name, description, version, author
├── README.md
├── hooks/hooks.json               # SessionStart -> scripts/session_context.sh
├── scripts/session_context.sh     # reads $CLAUDE_CONFIG_DIR/wiki, emits index.md
└── skills/wiki/
    ├── SKILL.md                   # router + new path resolution
    ├── init.md ingest.md query.md lint.md
    ├── bin/wiki_tools.py          # + `link` subcommand; init drops wiki/ wrapper
    ├── templates/CLAUDE.md        # single source of truth for wiki rules
    └── tests/                     # updated init tests + new link tests
```

Also: add a `wiki` entry to `.claude-plugin/marketplace.json` and document it in the
root `README.md`.

### Standalone wiki repo structure (post-init)

```
<wiki-repo>/                       # a standalone git repo; its root IS the wiki
├── CLAUDE.md   index.md   log.md
├── raw/{articles,papers,notes,assets}/
├── sources/ entities/ concepts/ analyses/ comparisons/
└── .obsidian/
```

### Path resolution (the core change)

- Wiki path = follow `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/wiki` (a symlink to the
  standalone wiki repo root).
- If the symlink is absent/broken → the skill guides the user to run `/wiki init`.
- Replaces all git-root-based resolution in `SKILL.md`, `init.md`, and any CLI logic
  that assumed the `wiki/` wrapper.

### `/wiki init [target]` — scaffold + link (idempotent)

1. `target` = the standalone wiki repo location (argument, or cwd if already inside it).
2. `wiki_tools.py init <target>` → scaffold the wiki structure **at `<target>` root**
   (no `wiki/` wrapper). Refuse if `<target>` is already a wiki (e.g. `index.md` present).
3. `wiki_tools.py link <target>` → create/replace symlink
   `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/wiki` → `<target>` (absolute path).
4. Ensure `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/CLAUDE.md` contains the pointer block
   (inserted once, between markers, so re-runs don't duplicate):

   ```markdown
   <!-- wiki-plugin:start -->
   ## Wiki
   All project documentation follows the wiki's rules.
   See `$CLAUDE_CONFIG_DIR/wiki/CLAUDE.md`. Every document must live in the wiki.
   <!-- wiki-plugin:end -->
   ```

### Wiki `CLAUDE.md` (template) — single source of truth

- Drop the `wiki/`-nesting language from the "Directory Structure" section (root is the
  wiki now).
- Add an explicit top rule: **all project documents must live in this wiki** (this is the
  rule the root CLAUDE.md delegates to).
- Everything else (page format, ingest/query/lint workflows, indexing, rules) stays.

### SessionStart hook — visibility

- `hooks/hooks.json` registers a `SessionStart` hook running `scripts/session_context.sh`
  (active on install, like english-coach's hooks).
- `session_context.sh`:
  - Resolve `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/wiki`.
  - If a valid symlink/dir → print a one-line reminder ("Project documentation lives in
    the wiki; follow its CLAUDE.md.") followed by the wiki's `index.md` contents, as
    additional session context.
  - If missing/broken → exit 0 silently (no noise in unlinked projects).

### Remaining subcommands

`ingest / query / lint / status` keep their behavior; they simply receive the wiki path
resolved via the symlink instead of via git root. `check-raw`'s git tracking now runs
inside the standalone wiki repo, which fits the new model (the wiki is its own repo).

## CLI changes (`bin/wiki_tools.py`)

- `cmd_init(target)`: scaffold at `<target>` root; remove the
  `os.path.join(project_root, 'wiki')` wrapper. Refuse when `<target>/index.md` exists.
- New `cmd_link(target)`: compute `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/wiki`, remove any
  existing symlink there, create a new absolute symlink to `<target>`. Idempotent.
  (Root-CLAUDE.md pointer editing can live in the CLI too, for testability, or in the
  init.md bash workflow — decide during implementation; prefer CLI for test coverage.)
- All other commands unchanged, but callers pass the symlink-resolved path.

## Testing

- Update `tests/test_init.py` for the no-`wiki/`-wrapper layout.
- Add tests for `cmd_link` (symlink created, replaced idempotently, honors
  `CLAUDE_CONFIG_DIR`) using a temp `CLAUDE_CONFIG_DIR`.
- Add a test for the root-CLAUDE.md pointer insertion (present once, idempotent) if that
  logic lands in the CLI.
- Run the full existing suite to confirm the migration didn't regress ingest/query/lint/
  status/index/frontmatter behavior.

## Open items to verify during build

- **Skill dir env var in a plugin**: the current skill hardcodes `${CLAUDE_SKILL_DIR}`.
  Confirm the correct variable for a plugin-packaged skill (plugins use
  `${CLAUDE_PLUGIN_ROOT}`) and update all path references in `SKILL.md` and the guides.
- **Hook context injection format**: confirm the SessionStart hook's expected stdout /
  JSON shape for adding session context (mirror english-coach's hook implementation).

## Out of scope

- Extracting this repo's existing `wiki/` content into a standalone repo.
- Touching the original skill at `~/Workspace/pp/ai/.claude/skills/wiki` (user removes it
  and relies on the installed plugin once this lands).
