# Wiki Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the standalone `wiki` skill into a `wiki` plugin in the `jojee-tools` marketplace, reworked so the wiki is a standalone repo linked per-project via `$CLAUDE_CONFIG_DIR/wiki` and surfaced in every session.

**Architecture:** A plugin bundling (a) the migrated skill under `skills/wiki/` — Python-CLI-backed, `${CLAUDE_SKILL_DIR}` references kept intact — and (b) a `SessionStart` hook that reads the `$CLAUDE_CONFIG_DIR/wiki` symlink and injects the wiki catalog. `/wiki init` scaffolds a standalone wiki repo (no `wiki/` wrapper), creates the symlink, and drops a delegating pointer into the root `CLAUDE.md`. All wiki rules live in the wiki's own `CLAUDE.md`.

**Tech Stack:** Python 3 (stdlib only), Bash + `jq`, Claude Code plugin manifest/hooks/skills.

## Global Constraints

- Python CLI is **stdlib only** — no third-party imports (matches existing `wiki_tools.py`).
- Config dir is relocatable: always resolve as `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` (shell) / `os.environ.get('CLAUDE_CONFIG_DIR') or ~/.claude` (Python). Never hardcode `~/.claude`.
- Keep `${CLAUDE_SKILL_DIR}` in SKILL.md and guides — it is expanded at skill-load time to `<plugin>/skills/wiki` and works unchanged. Do NOT convert these to `${CLAUDE_PLUGIN_ROOT}`.
- In `hooks.json`, the plugin root is `"${CLAUDE_PLUGIN_ROOT}"` (double-quoted, shell form).
- SessionStart context injection: JSON on stdout `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}`; exit 0 with empty stdout = silent no-op.
- Plugin manifest: `name: "wiki"`, `version: "1.0.0"`, `author: {name:"Jo-Jee", email:"jojee.dev@gmail.com"}`.
- The hook depends on `jq` (already a marketplace-wide dependency).
- Python tests use `unittest`, run from the tests dir. Bash tests are standalone scripts.
- Do NOT modify the original skill at `~/Workspace/pp/ai/.claude/skills/wiki`. Do NOT extract this repo's existing `wiki/` content.

---

### Task 1: Scaffold the plugin and copy the skill (baseline green)

**Files:**
- Create: `wiki/.claude-plugin/plugin.json`
- Create: `wiki/skills/wiki/…` (copied from the source skill)

**Interfaces:**
- Produces: the plugin directory `wiki/` with a working, unmodified copy of the skill's Python CLI + tests, so subsequent tasks modify a known-green baseline.

- [ ] **Step 1: Copy the source skill into the plugin and strip caches**

```bash
cd "$(git rev-parse --show-toplevel)"
mkdir -p wiki/skills wiki/.claude-plugin
cp -R /Users/george/Workspace/pp/ai/.claude/skills/wiki wiki/skills/wiki
find wiki/skills/wiki -name '__pycache__' -type d -prune -exec rm -rf {} +
find wiki/skills/wiki -name '*.pyc' -delete
```

- [ ] **Step 2: Write the plugin manifest**

Create `wiki/.claude-plugin/plugin.json`:

```json
{
  "name": "wiki",
  "description": "Per-project LLM Wiki: a standalone wiki repo linked via $CLAUDE_CONFIG_DIR/wiki and surfaced every session; init/ingest/query/lint/status.",
  "version": "1.0.0",
  "author": { "name": "Jo-Jee", "email": "jojee.dev@gmail.com" }
}
```

- [ ] **Step 3: Run the copied test suite to confirm a green baseline**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest -v`
Expected: all tests PASS (this is the pre-migration baseline).

- [ ] **Step 4: Commit**

```bash
git add wiki/.claude-plugin/plugin.json wiki/skills/wiki
git commit -m "feat(wiki): scaffold plugin and copy skill (baseline)"
```

---

### Task 2: Drop the `wiki/` wrapper in `cmd_init`

**Files:**
- Modify: `wiki/skills/wiki/bin/wiki_tools.py` (`cmd_init`, argparse `init` parser, dispatch)
- Test: `wiki/skills/wiki/tests/test_init.py`

**Interfaces:**
- Produces: `cmd_init(wiki_path, template_dir=None)` — scaffolds the wiki structure **directly at `wiki_path`** (the standalone repo root). Exits 2 if `wiki_path/index.md` already exists.

- [ ] **Step 1: Rewrite the init tests for the no-wrapper layout**

Replace the body of `wiki/skills/wiki/tests/test_init.py` with:

```python
import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from helpers import WikiTestCase
from wiki_tools import cmd_init


