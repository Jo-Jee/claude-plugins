"""wiki_tools.py — Wiki management CLI. stdlib only."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date

# ── Type → Directory mapping ─────────────────────────────────────────────

TYPE_DIR_MAP = {
    'source': 'sources',
    'entity': 'entities',
    'concept': 'concepts',
    'analysis': 'analyses',
    'comparison': 'comparisons',
}

VALID_TYPES = set(TYPE_DIR_MAP.keys())

WIKI_DIRS = [
    'raw/articles', 'raw/papers', 'raw/notes', 'raw/assets',
    'sources', 'entities', 'concepts', 'analyses', 'comparisons',
]

REQUIRED_FM_FIELDS = ['title', 'type', 'created', 'updated', 'sources', 'tags']

# ── Frontmatter parser (no PyYAML) ───────────────────────────────────────

def parse_frontmatter(text):
    """Parse YAML frontmatter from markdown text.

    Returns (dict, str) — frontmatter dict and body string.
    If no frontmatter, returns ({}, full_text).
    """
    text = text.replace('\r\n', '\n')
    if not text.startswith('---\n'):
        return {}, text
    end = text.find('\n---\n', 4)
    if end == -1:
        if text.endswith('\n---'):
            end = len(text) - 4
            raw = text[4:end]
            fm = {}
            for line in raw.split('\n'):
                line = line.strip()
                if not line or ':' not in line:
                    continue
                key, val = line.split(':', 1)
                fm[key.strip()] = _parse_yaml_value(val.strip())
            return fm, ''
        return {}, text
    raw = text[4:end]
    body = text[end + 5:]  # skip \n---\n
    fm = {}
    for line in raw.split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue
        key, val = line.split(':', 1)
        key = key.strip()
        val = val.strip()
        fm[key] = _parse_yaml_value(val)
    return fm, body


def _parse_yaml_value(val):
    """Parse a simple YAML value: string, list, or bare value."""
    if val == '[]':
        return []
    if val.startswith('[') and val.endswith(']'):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(item.strip()) for item in inner.split(',')]
    return _strip_quotes(val)


def _strip_quotes(val):
    """Strip surrounding quotes from a YAML value."""
    if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
        return val[1:-1]
    return val


def render_frontmatter(fm, body):
    """Render frontmatter dict + body into markdown text."""
    lines = ['---']
    for key in REQUIRED_FM_FIELDS:
        if key in fm:
            lines.append('{}: {}'.format(key, _render_yaml_value(fm[key])))
    # extra keys not in REQUIRED_FM_FIELDS
    for key, val in fm.items():
        if key not in REQUIRED_FM_FIELDS:
            lines.append('{}: {}'.format(key, _render_yaml_value(val)))
    lines.append('---')
    return '\n'.join(lines) + '\n' + body


def _render_yaml_value(val):
    """Render a value back to YAML-like string."""
    if isinstance(val, list):
        if not val:
            return '[]'
        return '[{}]'.format(', '.join(str(v) for v in val))
    return str(val)


# ── Helper ───────────────────────────────────────────────────────────────

def _write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


# ── Config-dir linking ───────────────────────────────────────────────────

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


# ── Obsidian defaults ───────────────────────────────────────────────────

OBSIDIAN_DEFAULTS = {
    'app.json': {"livePreview": True, "showFrontmatter": False},
    'appearance.json': {"baseFontSize": 16},
    'core-plugins.json': ["file-explorer", "global-search", "graph", "backlink", "tag-pane", "page-preview"],
    'graph.json': {"collapse-filter": False, "search": "", "showTags": True, "showAttachments": False},
    'workspace.json': {},
}

# ── Commands ────────────────────────────────────────────────────────────


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


def cmd_create_page(wiki_path, page_type, slug, title='', sources=None, tags=None):
    """Create a new wiki page with frontmatter skeleton."""
    if page_type not in VALID_TYPES:
        print("Error: invalid type '{}'. Must be one of: {}".format(
            page_type, ', '.join(sorted(VALID_TYPES))), file=sys.stderr)
        sys.exit(2)

    dir_name = TYPE_DIR_MAP[page_type]
    page_dir = os.path.join(wiki_path, dir_name)
    page_file = os.path.join(page_dir, '{}.md'.format(slug))

    if os.path.exists(page_file):
        print("Error: file already exists: {}".format(page_file), file=sys.stderr)
        sys.exit(2)

    os.makedirs(page_dir, exist_ok=True)
    today = date.today().isoformat()
    fm = {
        'title': title or slug,
        'type': page_type,
        'created': today,
        'updated': today,
        'sources': sources or [],
        'tags': tags or [],
    }
    body = "\n# {}\n\n\n\n## See Also\n- \n".format(fm['title'])
    _write(page_file, render_frontmatter(fm, body))
    print("Created: {}".format(page_file))


def cmd_update_frontmatter(file_path, updated=None, add_source=None, add_tag=None):
    """Update frontmatter fields of an existing page."""
    if not os.path.isfile(file_path):
        print("Error: file not found: {}".format(file_path), file=sys.stderr)
        sys.exit(2)

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    fm, body = parse_frontmatter(text)
    if not fm:
        print("Error: no frontmatter in {}".format(file_path), file=sys.stderr)
        sys.exit(2)

    if updated == 'today':
        updated = date.today().isoformat()
    if updated:
        fm['updated'] = updated

    if add_source:
        sources = fm.get('sources', [])
        if isinstance(sources, str):
            sources = [sources] if sources else []
        if add_source not in sources:
            sources.append(add_source)
        fm['sources'] = sources

    if add_tag:
        tags = fm.get('tags', [])
        if isinstance(tags, str):
            tags = [tags] if tags else []
        if add_tag not in tags:
            tags.append(add_tag)
        fm['tags'] = tags

    _write(file_path, render_frontmatter(fm, body))
    print("Updated: {}".format(file_path))


# ── sync-index helpers ─────────────────────────────────────────────────

SECTION_MAP = {
    'sources': '## Sources',
    'entities': '## Entities',
    'concepts': '## Concepts',
    'analyses': '## Analyses',
    'comparisons': '## Comparisons',
}


def _type_from_path(page_path):
    """Extract type directory from page path like 'entities/foo.md'."""
    return page_path.split('/')[0]


def _section_header(type_dir):
    return SECTION_MAP.get(type_dir, '## ' + type_dir.title())


def _upsert_index_entry(content, section, page_path, entry):
    """Insert or replace an entry in the correct section, sorted alphabetically."""
    lines = content.split('\n')
    # Find section boundaries
    section_start = None
    section_end = None
    for i, line in enumerate(lines):
        if line.strip() == section:
            section_start = i
        elif section_start is not None and line.startswith('## '):
            section_end = i
            break
    if section_start is None:
        # Section not found — append
        lines.append('')
        lines.append(section)
        lines.append(entry)
        return '\n'.join(lines)

    if section_end is None:
        section_end = len(lines)

    # Remove existing entry for this page_path
    filtered = []
    for i in range(len(lines)):
        if section_start < i < section_end and page_path in lines[i]:
            continue
        filtered.append(lines[i])

    # Recalculate section boundaries after removal
    lines = filtered
    for i, line in enumerate(lines):
        if line.strip() == section:
            section_start = i
            break
    section_end = None
    for i in range(section_start + 1, len(lines)):
        if lines[i].startswith('## '):
            section_end = i
            break
    if section_end is None:
        section_end = len(lines)

    # Collect existing entries in section and add new one
    entries = []
    for i in range(section_start + 1, section_end):
        if lines[i].startswith('- ['):
            entries.append(lines[i])

    entries.append(entry)
    entries.sort(key=lambda e: e.lower())

    # Rebuild section
    new_lines = lines[:section_start + 1]
    new_lines.append('')  # blank line after header
    new_lines.extend(entries)
    new_lines.append('')  # blank line before next section
    # Skip old section content, add rest
    new_lines.extend(lines[section_end:])

    return '\n'.join(new_lines)


def _remove_index_entry(content, page_path):
    """Remove all lines referencing page_path from index."""
    lines = content.split('\n')
    return '\n'.join(line for line in lines if page_path not in line)


def _sync_index_check(wiki_path, index_path):
    """Check index.md vs actual files. Return report dict."""
    # Collect all wiki page files
    actual_files = set()
    for type_dir in TYPE_DIR_MAP.values():
        dir_path = os.path.join(wiki_path, type_dir)
        if os.path.isdir(dir_path):
            for fname in os.listdir(dir_path):
                if fname.endswith('.md'):
                    actual_files.add('{}/{}'.format(type_dir, fname))

    # Parse index.md for referenced files
    indexed_files = set()
    if os.path.isfile(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.search(r'\]\(([^)]+\.md)\)', line)
                if m:
                    indexed_files.add(m.group(1))

    missing_from_index = sorted(actual_files - indexed_files)
    missing_files = sorted(indexed_files - actual_files)

    report = {
        'missing_from_index': missing_from_index,
        'missing_files': missing_files,
    }

    if missing_from_index or missing_files:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return report

    print("Index is in sync.")
    return report


def cmd_sync_index(wiki_path, add=None, remove=None, summary=None, check=False):
    """Manage index.md entries."""
    index_path = os.path.join(wiki_path, 'index.md')

    if check:
        return _sync_index_check(wiki_path, index_path)

    if not os.path.isfile(index_path):
        print("Error: index.md not found", file=sys.stderr)
        sys.exit(2)

    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if add:
        # Read title from page frontmatter
        page_full = os.path.join(wiki_path, add)
        if os.path.isfile(page_full):
            with open(page_full, 'r', encoding='utf-8') as f:
                fm, _ = parse_frontmatter(f.read())
            title = fm.get('title', os.path.splitext(os.path.basename(add))[0])
        else:
            title = os.path.splitext(os.path.basename(add))[0]

        page_type = _type_from_path(add)
        section = _section_header(page_type)
        entry = '- [{}]({}) \u2014 {}'.format(title, add, summary or '')
        content = _upsert_index_entry(content, section, add, entry)

    if remove:
        content = _remove_index_entry(content, remove)

    _write(index_path, content)
    if add:
        print("Index updated: added {}".format(add))
    if remove:
        print("Index updated: removed {}".format(remove))


# ── log-append ─────────────────────────────────────────────────────────

VALID_LOG_TYPES = {'init', 'ingest', 'query', 'lint'}


def cmd_log_append(wiki_path, log_type, title, created=None, modified=None,
                   refs=None, note=None):
    """Append an entry to log.md."""
    if log_type not in VALID_LOG_TYPES:
        print("Error: invalid log type '{}'. Must be one of: {}".format(
            log_type, ', '.join(sorted(VALID_LOG_TYPES))), file=sys.stderr)
        sys.exit(2)

    log_path = os.path.join(wiki_path, 'log.md')
    today = date.today().isoformat()

    lines = ['\n## [{date}] {type} | {title}'.format(date=today, type=log_type, title=title)]
    if created:
        lines.append('- \uc0dd\uc131: {}'.format(created))
    if modified:
        lines.append('- \uc218\uc815: {}'.format(modified))
    if refs:
        lines.append('- \ucc38\uc870: {}'.format(refs))
    if note:
        lines.append('- \uba54\ubaa8: {}'.format(note))
    lines.append('')

    entry = '\n'.join(lines)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(entry)

    print("Log appended: {} | {}".format(log_type, title))


# ── Helpers for lint / validate / status ──────────────────────────────────

CONTENT_DIRS = ['sources', 'entities', 'concepts', 'analyses', 'comparisons']

SOURCE_PATH_RE = re.compile(r'^(raw/|[a-z]+/[\w-]+\.md$)')


def _collect_wiki_pages(wiki_path):
    """Collect all .md files from wiki content directories.

    Returns list of (abs_path, rel_path) tuples where rel_path is
    relative to wiki_path (e.g. 'entities/foo.md').
    """
    pages = []
    for d in CONTENT_DIRS:
        dir_path = os.path.join(wiki_path, d)
        if not os.path.isdir(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if fname.endswith('.md'):
                abs_path = os.path.join(dir_path, fname)
                rel_path = '{}/{}'.format(d, fname)
                pages.append((abs_path, rel_path))
    return pages


def _collect_ingested_raw_paths(wiki_path):
    """Collect raw file paths referenced by any wiki page's `sources` frontmatter.

    A raw file is considered processed if its wiki-relative path appears in
    the `sources:` list of at least one wiki page.
    """
    ingested = set()
    for abs_path, _ in _collect_wiki_pages(wiki_path):
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                fm, _ = parse_frontmatter(f.read())
        except (OSError, UnicodeDecodeError):
            continue
        sources = fm.get('sources', [])
        if isinstance(sources, str):
            sources = [sources] if sources else []
        for src in sources:
            if isinstance(src, str) and src.startswith('raw/'):
                ingested.add(src)
    return ingested


def _count_unprocessed_raw(wiki_path):
    """Count raw files not referenced by any page's `sources` frontmatter."""
    raw_path = os.path.join(wiki_path, 'raw')
    if not os.path.isdir(raw_path):
        return 0
    ingested = _collect_ingested_raw_paths(wiki_path)
    count = 0
    for root, _, fnames in os.walk(raw_path):
        for fname in fnames:
            if fname.startswith('.'):
                continue
            rel = os.path.relpath(os.path.join(root, fname), wiki_path)
            if rel not in ingested:
                count += 1
    return count


