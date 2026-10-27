"""Run reproducible offline checks without importing the bot or loading .env."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tokenize

ROOT = Path(__file__).resolve().parents[1]
TEST_RUNNER = """
import sys
import unittest
suite = unittest.defaultTestLoader.discover('tests', pattern='test_*.py')
if suite.countTestCases() == 0:
    print('No tests discovered; validation cannot pass.', file=sys.stderr)
    raise SystemExit(1)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
"""


def main() -> int:
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required.", file=sys.stderr)
        return 1

    sources = sorted(ROOT.glob("*.py"))
    for folder in ("scripts", "tests"):
        sources.extend(sorted((ROOT / folder).rglob("*.py")))

    for source in sources:
        try:
            with tokenize.open(source) as stream:
                compile(stream.read(), str(source), "exec", dont_inherit=True)
        except (SyntaxError, UnicodeError, OSError) as error:
            print(f"Compilation failed: {source.relative_to(ROOT)}: {error}", file=sys.stderr)
            return 1
    print(f"Compiled {len(sources)} Python files in memory (no bot imports).", flush=True)

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-W", "error", "-B", "-c", TEST_RUNNER],
        cwd=ROOT,
        env=env,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