class TestInit(WikiTestCase, unittest.TestCase):
    def test_creates_directory_structure(self):
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        wiki = self.wiki_path
        self.assertTrue(os.path.isdir(wiki))
        for d in ('raw/notes', 'raw/articles', 'raw/papers', 'raw/assets',
                  'sources', 'entities', 'concepts', 'analyses', 'comparisons'):
            self.assertTrue(os.path.isdir(os.path.join(wiki, d)), d)

    def test_creates_index_and_log(self):
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        wiki = self.wiki_path
        self.assertTrue(os.path.isfile(os.path.join(wiki, 'index.md')))
        self.assertTrue(os.path.isfile(os.path.join(wiki, 'log.md')))
        self.assertIn('# Wiki Index', self.read_file(wiki, 'index.md'))
        self.assertIn('init', self.read_file(wiki, 'log.md'))

    def test_copies_claude_md(self):
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        self.assertTrue(os.path.isfile(os.path.join(self.wiki_path, 'CLAUDE.md')))

    def test_creates_obsidian_config(self):
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        obsidian = os.path.join(self.wiki_path, '.obsidian')
        self.assertTrue(os.path.isfile(os.path.join(obsidian, 'app.json')))

    def test_scaffolds_into_existing_empty_dir(self):
        os.makedirs(self.wiki_path)  # dir exists but no index.md yet
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        self.assertTrue(os.path.isfile(os.path.join(self.wiki_path, 'index.md')))

    def test_fails_if_already_a_wiki(self):
        os.makedirs(self.wiki_path)
        self.write_file(os.path.join(self.wiki_path, 'index.md'), '# Wiki Index\n')
        with self.assertRaises(SystemExit) as cm:
            cmd_init(self.wiki_path, template_dir=self._template_dir())
        self.assertEqual(cm.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest test_init -v`
Expected: FAIL — old `cmd_init` still creates a `wiki/` subdir, so `index.md` etc. are not at `wiki_path` root; `test_fails_if_already_a_wiki` fails because the old guard checks for the `wiki/` subdir, not `index.md`.

- [ ] **Step 3: Rewrite `cmd_init` to scaffold at the target root**

In `wiki/skills/wiki/bin/wiki_tools.py`, replace the `cmd_init` function with:

```python
def cmd_init(wiki_path, template_dir=None):
    """Scaffold the wiki structure directly at wiki_path (standalone repo root)."""
    index_path = os.path.join(wiki_path, 'index.md')
    if os.path.exists(index_path):
        print("Error: already a wiki (index.md exists) at {}".format(wiki_path), file=sys.stderr)
        sys.exit(2)

    # Create directories
    for d in WIKI_DIRS:
        os.makedirs(os.path.join(wiki_path, d), exist_ok=True)

    # Copy CLAUDE.md template
    if template_dir is None:
        template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
    src = os.path.join(template_dir, 'CLAUDE.md')
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(wiki_path, 'CLAUDE.md'))

    # Create index.md
    index_content = (
        "# Wiki Index\n\n"
        "## Sources\n\n"
        "## Entities\n\n"
        "## Concepts\n\n"
        "## Analyses\n\n"
        "## Comparisons\n"
    )
    _write(index_path, index_content)

    # Create log.md with init entry
    today = date.today().isoformat()
    log_content = "## [{date}] init | Wiki initialized\n- note: wiki initialization complete\n".format(date=today)
    _write(os.path.join(wiki_path, 'log.md'), log_content)

    # Create .obsidian config
    obsidian = os.path.join(wiki_path, '.obsidian')
    os.makedirs(obsidian, exist_ok=True)
    for name, content in OBSIDIAN_DEFAULTS.items():
        _write(os.path.join(obsidian, name), json.dumps(content, indent=2) + '\n')

    print("Wiki initialized at {}".format(wiki_path))
