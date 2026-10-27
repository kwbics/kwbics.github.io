"""Index scope of the locked formatter, using a disposable Git fixture only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SiteFormatterBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory(prefix="site-format-", dir=os.environ["TMPDIR"])
        self.root = Path(self.fixture.name)
        self.addCleanup(self.fixture.cleanup)
        self.git("init", "--quiet")
        shutil.copyfile(ROOT / "package-lock.json", self.root / "package-lock.json")
        (self.root / ".prettierrc.json").write_text(json.dumps({"printWidth": 150, "trailingComma": "es5"}))
        shutil.copyfile(ROOT / ".prettierignore", self.root / ".prettierignore")
        self.good = '{ "fixture": true }\n'
        self.bad = '{"fixture":true}'

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def check_format(self):
        return subprocess.run(["node", str(ROOT / "test/site_prettier.mjs")], cwd=self.root,
                              text=True, capture_output=True)

    def test_tracked_working_copy_format_error_is_visible(self):
        source = self.root / "tracked.json"
        source.write_text(self.good)
        self.git("add", "tracked.json")
        # File is already in the index; only the working copy becomes malformed.
        source.write_text(self.bad)
        result = self.check_format()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("[format] tracked.json", result.stderr)

    def test_staged_new_file_format_error_is_visible(self):
        (self.root / "new.json").write_text(self.bad)
        self.git("add", "new.json")
        result = self.check_format()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("[format] new.json", result.stderr)

    def test_unrelated_untracked_error_is_ignored(self):
        (self.root / "tracked.json").write_text(self.good)
        self.git("add", "tracked.json")
        (self.root / "unrelated.json").write_text(self.bad)
        result = self.check_format()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("unrelated.json", result.stdout + result.stderr)
        self.assertIn("1 source files checked; 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
