"""init/link default their target to the current directory when no path is given."""
import unittest
import os
import sys
import subprocess
import tempfile
import shutil

BIN = os.path.join(os.path.dirname(__file__), '..', 'bin', 'wiki_tools.py')


class TestCliCwdDefault(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run(self, args, cwd, env=None):
        return subprocess.run(
            [sys.executable, BIN] + args,
            cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_init_without_target_uses_cwd(self):
        target = os.path.join(self.tmp, 'mywiki')
        os.makedirs(target)
        r = self._run(['init'], cwd=target)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertTrue(os.path.isfile(os.path.join(target, 'index.md')))
        self.assertTrue(os.path.isdir(os.path.join(target, 'sources')))

    def test_link_without_target_uses_cwd(self):
        config = os.path.join(self.tmp, 'config')
        os.makedirs(config)
        target = os.path.join(self.tmp, 'mywiki')
        os.makedirs(target)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=config)
        r = self._run(['link'], cwd=target, env=env)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        link = os.path.join(config, 'wiki')
        self.assertTrue(os.path.islink(link))
        self.assertEqual(os.path.realpath(link), os.path.realpath(target))


if __name__ == '__main__':
    unittest.main()