# ── Task 6 commands ──────────────────────────────────────────────────────


def cmd_validate_frontmatter(wiki_path, file=None):
    """Validate frontmatter of wiki pages.

    If file is given, validate only that file; otherwise validate all pages.
    Returns list of issue dicts. Calls sys.exit(1) if issues found.
    """
    if file:
        pages = [(file, os.path.relpath(file, wiki_path))]
    else:
        pages = _collect_wiki_pages(wiki_path)

    issues = []
    for abs_path, rel_path in pages:
        with open(abs_path, 'r', encoding='utf-8') as f:
            text = f.read()
        fm, _ = parse_frontmatter(text)

        # Check required fields
        for field in REQUIRED_FM_FIELDS:
            if field not in fm:
                issues.append({
                    'file': rel_path,
                    'issue': 'missing required field: {}'.format(field),
                })

        # Validate type
        if 'type' in fm and fm['type'] not in VALID_TYPES:
            issues.append({
                'file': rel_path,
                'issue': 'invalid type: {}'.format(fm['type']),
            })

        # Validate sources
        if 'sources' in fm:
            sources = fm['sources']
            if isinstance(sources, str):
                sources = [sources] if sources else []
            for src in sources:
                if not SOURCE_PATH_RE.match(src):
                    issues.append({
                        'file': rel_path,
                        'issue': 'invalid source path: {}'.format(src),
                    })

    if issues:
        print(json.dumps(issues, indent=2, ensure_ascii=False))
    else:
        print("All frontmatter valid.")
    return issues


