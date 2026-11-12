"""Regression: repository checkout names need not equal the skill identifier."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from self_check import check

class StructureTests(unittest.TestCase):
    def test_repository_directory_alias_is_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            alias = Path(temporary) / "arbitrary-checkout-name"
            shutil.copytree(ROOT, alias, ignore=shutil.ignore_patterns(".git", "__pycache__", ".runs"))
            self.assertEqual(check(alias), [])

if __name__ == "__main__":
    unittest.main()