```

- [ ] **Step 4: Update the argparse parser and dispatch for `init`**

In `main()`, change the `init` parser's argument name and the dispatch call. Find:

```python
    p_init = sub.add_parser('init', help='Initialize wiki in project')
    p_init.add_argument('project_root', help='Project root directory')
```
Replace with:
```python
    p_init = sub.add_parser('init', help='Initialize a standalone wiki repo at TARGET')
    p_init.add_argument('target', help='Wiki repo root directory (the wiki lives here directly)')
```
Find:
```python
    if args.command == 'init':
        cmd_init(args.project_root)
```
Replace with:
```python
    if args.command == 'init':
        cmd_init(args.target)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest test_init -v`
Expected: PASS (all 6 tests).

- [ ] **Step 6: Commit**

```bash
git add wiki/skills/wiki/bin/wiki_tools.py wiki/skills/wiki/tests/test_init.py
git commit -m "feat(wiki): scaffold wiki at repo root, drop wiki/ wrapper"
```

---

### Task 3: Add `cmd_link` — symlink `$CLAUDE_CONFIG_DIR/wiki` → wiki repo

**Files:**
- Modify: `wiki/skills/wiki/bin/wiki_tools.py` (new `_config_dir`, `cmd_link`, parser, dispatch)
- Test: `wiki/skills/wiki/tests/test_link.py` (create)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `_config_dir() -> str` (returns `$CLAUDE_CONFIG_DIR` or `~/.claude`). `cmd_link(target)` — creates/replaces the symlink `<config_dir>/wiki -> abspath(target)`; refuses if the path exists as a non-symlink; exits 2 if target is not a directory.

- [ ] **Step 1: Write the failing test**

Create `wiki/skills/wiki/tests/test_link.py`:

```python
import unittest
import os
import sys
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from wiki_tools import cmd_link, _config_dir