def cmd_lint_links(wiki_path):
    """Lint wiki-style [[links]]. Detect broken links and orphan pages.

    Returns report dict with 'broken' and 'orphans' keys.
    Calls sys.exit(1) if broken links or orphans found.
    """
    pages = _collect_wiki_pages(wiki_path)
    link_re = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')

    # Build slug -> rel_path map and track links
    slug_map = {}
    outgoing = {}  # rel_path -> set of slugs linked to
    for abs_path, rel_path in pages:
        slug = os.path.splitext(os.path.basename(abs_path))[0]
        slug_map[slug] = rel_path

        with open(abs_path, 'r', encoding='utf-8') as f:
            text = f.read()
        _, body = parse_frontmatter(text)
        outgoing[rel_path] = set(link_re.findall(body))

    # Detect broken links
    broken = []
    for rel_path, linked_slugs in outgoing.items():
        for slug in linked_slugs:
            if slug not in slug_map:
                broken.append({'file': rel_path, 'link': slug})

    # Detect orphans (pages with no incoming links)
    incoming = {slug: set() for slug in slug_map}
    for rel_path, linked_slugs in outgoing.items():
        src_slug = os.path.splitext(os.path.basename(rel_path))[0]
        for slug in linked_slugs:
            if slug in incoming:
                incoming[slug].add(src_slug)

    orphans = [slug_map[slug] for slug in sorted(incoming) if not incoming[slug]]

    report = {'broken': broken, 'orphans': orphans}
    if broken or orphans:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("All links valid, no orphans.")
    return report


