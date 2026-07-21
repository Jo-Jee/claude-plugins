"""Shared test utilities."""
import os
import tempfile
import shutil


class WikiTestCase:
    """Mixin for tests that need a temp wiki directory."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.wiki_path = os.path.join(self.tmpdir, 'wiki')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def read_file(self, *path_parts):
        with open(os.path.join(*path_parts), 'r') as f:
            return f.read()

    def write_file(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)

    def _template_dir(self):
        return os.path.join(os.path.dirname(__file__), '..', 'templates')