class TestLink(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config = os.path.join(self.tmp, 'config')
        os.makedirs(self.config)
        self.target = os.path.join(self.tmp, 'mywiki')
        os.makedirs(self.target)
        self._old_env = os.environ.get('CLAUDE_CONFIG_DIR')
        os.environ['CLAUDE_CONFIG_DIR'] = self.config

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop('CLAUDE_CONFIG_DIR', None)
        else:
            os.environ['CLAUDE_CONFIG_DIR'] = self._old_env
        shutil.rmtree(self.tmp)

    def test_config_dir_honors_env(self):
        self.assertEqual(_config_dir(), self.config)

    def test_creates_symlink_to_target(self):
        cmd_link(self.target)
        link = os.path.join(self.config, 'wiki')
        self.assertTrue(os.path.islink(link))
        self.assertEqual(os.path.realpath(link), os.path.realpath(self.target))

    def test_idempotent_replaces_existing_symlink(self):
        cmd_link(self.target)
        other = os.path.join(self.tmp, 'other')
        os.makedirs(other)
        cmd_link(other)  # should replace, not error
        link = os.path.join(self.config, 'wiki')
        self.assertEqual(os.path.realpath(link), os.path.realpath(other))

    def test_refuses_non_symlink_at_link_path(self):
        os.makedirs(os.path.join(self.config, 'wiki'))  # real dir squats the path
        with self.assertRaises(SystemExit) as cm:
            cmd_link(self.target)
        self.assertEqual(cm.exception.code, 2)

    def test_rejects_nondir_target(self):
        with self.assertRaises(SystemExit) as cm:
            cmd_link(os.path.join(self.tmp, 'does-not-exist'))
        self.assertEqual(cm.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest test_link -v`
Expected: FAIL — `ImportError: cannot import name 'cmd_link'` (and `_config_dir`).

- [ ] **Step 3: Implement `_config_dir` and `cmd_link`**

In `wiki/skills/wiki/bin/wiki_tools.py`, add after the `_write` helper (near line 117):

```python
def _config_dir():
    """Claude Code config dir; relocatable via CLAUDE_CONFIG_DIR (default ~/.claude)."""
    return os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')


def cmd_link(target):
    """Symlink <config_dir>/wiki -> abspath(target). Idempotent; refuses non-symlink."""
    target_abs = os.path.abspath(target)
    if not os.path.isdir(target_abs):
        print("Error: target is not a directory: {}".format(target_abs), file=sys.stderr)
        sys.exit(2)
    config_dir = _config_dir()
    os.makedirs(config_dir, exist_ok=True)
    link_path = os.path.join(config_dir, 'wiki')
    if os.path.islink(link_path):
        os.unlink(link_path)
    elif os.path.exists(link_path):
        print("Error: {} exists and is not a symlink; refusing to replace".format(link_path), file=sys.stderr)
        sys.exit(2)
    os.symlink(target_abs, link_path)
    print("Linked {} -> {}".format(link_path, target_abs))
```

- [ ] **Step 4: Add the `link` subcommand parser and dispatch**

In `main()`, after the `init` parser block, add:

```python
    # link
    p_link = sub.add_parser('link', help='Symlink $CLAUDE_CONFIG_DIR/wiki to a wiki repo')
    p_link.add_argument('target', help='Wiki repo root directory to link')
```
In the dispatch chain, after the `init` branch, add:
```python
    elif args.command == 'link':
        cmd_link(args.target)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest test_link -v`
Expected: PASS (all 5 tests).

- [ ] **Step 6: Commit**

```bash
git add wiki/skills/wiki/bin/wiki_tools.py wiki/skills/wiki/tests/test_link.py
git commit -m "feat(wiki): add link command for \$CLAUDE_CONFIG_DIR/wiki symlink"
```

---

### Task 4: Add `cmd_ensure_root_pointer` — delegating block in root CLAUDE.md

**Files:**
- Modify: `wiki/skills/wiki/bin/wiki_tools.py` (constants, `cmd_ensure_root_pointer`, parser, dispatch)
- Test: `wiki/skills/wiki/tests/test_root_pointer.py` (create)

**Interfaces:**
- Consumes: `_config_dir()` from Task 3.
- Produces: `cmd_ensure_root_pointer()` — ensures `<config_dir>/CLAUDE.md` contains exactly one pointer block between `<!-- wiki-plugin:start -->` and `<!-- wiki-plugin:end -->`, preserving any surrounding content. Idempotent.

- [ ] **Step 1: Write the failing test**

Create `wiki/skills/wiki/tests/test_root_pointer.py`:

```python
import unittest
import os
import sys
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from wiki_tools import cmd_ensure_root_pointer, POINTER_START, POINTER_END


class TestRootPointer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config = os.path.join(self.tmp, 'config')
        os.makedirs(self.config)
        self._old = os.environ.get('CLAUDE_CONFIG_DIR')
        os.environ['CLAUDE_CONFIG_DIR'] = self.config
        self.claude_md = os.path.join(self.config, 'CLAUDE.md')

    def tearDown(self):
        if self._old is None:
            os.environ.pop('CLAUDE_CONFIG_DIR', None)
        else:
            os.environ['CLAUDE_CONFIG_DIR'] = self._old
        shutil.rmtree(self.tmp)

    def _read(self):
        with open(self.claude_md, encoding='utf-8') as f:
            return f.read()

    def test_creates_pointer_when_no_file(self):
        cmd_ensure_root_pointer()
        text = self._read()
        self.assertIn(POINTER_START, text)
        self.assertIn(POINTER_END, text)
        self.assertIn('must live in the wiki', text)

    def test_idempotent_single_block(self):
        cmd_ensure_root_pointer()
        cmd_ensure_root_pointer()
        text = self._read()
        self.assertEqual(text.count(POINTER_START), 1)
        self.assertEqual(text.count(POINTER_END), 1)

    def test_preserves_existing_content(self):
        with open(self.claude_md, 'w', encoding='utf-8') as f:
            f.write('# My global rules\n\nBe concise.\n')
        cmd_ensure_root_pointer()
        text = self._read()
        self.assertIn('Be concise.', text)
        self.assertIn(POINTER_START, text)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest test_root_pointer -v`
Expected: FAIL — `ImportError: cannot import name 'cmd_ensure_root_pointer'`.

- [ ] **Step 3: Implement the pointer logic**

In `wiki/skills/wiki/bin/wiki_tools.py`, add after `cmd_link` (from Task 3):

```python
POINTER_START = '<!-- wiki-plugin:start -->'
POINTER_END = '<!-- wiki-plugin:end -->'
POINTER_BLOCK = (
    POINTER_START + '\n'
    '## Wiki\n'
    "All project documentation follows the wiki's rules.\n"
    'See `$CLAUDE_CONFIG_DIR/wiki/CLAUDE.md`. Every document must live in the wiki.\n'
    + POINTER_END + '\n'
)


def cmd_ensure_root_pointer():
    """Ensure exactly one wiki pointer block in <config_dir>/CLAUDE.md (idempotent)."""
    config_dir = _config_dir()
    os.makedirs(config_dir, exist_ok=True)
    path = os.path.join(config_dir, 'CLAUDE.md')
    existing = ''
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            existing = f.read()

    if POINTER_START in existing and POINTER_END in existing:
        pre = existing.split(POINTER_START)[0]
        post = existing.split(POINTER_END, 1)[1]
        new = pre + POINTER_BLOCK + post
    elif existing == '':
        new = POINTER_BLOCK
    else:
        sep = '' if existing.endswith('\n') else '\n'
        new = existing + sep + '\n' + POINTER_BLOCK

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new)
    print("Root pointer ensured in {}".format(path))
```

- [ ] **Step 4: Add the `ensure-root-pointer` subcommand parser and dispatch**

In `main()`, after the `link` parser block, add:

```python
    # ensure-root-pointer
    sub.add_parser('ensure-root-pointer',
                   help='Ensure the wiki pointer block in $CLAUDE_CONFIG_DIR/CLAUDE.md')
```
In the dispatch chain, after the `link` branch, add:
```python
    elif args.command == 'ensure-root-pointer':
        cmd_ensure_root_pointer()
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest test_root_pointer -v`
Expected: PASS (all 3 tests).

- [ ] **Step 6: Run the full Python suite for regressions**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest -v`
Expected: PASS (init, link, root_pointer, create_page, frontmatter, lint, log_append, sync_index, utils).

- [ ] **Step 7: Commit**

```bash
git add wiki/skills/wiki/bin/wiki_tools.py wiki/skills/wiki/tests/test_root_pointer.py
git commit -m "feat(wiki): add ensure-root-pointer for delegating root CLAUDE.md block"
```

---

### Task 5: Rework path resolution in SKILL.md and guides

**Files:**
- Modify: `wiki/skills/wiki/SKILL.md`
- Modify: `wiki/skills/wiki/init.md`
- Modify: `wiki/skills/wiki/query.md`

**Interfaces:**
- Consumes: `wiki_tools.py` subcommands `init`, `link`, `ensure-root-pointer` (Tasks 2–4).
- Produces: skill instructions that resolve the wiki via the `$CLAUDE_CONFIG_DIR/wiki` symlink and wire everything during `/wiki init`. `${CLAUDE_SKILL_DIR}` references are unchanged.

- [ ] **Step 1: Replace the "Setup" section of `SKILL.md`**

In `wiki/skills/wiki/SKILL.md`, replace the whole `## Setup` section (the "Wiki path resolution" list that uses `git rev-parse --show-toplevel`) with:

```markdown
## Setup

Python CLI path: `${CLAUDE_SKILL_DIR}/bin/wiki_tools.py`

Wiki path resolution:
1. The wiki is whatever `$CLAUDE_CONFIG_DIR/wiki` points to (default `~/.claude/wiki`):
   ```bash
   WIKI="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/wiki"
   ```
2. If `$WIKI` does not exist or is not a directory → the current project has no wiki
   linked. Guide the user to run `/wiki init` (see the init guide).
3. Otherwise use `$WIKI` as `<wiki_path>` for every subcommand below.
```

- [ ] **Step 2: Verify no git-root resolution remains in SKILL.md**

Run: `grep -n "rev-parse\|git_root\|git root" wiki/skills/wiki/SKILL.md`
Expected: no output (exit status 1 / empty).

- [ ] **Step 3: Rewrite `init.md` to scaffold + link + write the pointer**

Replace the `## Workflow` section of `wiki/skills/wiki/init.md` with:

```markdown
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
```

- [ ] **Step 4: Fix the `wiki/index.md` reference in `query.md`**

In `wiki/skills/wiki/query.md`, find:
```markdown
Read `wiki/index.md` and find pages relevant to the question.
```
Replace with:
```markdown
Read the wiki's `index.md` (`$WIKI/index.md`, i.e. `<wiki_path>/index.md`) and find pages relevant to the question.
```

- [ ] **Step 5: Verify the guides reference the new subcommands**

Run: `grep -n "link\|ensure-root-pointer" wiki/skills/wiki/init.md`
Expected: lines showing both `link` and `ensure-root-pointer` invocations.

- [ ] **Step 6: Commit**

```bash
git add wiki/skills/wiki/SKILL.md wiki/skills/wiki/init.md wiki/skills/wiki/query.md
git commit -m "docs(wiki): resolve wiki via \$CLAUDE_CONFIG_DIR/wiki; init links + pointers"
```

---

### Task 6: Update the wiki template CLAUDE.md (single source of truth)

**Files:**
- Modify: `wiki/skills/wiki/templates/CLAUDE.md`

**Interfaces:**
- Produces: the wiki's own `CLAUDE.md` (copied by `init`) — now describes the standalone-repo layout (no `wiki/` wrapper) and carries the top rule that all project documents must live in the wiki. This is what the root pointer delegates to.

- [ ] **Step 1: Rewrite the "Directory Structure" block (drop the `wiki/` wrapper)**

In `wiki/skills/wiki/templates/CLAUDE.md`, replace the fenced directory tree under `## Directory Structure` with:

```markdown
```
./                        # this repo's root IS the wiki
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
```

- [ ] **Step 2: Add the top rule that all documents live in the wiki**

In `wiki/skills/wiki/templates/CLAUDE.md`, in the `## Rules` section, insert as the new first list item (renumbering is not required — the list is markdown-ordinal):

```markdown
1. **All project documentation lives in this wiki.** Notes, designs, requirements, and
   references belong here — never scattered across the codebase. Save new raw material
   under `raw/notes/` (or the appropriate `raw/` subdir).
```

Then update the intro paragraph under `## Project` to append:

```markdown
This wiki is a standalone repository linked into the project's Claude config dir at
`$CLAUDE_CONFIG_DIR/wiki`, so its catalog is visible in every session.
```

- [ ] **Step 3: Verify the changes**

Run: `grep -n "root IS the wiki\|All project documentation lives in this wiki" wiki/skills/wiki/templates/CLAUDE.md`
Expected: both lines present.

Run: `grep -n "wiki/" wiki/skills/wiki/templates/CLAUDE.md`
Expected: no `wiki/`-wrapper paths in the directory tree (references to subdirs like `raw/` are fine; there should be no leading `wiki/` prefix on structure paths).

- [ ] **Step 4: Commit**

```bash
git add wiki/skills/wiki/templates/CLAUDE.md
git commit -m "docs(wiki): template describes standalone repo + docs-live-here rule"
```

---

### Task 7: SessionStart hook — surface the wiki catalog every session

**Files:**
- Create: `wiki/hooks/hooks.json`
- Create: `wiki/scripts/session_context.sh`
- Test: `wiki/tests/test-session-context.sh` (create)

**Interfaces:**
- Consumes: the `$CLAUDE_CONFIG_DIR/wiki` symlink created by `cmd_link` (Task 3).
- Produces: a `SessionStart` hook that prints `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"<reminder + index.md>"}}` when a wiki is linked, and nothing when it isn't.

- [ ] **Step 1: Write the failing bash test**

Create `wiki/tests/test-session-context.sh`:

```bash
#!/usr/bin/env bash
# Tests for session_context.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../scripts/session_context.sh"
fail=0
assert(){ if [ "$2" -ne 0 ]; then echo "FAIL: $1"; fail=1; else echo "ok: $1"; fi; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export CLAUDE_CONFIG_DIR="$TMP/config"
mkdir -p "$CLAUDE_CONFIG_DIR"

# --- Case 1: no wiki linked -> silent no-op ---
out="$(bash "$SCRIPT")"; rc=$?
[ "$rc" -eq 0 ]; assert "exit 0 when unlinked" $?
[ -z "$out" ]; assert "no stdout when unlinked" $?

# --- Case 2: linked wiki with index -> JSON context ---
WIKIREPO="$TMP/mywiki"; mkdir -p "$WIKIREPO"
printf '# Wiki Index\n\n## Concepts\n- [Foo](concepts/foo.md) — bar\n' > "$WIKIREPO/index.md"
ln -s "$WIKIREPO" "$CLAUDE_CONFIG_DIR/wiki"
out="$(bash "$SCRIPT")"; rc=$?
[ "$rc" -eq 0 ]; assert "exit 0 when linked" $?
printf '%s' "$out" | jq -e '.hookSpecificOutput.hookEventName=="SessionStart"' >/dev/null 2>&1; assert "hookEventName set" $?
printf '%s' "$out" | jq -e '.hookSpecificOutput.additionalContext | contains("Wiki Index")' >/dev/null 2>&1; assert "index content included" $?
printf '%s' "$out" | jq -e '.hookSpecificOutput.additionalContext | contains("must live")' >/dev/null 2>&1; assert "reminder included" $?

# --- Case 3: symlink present but index missing -> silent ---
rm "$CLAUDE_CONFIG_DIR/wiki"; EMPTY="$TMP/empty"; mkdir -p "$EMPTY"
ln -s "$EMPTY" "$CLAUDE_CONFIG_DIR/wiki"
out="$(bash "$SCRIPT")"; rc=$?
[ "$rc" -eq 0 ] && [ -z "$out" ]; assert "silent when index.md missing" $?

[ "$fail" -eq 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash wiki/tests/test-session-context.sh`
Expected: FAIL — the script does not exist yet (`No such file or directory`), so assertions fail.

- [ ] **Step 3: Write the hook script**

Create `wiki/scripts/session_context.sh`:

```bash
#!/usr/bin/env bash
# SessionStart hook: surface the linked project wiki's catalog.
# Reads the $CLAUDE_CONFIG_DIR/wiki symlink and prints JSON with additionalContext.
# Silent (exit 0, no stdout) when no wiki is linked or the catalog is missing.
set -u

CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
WIKI="$CONFIG_DIR/wiki"
INDEX="$WIKI/index.md"

# No linked wiki (missing / broken symlink) or no catalog -> silent no-op.
[ -e "$WIKI" ] || exit 0
[ -f "$INDEX" ] || exit 0

CTX="$(printf 'Project documentation lives in the wiki (%s). Follow its CLAUDE.md; every document must live there.\n\n%s' \
  "$WIKI" "$(cat "$INDEX")")"

jq -n --arg ctx "$CTX" \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
```

Then make it executable:
```bash
chmod +x wiki/scripts/session_context.sh
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `bash wiki/tests/test-session-context.sh`
Expected: `ALL PASS`.

- [ ] **Step 5: Register the hook**

Create `wiki/hooks/hooks.json`:

```json
{
  "description": "Surfaces the linked project wiki's catalog at the start of every session.",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/session_context.sh", "timeout": 10 }
        ]
      },
      {
        "matcher": "resume",
        "hooks": [
          { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/session_context.sh", "timeout": 10 }
        ]
      },
      {
        "matcher": "clear",
        "hooks": [
          { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/session_context.sh", "timeout": 10 }
        ]
      }
    ]
  }
}
```

- [ ] **Step 6: Validate the hook JSON**

Run: `python3 -c "import json; json.load(open('wiki/hooks/hooks.json')); print('valid')"`
Expected: `valid`.

- [ ] **Step 7: Commit**

```bash
git add wiki/hooks/hooks.json wiki/scripts/session_context.sh wiki/tests/test-session-context.sh
git commit -m "feat(wiki): SessionStart hook surfaces linked wiki catalog"
```

---

### Task 8: Register in the marketplace and document

**Files:**
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: the `wiki/` plugin directory (Tasks 1–7).
- Produces: a discoverable, installable `wiki` plugin entry and user-facing docs.

- [ ] **Step 1: Add the marketplace entry**

In `.claude-plugin/marketplace.json`, add to the `plugins` array (after the `statusline` entry):

```json
    {
      "name": "wiki",
      "source": "./wiki",
      "category": "productivity",
      "description": "Per-project LLM Wiki: a standalone wiki repo linked via $CLAUDE_CONFIG_DIR/wiki and surfaced in every session; init/ingest/query/lint/status."
    }
