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
