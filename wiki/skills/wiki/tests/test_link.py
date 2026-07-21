import unittest
import os
import sys
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from wiki_tools import cmd_link, _config_dir


class TestLink(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config = os.path.join(self.tmp, 'config')
        os.makedirs(self.config)
        self.target = os.path.join(self.tmp, 'mywiki')
        os.makedirs(self.target)
        self._old_env = os.environ.get('CLAUDE_CONFIG_DIR')
        os.environ['CLAUDE_CONFIG_DIR'] = self.config

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop('CLAUDE_CONFIG_DIR', None)
        else:
            os.environ['CLAUDE_CONFIG_DIR'] = self._old_env
        shutil.rmtree(self.tmp)

    def test_config_dir_honors_env(self):
        self.assertEqual(_config_dir(), self.config)

    def test_creates_symlink_to_target(self):
        cmd_link(self.target)
        link = os.path.join(self.config, 'wiki')
        self.assertTrue(os.path.islink(link))
        self.assertEqual(os.path.realpath(link), os.path.realpath(self.target))

    def test_idempotent_replaces_existing_symlink(self):
        cmd_link(self.target)
        other = os.path.join(self.tmp, 'other')
        os.makedirs(other)
        cmd_link(other)  # should replace, not error
        link = os.path.join(self.config, 'wiki')
        self.assertEqual(os.path.realpath(link), os.path.realpath(other))

    def test_refuses_non_symlink_at_link_path(self):
        os.makedirs(os.path.join(self.config, 'wiki'))  # real dir squats the path
        with self.assertRaises(SystemExit) as cm:
            cmd_link(self.target)
        self.assertEqual(cm.exception.code, 2)

    def test_rejects_nondir_target(self):
        with self.assertRaises(SystemExit) as cm:
            cmd_link(os.path.join(self.tmp, 'does-not-exist'))
        self.assertEqual(cm.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