```

- [ ] **Step 2: Validate marketplace JSON**

Run: `python3 -c "import json; d=json.load(open('.claude-plugin/marketplace.json')); print([p['name'] for p in d['plugins']])"`
Expected: `['english-coach', 'statusline', 'wiki']`.

- [ ] **Step 3: Document the plugin in README.md**

In `README.md`, add a new section under `## Plugins` (after the statusline section):

```markdown
### wiki
A per-project LLM Wiki (Karpathy's LLM-Wiki pattern) managed as a **standalone repo**.
- `/wiki init [path]` — scaffold a wiki repo, link it at `$CLAUDE_CONFIG_DIR/wiki`, and
  add a delegating pointer to your root `CLAUDE.md`.
- `/wiki ingest` — integrate a `raw/` source into wiki pages (subagent-driven).
- `/wiki query <q>` — search the wiki and synthesize a cited answer.
- `/wiki lint` — structural + semantic health check.
- `/wiki status` — page counts, last activity, lint summary.

A `SessionStart` hook injects the linked wiki's `index.md` into every session, so its
catalog is always visible. All wiki rules live in the wiki's own `CLAUDE.md`; the root
`CLAUDE.md` just delegates to it.

**Requires:** `python3` and `jq` on `PATH`.
```

Also update the `## Install` section to add:
```markdown
/plugin install wiki@jojee-tools
```

