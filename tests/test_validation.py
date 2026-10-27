"""Check validator failure paths against tiny isolated project fixtures."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

VALIDATOR = Path(__file__).resolve().parents[1] / "scripts" / "validate.py"


class ValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="flightbizubot-validation-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "scripts").mkdir()
        (self.root / "tests").mkdir()
        shutil.copyfile(VALIDATOR, self.root / "scripts" / "validate.py")
        (self.root / "tests" / "test_fixture.py").write_text(
            "import unittest\nclass Fixture(unittest.TestCase):\n"
            "    def test_ok(self):\n        self.assertTrue(True)\n", encoding="utf-8")

    def run_validation(self):
        # Call from outside the fixture root to check cwd independence.
        return subprocess.run(
            [sys.executable, "-W", "error", "-B", str(self.root / "scripts" / "validate.py")],
            cwd=self.root.parent, capture_output=True, text=True, check=False,
        )

    def test_compiles_without_importing_application_or_writing_bytecode(self):
        (self.root / "main.py").write_text(
            "raise RuntimeError('Application must not be imported')\n", encoding="utf-8")
        result = self.run_validation()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(list(self.root.rglob("*.pyc")))

    def test_invalid_syntax_is_rejected(self):
        (self.root / "main.py").write_text("def invalid(:\n", encoding="utf-8")
        result = self.run_validation()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Compilation failed", result.stderr)

    def test_empty_test_suite_is_rejected(self):
        (self.root / "tests" / "test_fixture.py").write_text("", encoding="utf-8")
        result = self.run_validation()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No tests discovered", result.stderr)

    def test_test_failure_is_propagated(self):
        (self.root / "tests" / "test_fixture.py").write_text(
            "import unittest\nclass Fixture(unittest.TestCase):\n"
            "    def test_failure(self):\n        self.fail('expected fixture failure')\n",
            encoding="utf-8")
        result = self.run_validation()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAILED", result.stderr)

    def test_unhandled_warning_in_test_is_rejected(self):
        (self.root / "tests" / "test_fixture.py").write_text(
            "import unittest, warnings\nclass Fixture(unittest.TestCase):\n"
            "    def test_warning(self):\n        warnings.warn('fixture warning')\n",
            encoding="utf-8")
        result = self.run_validation()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UserWarning", result.stderr)


if __name__ == "__main__":
    unittest.main()
