from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.snapshot_integrity import (
    SnapshotIntegrityError,
    is_snapshot_fresh,
    validate_snapshot_integrity,
)
from scripts.verify_code_only_release import (
    ReleaseError,
    validate_dispatch_environment,
    validate_publisher_tree,
)

ROOT = Path(__file__).resolve().parents[1]


class CodeOnlyReleaseTests(unittest.TestCase):
    def test_code_only_keeps_the_real_last_good_timestamps(self) -> None:
        with (ROOT / "docs/data/snapshot.json").open(encoding="utf-8") as stream:
            before = json.load(stream)
        result = validate_snapshot_integrity(ROOT / "docs/data")
        with (ROOT / "docs/data/snapshot.json").open(encoding="utf-8") as stream:
            after = json.load(stream)
        self.assertEqual(before["published_at"], result["published_at"])
        self.assertEqual(before["source"]["last_refreshed"], result["source_last_refreshed"])
        self.assertEqual(before, after)

    def test_corrupt_snapshot_is_blocked(self) -> None:
        # Keep the test fixture under the writable repository root; Windows
        # sandbox temp directories can be readable but not writable.
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            data_dir = Path(temp)
            shutil.copy2(ROOT / "docs/data/snapshot.json", data_dir / "snapshot.json")
            shutil.copy2(ROOT / "docs/data/establishments.csv", data_dir / "establishments.csv")
            raw = (data_dir / "snapshot.json").read_bytes()
            (data_dir / "snapshot.json").write_bytes(raw[:-1])
            with self.assertRaises(SnapshotIntegrityError):
                validate_snapshot_integrity(data_dir)

    def test_ordinary_three_hour_freshness_boundary_is_unchanged(self) -> None:
        now = datetime(2026, 11, 1, 22, 0, tzinfo=timezone.utc)
        self.assertTrue(is_snapshot_fresh(now - timedelta(hours=3), now))
        self.assertFalse(is_snapshot_fresh(now - timedelta(hours=3, seconds=1), now))
        # This matches the existing ordinary verifier's comparison behavior.
        self.assertTrue(is_snapshot_fresh(now + timedelta(minutes=1), now))

    def test_publisher_tree_provenance_check_uses_a_synthetic_history(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            repo = Path(temp)
            data = repo / "docs/data"
            data.mkdir(parents=True)
            (data / "snapshot.json").write_text("{}", encoding="utf-8")
            subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Scarb.TO data publisher"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
                check=True,
            )
            subprocess.run(["git", "-C", str(repo), "add", "docs/data"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "--quiet", "-m", "data: refresh validated Scarborough DineSafe snapshot"],
                check=True,
            )
            self.assertRegex(validate_publisher_tree(repo), r"^[0-9a-f]{40}$")
            (data / "untracked.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ReleaseError):
                validate_publisher_tree(repo)

    def test_dispatch_requires_main_and_explicit_code_only_event(self) -> None:
        env = {
            "GITHUB_REPOSITORY": "justinpfisher/ScarbTO",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_SHA": "a" * 40,
        }
        self.assertEqual(validate_dispatch_environment(env), "a" * 40)
        for key, value in (("GITHUB_REF", "refs/heads/feature"), ("GITHUB_EVENT_NAME", "push")):
            invalid = dict(env)
            invalid[key] = value
            with self.subTest(key=key), self.assertRaises(ReleaseError):
                validate_dispatch_environment(invalid)

    def test_workflow_keeps_tests_and_normal_refresh_path(self) -> None:
        workflow = (ROOT / ".github/workflows/refresh-and-publish.yml").read_text(encoding="utf-8")
        self.assertIn("default: refresh", workflow)
        self.assertIn("needs: test", workflow)
        self.assertIn("if: inputs.release_mode != 'code_only'", workflow)
        self.assertIn("if: inputs.release_mode == 'code_only'", workflow)
        self.assertIn("run: python scripts/update_dinesafe.py", workflow)
        self.assertIn("run: python scripts/verify_snapshot.py", workflow)
        self.assertIn("run: python scripts/verify_code_only_release.py", workflow)
        self.assertIn("run: python scripts/verify_live_overlay.py", workflow)


if __name__ == "__main__":
    unittest.main()
