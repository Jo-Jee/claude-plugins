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
