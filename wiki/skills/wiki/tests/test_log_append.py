import unittest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from helpers import WikiTestCase
from wiki_tools import cmd_init, cmd_log_append


class TestLogAppend(WikiTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        cmd_init(self.wiki_path, template_dir=self._template_dir())

    def test_appends_ingest_entry(self):
        cmd_log_append(self.wiki_path, 'ingest', 'Project Overview',
                       created='sources/overview.md', modified='entities/foo.md')
        log = self.read_file(self.wiki_path, 'log.md')
        self.assertIn('ingest | Project Overview', log)
        self.assertIn('sources/overview.md', log)
        self.assertIn('entities/foo.md', log)

    def test_appends_query_entry(self):
        cmd_log_append(self.wiki_path, 'query', 'What is Centrifugo?',
                       refs='entities/centrifugo.md')
        log = self.read_file(self.wiki_path, 'log.md')
        self.assertIn('query | What is Centrifugo?', log)
        self.assertIn('centrifugo.md', log)

    def test_appends_lint_entry(self):
        cmd_log_append(self.wiki_path, 'lint', 'Routine check',
                       note='Found 2 issues, fixed 1')
        log = self.read_file(self.wiki_path, 'log.md')
        self.assertIn('lint | Routine check', log)
        self.assertIn('Found 2 issues', log)

    def test_preserves_existing_entries(self):
        cmd_log_append(self.wiki_path, 'ingest', 'First')
        cmd_log_append(self.wiki_path, 'ingest', 'Second')
        log = self.read_file(self.wiki_path, 'log.md')
        self.assertIn('First', log)
        self.assertIn('Second', log)
        # init entry from setUp should still be there
        self.assertIn('init', log)

    def test_includes_date(self):
        from datetime import date
        cmd_log_append(self.wiki_path, 'query', 'Test date')
        log = self.read_file(self.wiki_path, 'log.md')
        self.assertIn(date.today().isoformat(), log)


if __name__ == '__main__':
    unittest.main()