def cmd_check_raw(wiki_path):
    """Check raw/ for uncommitted or post-add modifications.

    Calls sys.exit(1) if modified raw files found.
    """
    # Find git root
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, cwd=wiki_path,
        )
        if result.returncode != 0:
            print("Warning: not a git repository, skipping raw check.")
            return
    except FileNotFoundError:
        print("Warning: git not found, skipping raw check.")
        return

    git_root = os.path.realpath(result.stdout.strip())
    raw_rel = os.path.relpath(os.path.realpath(os.path.join(wiki_path, 'raw')), git_root)

    modified = []

    # Check unstaged changes
    result = subprocess.run(
        ['git', 'diff', '--name-only', '--', raw_rel],
        capture_output=True, text=True, cwd=git_root,
    )
    if result.stdout.strip():
        modified.extend(result.stdout.strip().split('\n'))

    # Check staged changes
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--', raw_rel],
        capture_output=True, text=True, cwd=git_root,
    )
    if result.stdout.strip():
        modified.extend(result.stdout.strip().split('\n'))

    # Check committed modifications after initial add
    result = subprocess.run(
        ['git', 'log', '--diff-filter=M', '--name-only', '--pretty=format:', '--', raw_rel],
        capture_output=True, text=True, cwd=git_root,
    )
    if result.stdout.strip():
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                modified.append(line.strip())

    modified = sorted(set(modified))
    if modified:
        print(json.dumps({'modified_raw': modified}, indent=2, ensure_ascii=False))
        sys.exit(1)

    print("Raw files are clean.")


