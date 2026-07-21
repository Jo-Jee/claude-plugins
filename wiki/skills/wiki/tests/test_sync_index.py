import unittest
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from helpers import WikiTestCase
from wiki_tools import cmd_init, cmd_create_page, cmd_sync_index


class TestSyncIndexAdd(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        cmd_create_page(self.wiki_path, 'entity', 'foo', title='Foo Tool')

    def test_adds_entry_to_correct_section(self):
        cmd_sync_index(self.wiki_path, add='entities/foo.md', summary='A foo tool')
        index = self.read_file(self.wiki_path, 'index.md')
        self.assertIn('- [Foo Tool](entities/foo.md)', index)
        self.assertIn('A foo tool', index)
        # Should be under Entities section
        lines = index.split('\n')
        entities_idx = next(i for i, l in enumerate(lines) if '## Entities' in l)
        foo_idx = next(i for i, l in enumerate(lines) if 'foo.md' in l)
        self.assertGreater(foo_idx, entities_idx)

    def test_upsert_replaces_existing(self):
        cmd_sync_index(self.wiki_path, add='entities/foo.md', summary='Old summary')
        cmd_sync_index(self.wiki_path, add='entities/foo.md', summary='New summary')
        index = self.read_file(self.wiki_path, 'index.md')
        self.assertNotIn('Old summary', index)
        self.assertIn('New summary', index)
        # Should appear only once
        self.assertEqual(index.count('foo.md'), 1)

    def test_alphabetical_sort(self):
        cmd_create_page(self.wiki_path, 'entity', 'alpha', title='Alpha')
        cmd_create_page(self.wiki_path, 'entity', 'zeta', title='Zeta')
        cmd_sync_index(self.wiki_path, add='entities/zeta.md', summary='Z tool')
        cmd_sync_index(self.wiki_path, add='entities/alpha.md', summary='A tool')
        cmd_sync_index(self.wiki_path, add='entities/foo.md', summary='F tool')
        index = self.read_file(self.wiki_path, 'index.md')
        alpha_pos = index.index('alpha.md')
        foo_pos = index.index('foo.md')
        zeta_pos = index.index('zeta.md')
        self.assertLess(alpha_pos, foo_pos)
        self.assertLess(foo_pos, zeta_pos)


class TestSyncIndexRemove(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())
        cmd_create_page(self.wiki_path, 'entity', 'foo', title='Foo')
        cmd_sync_index(self.wiki_path, add='entities/foo.md', summary='A foo')

    def test_removes_entry(self):
        cmd_sync_index(self.wiki_path, remove='entities/foo.md')
        index = self.read_file(self.wiki_path, 'index.md')
        self.assertNotIn('foo.md', index)


class TestSyncIndexCheck(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())

    def test_detects_file_not_in_index(self):
        cmd_create_page(self.wiki_path, 'entity', 'orphan', title='Orphan')
        report = cmd_sync_index(self.wiki_path, check=True)
        self.assertTrue(any('orphan' in str(item) for item in report.get('missing_from_index', [])))

    def test_detects_index_entry_without_file(self):
        cmd_create_page(self.wiki_path, 'entity', 'ghost', title='Ghost')
        cmd_sync_index(self.wiki_path, add='entities/ghost.md', summary='Ghost')
        os.remove(os.path.join(self.wiki_path, 'entities', 'ghost.md'))
        report = cmd_sync_index(self.wiki_path, check=True)
        self.assertTrue(any('ghost' in str(item) for item in report.get('missing_files', [])))

    def test_clean_wiki_returns_empty(self):
        report = cmd_sync_index(self.wiki_path, check=True)
        self.assertEqual(report.get('missing_from_index', []), [])
        self.assertEqual(report.get('missing_files', []), [])


if __name__ == '__main__':
    unittest.main()
