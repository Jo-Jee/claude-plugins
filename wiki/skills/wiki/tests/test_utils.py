import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from helpers import WikiTestCase
from wiki_tools import (cmd_init, cmd_create_page, cmd_delete_page,
                        cmd_list_raw, cmd_status, cmd_sync_index)


class TestDeletePage(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())

    def test_delete_existing_page(self):
        cmd_create_page(self.wiki_path, 'entity', 'foo', title='Foo')
        page_path = os.path.join(self.wiki_path, 'entities', 'foo.md')
        self.assertTrue(os.path.isfile(page_path))
        result = cmd_delete_page(self.wiki_path, page_path)
        self.assertFalse(os.path.isfile(page_path))
        self.assertIsInstance(result, dict)
        self.assertIn('broken_refs', result)

    def test_delete_nonexistent_exits(self):
        page_path = os.path.join(self.wiki_path, 'entities', 'nope.md')
        with self.assertRaises(SystemExit) as cm:
            cmd_delete_page(self.wiki_path, page_path)
        self.assertEqual(cm.exception.code, 2)

    def test_delete_warns_broken_refs(self):
        cmd_create_page(self.wiki_path, 'entity', 'target', title='Target')
        # Create a page that links to target
        linker_path = os.path.join(self.wiki_path, 'entities', 'linker.md')
        self.write_file(linker_path, "---\ntitle: Linker\ntype: entity\ncreated: 2026-01-01\nupdated: 2026-01-01\nsources: []\ntags: []\n---\n\n# Linker\n\nSee [[target]].\n")
        target_path = os.path.join(self.wiki_path, 'entities', 'target.md')
        result = cmd_delete_page(self.wiki_path, target_path)
        self.assertIn('entities/linker.md', result['broken_refs'])

    def test_delete_updates_index(self):
        cmd_create_page(self.wiki_path, 'entity', 'indexed', title='Indexed')
        cmd_sync_index(self.wiki_path, add='entities/indexed.md', summary='Test')
        index_path = os.path.join(self.wiki_path, 'index.md')
        content = self.read_file(index_path)
        self.assertIn('indexed.md', content)
        page_path = os.path.join(self.wiki_path, 'entities', 'indexed.md')
        cmd_delete_page(self.wiki_path, page_path)
        content = self.read_file(index_path)
        self.assertNotIn('indexed.md', content)


class TestListRaw(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())

    def test_list_empty_raw(self):
        result = cmd_list_raw(self.wiki_path)
        self.assertEqual(result, [])

    def test_list_raw_files(self):
        self.write_file(os.path.join(self.wiki_path, 'raw', 'notes', 'a.md'), 'content')
        self.write_file(os.path.join(self.wiki_path, 'raw', 'articles', 'b.md'), 'content')
        result = cmd_list_raw(self.wiki_path)
        self.assertEqual(len(result), 2)

    def test_list_excludes_hidden(self):
        self.write_file(os.path.join(self.wiki_path, 'raw', 'notes', '.hidden'), 'secret')
        self.write_file(os.path.join(self.wiki_path, 'raw', 'notes', 'visible.md'), 'content')
        result = cmd_list_raw(self.wiki_path)
        self.assertEqual(len(result), 1)
        self.assertIn('raw/notes/visible.md', result[0])

    def test_unprocessed_filter(self):
        self.write_file(os.path.join(self.wiki_path, 'raw', 'notes', 'paper.md'), 'raw content')
        # Create a source page that references the raw file (as `ingest` does via --sources)
        cmd_create_page(self.wiki_path, 'source', 'paper', title='Paper',
                        sources=['raw/notes/paper.md'])
        all_raw = cmd_list_raw(self.wiki_path)
        self.assertEqual(len(all_raw), 1)
        unprocessed = cmd_list_raw(self.wiki_path, unprocessed=True)
        self.assertEqual(len(unprocessed), 0)


class TestStatus(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())

    def test_status_empty_wiki(self):
        status = cmd_status(self.wiki_path)
        self.assertIn('pages', status)
        self.assertIn('last_log_date', status)
        self.assertIn('unprocessed_raw', status)
        for t in ['source', 'entity', 'concept', 'analysis', 'comparison']:
            self.assertEqual(status['pages'][t], 0)

    def test_status_counts_pages(self):
        cmd_create_page(self.wiki_path, 'entity', 'a', title='A')
        cmd_create_page(self.wiki_path, 'entity', 'b', title='B')
        cmd_create_page(self.wiki_path, 'concept', 'c', title='C')
        status = cmd_status(self.wiki_path)
        self.assertEqual(status['pages']['entity'], 2)
        self.assertEqual(status['pages']['concept'], 1)
        self.assertEqual(status['total'], 3)
        self.assertIn('lint', status)

    def test_status_counts_unprocessed_raw(self):
        self.write_file(os.path.join(self.wiki_path, 'raw', 'notes', 'x.md'), 'content')
        status = cmd_status(self.wiki_path)
        self.assertEqual(status['unprocessed_raw'], 1)

    def test_status_last_log_date(self):
        status = cmd_status(self.wiki_path)
        # log.md was created by init, should have today's date
        self.assertIsNotNone(status['last_log_date'])


if __name__ == '__main__':
    unittest.main()