# ── Task 7 commands ──────────────────────────────────────────────────────


def cmd_delete_page(wiki_path, page_path):
    """Delete a wiki page and update index.

    page_path can be relative to wiki_path (e.g. 'entities/foo.md')
    or absolute. Returns {'broken_refs': [...]}.
    """
    if os.path.isabs(page_path):
        abs_path = page_path
        rel_path = os.path.relpath(page_path, wiki_path)
    else:
        abs_path = os.path.join(wiki_path, page_path)
        rel_path = page_path

    if not os.path.isfile(abs_path):
        print("Error: file not found: {}".format(rel_path), file=sys.stderr)
        sys.exit(2)

    slug = os.path.splitext(os.path.basename(abs_path))[0]

    # Find incoming links to this page
    pages = _collect_wiki_pages(wiki_path)
    link_re = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
    broken_refs = []
    for abs_p, rel_p in pages:
        if abs_p == abs_path:
            continue
        with open(abs_p, 'r', encoding='utf-8') as f:
            text = f.read()
        _, body = parse_frontmatter(text)
        if slug in link_re.findall(body):
            broken_refs.append(rel_p)

    if broken_refs:
        print("Warning: deleting {} will break links from: {}".format(
            rel_path, ', '.join(broken_refs)), file=sys.stderr)

    # Delete file
    os.remove(abs_path)

    # Update index
    cmd_sync_index(wiki_path, remove=rel_path)

    print("Deleted: {}".format(rel_path))
    return {'broken_refs': broken_refs}


