"""Self-contained runner for the narma10_np test suite.

    python tests/narma10_np/run_tests.py

Adds the repo root to ``sys.path`` and runs unittest discovery over this
directory, so it works without pytest and without a top-level ``tests`` package.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(HERE), top_level_dir=str(REPO_ROOT),
                            pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
