import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from helpers import WikiTestCase
from wiki_tools import cmd_init, cmd_create_page, cmd_update_frontmatter, parse_frontmatter, render_frontmatter


class TestCreatePage(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())

    def test_creates_entity_page(self):
        cmd_create_page(self.wiki_path, 'entity', 'centrifugo', title='Centrifugo')
        path = os.path.join(self.wiki_path, 'entities', 'centrifugo.md')
        self.assertTrue(os.path.isfile(path))
        fm, body = parse_frontmatter(self.read_file(path))
        self.assertEqual(fm['title'], 'Centrifugo')
        self.assertEqual(fm['type'], 'entity')
        self.assertIn('# Centrifugo', body)

    def test_creates_analysis_page_in_analyses(self):
        cmd_create_page(self.wiki_path, 'analysis', 'cost-compare', title='Cost Compare')
        path = os.path.join(self.wiki_path, 'analyses', 'cost-compare.md')
        self.assertTrue(os.path.isfile(path))

    def test_sets_sources_and_tags(self):
        cmd_create_page(self.wiki_path, 'source', 'overview',
                        title='Overview', sources=['raw/notes/a.md'], tags=['ai', 'ml'])
        path = os.path.join(self.wiki_path, 'sources', 'overview.md')
        fm, _ = parse_frontmatter(self.read_file(path))
        self.assertEqual(fm['sources'], ['raw/notes/a.md'])
        self.assertEqual(fm['tags'], ['ai', 'ml'])

    def test_refuses_overwrite(self):
        cmd_create_page(self.wiki_path, 'entity', 'foo', title='Foo')
        with self.assertRaises(SystemExit) as cm:
            cmd_create_page(self.wiki_path, 'entity', 'foo', title='Foo')
        self.assertEqual(cm.exception.code, 2)

    def test_invalid_type(self):
        with self.assertRaises(SystemExit) as cm:
            cmd_create_page(self.wiki_path, 'invalid', 'foo', title='Foo')
        self.assertEqual(cm.exception.code, 2)


class TestUpdateFrontmatter(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        cmd_create_page(self.wiki_path, 'entity', 'test', title='Test')
        self.page_path = os.path.join(self.wiki_path, 'entities', 'test.md')

    def test_updates_date(self):
        cmd_update_frontmatter(self.page_path, updated='2026-12-31')
        fm, _ = parse_frontmatter(self.read_file(self.page_path))
        self.assertEqual(fm['updated'], '2026-12-31')

    def test_adds_source(self):
        cmd_update_frontmatter(self.page_path, add_source='raw/notes/new.md')
        fm, _ = parse_frontmatter(self.read_file(self.page_path))
        self.assertIn('raw/notes/new.md', fm['sources'])

    def test_adds_tag(self):
        cmd_update_frontmatter(self.page_path, add_tag='new-tag')
        fm, _ = parse_frontmatter(self.read_file(self.page_path))
        self.assertIn('new-tag', fm['tags'])

    def test_preserves_body(self):
        content = self.read_file(self.page_path)
        fm, body = parse_frontmatter(content)
        new_content = render_frontmatter(fm, "\n# Test\n\nSome body content.\n")
        self.write_file(self.page_path, new_content)
        cmd_update_frontmatter(self.page_path, add_tag='x')
        _, body = parse_frontmatter(self.read_file(self.page_path))
        self.assertIn('Some body content.', body)


if __name__ == '__main__':
    unittest.main()
