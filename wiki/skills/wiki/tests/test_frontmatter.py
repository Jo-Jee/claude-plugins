# skills/wiki/tests/test_frontmatter.py
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from wiki_tools import parse_frontmatter, render_frontmatter


class TestParseFrontmatter(unittest.TestCase):
    def test_basic(self):
        text = (
            "---\n"
            "title: Test Page\n"
            "type: entity\n"
            "created: 2026-04-15\n"
            "updated: 2026-04-15\n"
            "sources: []\n"
            "tags: []\n"
            "---\n"
            "\n"
            "# Test Page\n"
            "\nBody content.\n"
        )
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm['title'], 'Test Page')
        self.assertEqual(fm['type'], 'entity')
        self.assertEqual(fm['sources'], [])
        self.assertIn('# Test Page', body)

    def test_with_list_values(self):
        text = (
            "---\n"
            "title: Test\n"
            "type: source\n"
            "created: 2026-04-15\n"
            "updated: 2026-04-15\n"
            "sources: [raw/notes/a.md]\n"
            "tags: [ai, ml]\n"
            "---\n"
            "\n# Test\n"
        )
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm['sources'], ['raw/notes/a.md'])
        self.assertEqual(fm['tags'], ['ai', 'ml'])

    def test_no_frontmatter(self):
        text = "# Just a heading\n\nBody.\n"
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm, {})
        self.assertEqual(body, text)


class TestRenderFrontmatter(unittest.TestCase):
    def test_roundtrip(self):
        fm = {
            'title': 'Test Page',
            'type': 'entity',
            'created': '2026-04-15',
            'updated': '2026-04-15',
            'sources': [],
            'tags': ['ai'],
        }
        body = "\n# Test Page\n\nBody.\n"
        result = render_frontmatter(fm, body)
        self.assertTrue(result.startswith('---\n'))
        parsed_fm, parsed_body = parse_frontmatter(result)
        self.assertEqual(parsed_fm['title'], 'Test Page')
        self.assertEqual(parsed_fm['tags'], ['ai'])
        self.assertEqual(parsed_body, body)


if __name__ == '__main__':
    unittest.main()
