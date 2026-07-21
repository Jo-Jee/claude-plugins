import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from helpers import WikiTestCase
from wiki_tools import cmd_init


class TestInit(WikiTestCase, unittest.TestCase):
    def test_creates_directory_structure(self):
        cmd_init(self.tmpdir, template_dir=self._template_dir())
        wiki = self.wiki_path
        self.assertTrue(os.path.isdir(wiki))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'raw', 'notes')))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'raw', 'articles')))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'raw', 'papers')))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'raw', 'assets')))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'sources')))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'entities')))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'concepts')))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'analyses')))
        self.assertTrue(os.path.isdir(os.path.join(wiki, 'comparisons')))

    def test_creates_index_and_log(self):
        cmd_init(self.tmpdir, template_dir=self._template_dir())
        wiki = self.wiki_path
        self.assertTrue(os.path.isfile(os.path.join(wiki, 'index.md')))
        self.assertTrue(os.path.isfile(os.path.join(wiki, 'log.md')))
        index = self.read_file(wiki, 'index.md')
        self.assertIn('# Wiki Index', index)
        log = self.read_file(wiki, 'log.md')
        self.assertIn('init', log)

    def test_copies_claude_md(self):
        cmd_init(self.tmpdir, template_dir=self._template_dir())
        self.assertTrue(os.path.isfile(os.path.join(self.wiki_path, 'CLAUDE.md')))

    def test_creates_obsidian_config(self):
        cmd_init(self.tmpdir, template_dir=self._template_dir())
        obsidian = os.path.join(self.wiki_path, '.obsidian')
        self.assertTrue(os.path.isfile(os.path.join(obsidian, 'app.json')))

    def test_fails_if_wiki_exists(self):
        os.makedirs(self.wiki_path)
        with self.assertRaises(SystemExit) as cm:
            cmd_init(self.tmpdir, template_dir=self._template_dir())
        self.assertEqual(cm.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