def cmd_list_raw(wiki_path, unprocessed=False):
    """List raw files.

    If unprocessed=True, filter out files matched to a sources/ page.
    Returns list of relative file paths.
    """
    raw_path = os.path.join(wiki_path, 'raw')
    if not os.path.isdir(raw_path):
        print("No raw/ directory found.")
        return []

    ingested = _collect_ingested_raw_paths(wiki_path) if unprocessed else set()

    files = []
    for root, _, fnames in os.walk(raw_path):
        for fname in fnames:
            if fname.startswith('.'):
                continue
            rel = os.path.relpath(os.path.join(root, fname), wiki_path)
            if unprocessed and rel in ingested:
                continue
            files.append(rel)

    files.sort()
    print(json.dumps(files, indent=2, ensure_ascii=False))
    return files


def cmd_status(wiki_path):
    """Show wiki status: page counts, last log date, unprocessed raw count.

    Returns status dict and prints JSON.
    """
    # Count pages per type
    counts = {}
    for type_name, dir_name in TYPE_DIR_MAP.items():
        dir_path = os.path.join(wiki_path, dir_name)
        if os.path.isdir(dir_path):
            counts[type_name] = len([f for f in os.listdir(dir_path) if f.endswith('.md')])
        else:
            counts[type_name] = 0

    # Last log date
    log_path = os.path.join(wiki_path, 'log.md')
    last_log_date = None
    if os.path.isfile(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', line)
                if m:
                    last_log_date = m.group(1)

    # Unprocessed raw count
    unprocessed_raw = _count_unprocessed_raw(wiki_path)

    # Structural lint summary
    fm_issues = cmd_validate_frontmatter(wiki_path)
    link_report = cmd_lint_links(wiki_path)
    index_report = cmd_sync_index(wiki_path, check=True)

    status = {
        'pages': counts,
        'total': sum(counts.values()),
        'last_log_date': last_log_date,
        'unprocessed_raw': unprocessed_raw,
        'lint': {
            'frontmatter_issues': len(fm_issues),
            'broken_links': len(link_report.get('broken', [])),
            'orphan_pages': len(link_report.get('orphans', [])),
            'index_mismatches': len(index_report.get('missing_from_index', [])) + len(index_report.get('missing_files', [])),
        },
    }
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return status


# ── CLI entry point ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog='wiki_tools',
        description='Wiki management CLI for LLM Wiki projects.',
    )
    sub = parser.add_subparsers(dest='command')

    # init
    p_init = sub.add_parser('init', help='Initialize a standalone wiki repo (defaults to the current directory)')
    p_init.add_argument('target', nargs='?', default=None,
                        help='Wiki repo root directory (the wiki lives here directly); '
                             'defaults to the current directory')

    # link
    p_link = sub.add_parser('link', help='Symlink $CLAUDE_CONFIG_DIR/wiki to a wiki repo (defaults to the current directory)')
    p_link.add_argument('target', nargs='?', default=None,
                        help='Wiki repo root directory to link; defaults to the current directory')

    # ensure-root-pointer
    sub.add_parser('ensure-root-pointer',
                   help='Ensure the wiki pointer block in $CLAUDE_CONFIG_DIR/CLAUDE.md')

    # create-page
    p_cp = sub.add_parser('create-page', help='Create wiki page skeleton')
    p_cp.add_argument('wiki_path')
    p_cp.add_argument('type', choices=sorted(VALID_TYPES))
    p_cp.add_argument('slug')
    p_cp.add_argument('--title', default='')
    p_cp.add_argument('--sources', default='')
    p_cp.add_argument('--tags', default='')

    # update-frontmatter
    p_uf = sub.add_parser('update-frontmatter', help='Update page frontmatter')
    p_uf.add_argument('file_path')
    p_uf.add_argument('--updated', default=None)
    p_uf.add_argument('--add-source', default=None)
    p_uf.add_argument('--add-tag', default=None)

    # sync-index
    p_si = sub.add_parser('sync-index', help='Manage index.md')
    p_si.add_argument('wiki_path')
    p_si.add_argument('--add', default=None)
    p_si.add_argument('--remove', default=None)
    p_si.add_argument('--summary', default=None)
    p_si.add_argument('--check', action='store_true')

    # log-append
    p_log = sub.add_parser('log-append', help='Append entry to log.md')
    p_log.add_argument('wiki_path')
    p_log.add_argument('type', choices=sorted(VALID_LOG_TYPES))
    p_log.add_argument('title')
    p_log.add_argument('--created', default=None)
    p_log.add_argument('--modified', default=None)
    p_log.add_argument('--refs', default=None)
    p_log.add_argument('--note', default=None)

    # validate-frontmatter
    p_vf = sub.add_parser('validate-frontmatter', help='Validate page frontmatter')
    p_vf.add_argument('wiki_path')
    p_vf.add_argument('--file', default=None)

    # lint-links
    p_ll = sub.add_parser('lint-links', help='Lint wiki-style [[links]]')
    p_ll.add_argument('wiki_path')

    # check-raw
    p_cr = sub.add_parser('check-raw', help='Check raw/ for modifications')
    p_cr.add_argument('wiki_path')

    # delete-page
    p_dp = sub.add_parser('delete-page', help='Delete a wiki page')
    p_dp.add_argument('wiki_path')
    p_dp.add_argument('page_path')

    # list-raw
    p_lr = sub.add_parser('list-raw', help='List raw files')
    p_lr.add_argument('wiki_path')
    p_lr.add_argument('--unprocessed', action='store_true')

    # status
    p_st = sub.add_parser('status', help='Show wiki status')
    p_st.add_argument('wiki_path')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(2)

    if args.command == 'init':
        cmd_init(args.target or os.getcwd())
    elif args.command == 'link':
        cmd_link(args.target or os.getcwd())
    elif args.command == 'ensure-root-pointer':
        cmd_ensure_root_pointer()
    elif args.command == 'create-page':
        sources = [s.strip() for s in args.sources.split(',') if s.strip()] if args.sources else []
        tags = [t.strip() for t in args.tags.split(',') if t.strip()] if args.tags else []
        cmd_create_page(args.wiki_path, args.type, args.slug,
                        title=args.title, sources=sources, tags=tags)
    elif args.command == 'update-frontmatter':
        cmd_update_frontmatter(args.file_path, updated=args.updated,
                               add_source=args.add_source, add_tag=args.add_tag)
    elif args.command == 'sync-index':
        cmd_sync_index(args.wiki_path, add=args.add, remove=args.remove,
                       summary=args.summary, check=args.check)
    elif args.command == 'log-append':
        cmd_log_append(args.wiki_path, args.type, args.title,
                       created=args.created, modified=args.modified,
                       refs=args.refs, note=args.note)
    elif args.command == 'validate-frontmatter':
        issues = cmd_validate_frontmatter(args.wiki_path, file=args.file)
        if issues:
            sys.exit(1)
    elif args.command == 'lint-links':
        report = cmd_lint_links(args.wiki_path)
        if report.get('broken') or report.get('orphans'):
            sys.exit(1)
    elif args.command == 'check-raw':
        cmd_check_raw(args.wiki_path)
    elif args.command == 'delete-page':
        cmd_delete_page(args.wiki_path, args.page_path)
    elif args.command == 'list-raw':
        cmd_list_raw(args.wiki_path, unprocessed=args.unprocessed)
    elif args.command == 'status':
        cmd_status(args.wiki_path)


if __name__ == '__main__':
    main()
