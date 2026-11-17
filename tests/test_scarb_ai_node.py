"""Include AI collector/resolver tests in the existing Python discovery step.

The established GMKtec workflow installs Node 22 before Python unit tests.
This does not add a runner, a model call or a new workflow trigger.
"""
import subprocess
import unittest
from pathlib import Path


class ScarbAiNodeTests(unittest.TestCase):
    def test_collector_and_resolver(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(["node", "--test", "tests/scarb-ai-copy.test.mjs"],
                                cwd=root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
