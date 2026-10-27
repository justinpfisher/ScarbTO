"""Run offline Python and Node tests contained in research prototype lanes."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    repository = Path(__file__).resolve().parents[2]
    research = repository / "research"
    if not research.is_dir():
        print("No research directory; skipping research prototype tests.")
        return 0

    test_directories = sorted(path for path in research.glob("*/tests") if path.is_dir())
    python_suites = [directory for directory in test_directories if any(directory.glob("test_*.py"))]
    node_suites = [
        (directory, test_file)
        for directory in test_directories
        for test_file in sorted(directory.glob("*.test.mjs"))
    ]
    if not python_suites and not node_suites:
        print("No research prototype tests found; skipping.")
        return 0

    for directory in python_suites:
        print(f"Running Python research tests in {directory.relative_to(repository)}")
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
            cwd=directory.parent,
            check=True,
        )
    for directory, test_file in node_suites:
        print(f"Running Node research test {test_file.relative_to(repository)}")
        subprocess.run(["node", str(test_file)], cwd=directory.parent, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