- [ ] **Step 4: Run the entire test surface one more time**

Run: `cd wiki/skills/wiki/tests && python3 -m unittest -v && cd - && bash wiki/tests/test-session-context.sh`
Expected: Python suite PASS + `ALL PASS` for the hook test.

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/marketplace.json README.md
git commit -m "docs(wiki): register plugin in marketplace and README"
```

---

## Manual verification (after all tasks)

Drive the real feature end-to-end in a throwaway location (does not touch your real config):

```bash
export CLAUDE_CONFIG_DIR="$(mktemp -d)/config"
TARGET="$(mktemp -d)/mywiki"; mkdir -p "$TARGET"
python3 wiki/skills/wiki/bin/wiki_tools.py init "$TARGET"
python3 wiki/skills/wiki/bin/wiki_tools.py link "$TARGET"
python3 wiki/skills/wiki/bin/wiki_tools.py ensure-root-pointer
ls -la "$CLAUDE_CONFIG_DIR/wiki"            # symlink -> $TARGET
cat "$CLAUDE_CONFIG_DIR/CLAUDE.md"          # pointer block present
CLAUDE_PLUGIN_ROOT="$PWD/wiki" bash wiki/scripts/session_context.sh | jq .
python3 wiki/skills/wiki/bin/wiki_tools.py status "$TARGET"
unset CLAUDE_CONFIG_DIR
```

Expected: symlink resolves to `$TARGET`; root `CLAUDE.md` has the pointer block; the hook emits valid JSON whose `additionalContext` contains the reminder + `# Wiki Index`; `status` prints the JSON summary.
