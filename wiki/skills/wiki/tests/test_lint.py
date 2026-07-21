import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from helpers import WikiTestCase
from wiki_tools import (cmd_init, cmd_create_page, cmd_validate_frontmatter,
                        cmd_lint_links, cmd_check_raw, render_frontmatter)


class TestValidateFrontmatter(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())

    def test_valid_page_passes(self):
        cmd_create_page(self.wiki_path, 'entity', 'ok', title='OK')
        report = cmd_validate_frontmatter(self.wiki_path)
        self.assertEqual(report, [])

    def test_missing_field_reported(self):
        path = os.path.join(self.wiki_path, 'entities', 'bad.md')
        self.write_file(path, "---\ntype: entity\n---\n\n# Bad\n")
        report = cmd_validate_frontmatter(self.wiki_path)
        self.assertTrue(len(report) > 0)
        self.assertTrue(any('title' in str(item) for item in report))

    def test_single_file_mode(self):
        path = os.path.join(self.wiki_path, 'entities', 'bad.md')
        self.write_file(path, "---\ntype: entity\n---\n\n# Bad\n")
        report = cmd_validate_frontmatter(self.wiki_path, file=path)
        self.assertTrue(len(report) > 0)

    def test_invalid_source_path(self):
        path = os.path.join(self.wiki_path, 'entities', 'badsrc.md')
        self.write_file(path, "---\ntitle: BadSrc\ntype: entity\ncreated: 2026-01-01\nupdated: 2026-01-01\nsources: [not-a-valid-path]\ntags: []\n---\n\n# BadSrc\n")
        report = cmd_validate_frontmatter(self.wiki_path, file=path)
        self.assertTrue(any('invalid source' in str(item) for item in report))

    def test_valid_source_paths(self):
        cmd_create_page(self.wiki_path, 'entity', 'goodsrc', title='GoodSrc')
        path = os.path.join(self.wiki_path, 'entities', 'goodsrc.md')
        self.write_file(path, "---\ntitle: GoodSrc\ntype: entity\ncreated: 2026-01-01\nupdated: 2026-01-01\nsources: [raw/notes/a.md]\ntags: []\n---\n\n# GoodSrc\n")
        report = cmd_validate_frontmatter(self.wiki_path, file=path)
        self.assertEqual(report, [])


class TestCheckRaw(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        import subprocess
        subprocess.run(['git', 'init'], cwd=self.tmpdir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=self.tmpdir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=self.tmpdir, capture_output=True)
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        subprocess.run(['git', 'add', '.'], cwd=self.tmpdir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=self.tmpdir, capture_output=True)

    def test_clean_raw_passes(self):
        cmd_check_raw(self.wiki_path)

    def test_detects_uncommitted_changes(self):
        import subprocess
        raw_file = os.path.join(self.wiki_path, 'raw', 'notes', 'test.md')
        self.write_file(raw_file, 'original content')
        subprocess.run(['git', 'add', '.'], cwd=self.tmpdir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'add raw'], cwd=self.tmpdir, capture_output=True)
        self.write_file(raw_file, 'modified content')
        with self.assertRaises(SystemExit) as cm:
            cmd_check_raw(self.wiki_path)
        self.assertEqual(cm.exception.code, 1)


class TestLintLinks(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())

    def test_detects_broken_link(self):
        path = os.path.join(self.wiki_path, 'entities', 'a.md')
        self.write_file(path, "---\ntitle: A\ntype: entity\ncreated: 2026-01-01\nupdated: 2026-01-01\nsources: []\ntags: []\n---\n\n# A\n\nSee [[nonexistent]].\n")
        report = cmd_lint_links(self.wiki_path)
        self.assertTrue(any('nonexistent' in str(b) for b in report.get('broken', [])))

    def test_detects_orphan_page(self):
        for slug in ['alpha', 'beta']:
            path = os.path.join(self.wiki_path, 'entities', slug + '.md')
            self.write_file(path, "---\ntitle: {t}\ntype: entity\ncreated: 2026-01-01\nupdated: 2026-01-01\nsources: []\ntags: []\n---\n\n# {t}\n\nNo links.\n".format(t=slug.title()))
        report = cmd_lint_links(self.wiki_path)
        self.assertTrue(len(report.get('orphans', [])) >= 2)

    def test_parses_display_text_links(self):
        path = os.path.join(self.wiki_path, 'entities', 'a.md')
        self.write_file(path, "---\ntitle: A\ntype: entity\ncreated: 2026-01-01\nupdated: 2026-01-01\nsources: []\ntags: []\n---\n\n# A\n\nSee [[b|Beta page]].\n")
        path_b = os.path.join(self.wiki_path, 'entities', 'b.md')
        self.write_file(path_b, "---\ntitle: B\ntype: entity\ncreated: 2026-01-01\nupdated: 2026-01-01\nsources: []\ntags: []\n---\n\n# B\nSee [[a]].\n")
        report = cmd_lint_links(self.wiki_path)
        self.assertEqual(report.get('broken', []), [])


if __name__ == '__main__':
    unittest.main()
