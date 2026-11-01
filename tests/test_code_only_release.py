from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
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
            (repo / "README.md").write_text("trusted main base\n", encoding="utf-8")
            subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "fixture"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "fixture@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "-m", "base"], check=True)
            data = repo / "docs/data"
            data.mkdir(parents=True)
            (data / "snapshot.json").write_text("{}", encoding="utf-8")
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
            commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD:docs/data"], text=True).strip()
            parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^"], text=True).strip()
            committed_at = subprocess.check_output(["git", "-C", str(repo), "show", "-s", "--format=%cI", "HEAD"], text=True).strip()
            timestamp = datetime.fromisoformat(committed_at.replace("Z", "+00:00"))
            run = {
                "id": 123,
                "run_attempt": 1,
                "path": ".github/workflows/refresh-and-publish.yml",
                "head_sha": parent,
                "head_branch": "main",
                "status": "completed",
                "conclusion": "success",
                "event": "push",
                "run_started_at": (timestamp - timedelta(minutes=1)).isoformat(),
                "updated_at": (timestamp + timedelta(minutes=1)).isoformat(),
            }
            job = {
                "name": "publish",
                "status": "completed",
                "conclusion": "success",
                "steps": [
                    {"name": name, "status": "completed", "conclusion": "success"}
                    for name in (
                        "Retrieve and validate official Toronto data",
                        "Validate output is public and usable",
                        "Persist only validated data and recoverable release baseline",
                        "Deploy last validated snapshot",
                        "Verify Scarb.TO production HTTP response and official boundary assets",
                    )
                ],
            }

            def api_response(path: str) -> dict:
                if "/workflows/" in path:
                    return {"total_count": 1, "workflow_runs": [run]}
                return {"total_count": 1, "jobs": [job]}

            with patch("scripts.verify_code_only_release._github_api_json", side_effect=api_response):
                result = validate_publisher_tree(repo, expected={"commit": commit, "tree": tree, "run_id": 123})
            self.assertEqual(result["commit"], commit)
            self.assertEqual(result["run_id"], 123)
            (data / "untracked.json").write_text("{}", encoding="utf-8")
            with patch("scripts.verify_code_only_release._github_api_json", side_effect=api_response):
                with self.assertRaises(ReleaseError):
                    validate_publisher_tree(repo, expected={"commit": commit, "tree": tree, "run_id": 123})

    def test_forged_bot_commit_metadata_without_successful_run_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Scarb.TO data publisher"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
                check=True,
            )
            (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "seed.txt"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "-m", "seed"], check=True)
            data = repo / "docs/data"
            data.mkdir(parents=True)
            (data / "snapshot.json").write_text("{}", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "docs/data"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "--quiet", "-m", "data: refresh validated Scarborough DineSafe snapshot"],
                check=True,
            )
            commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD:docs/data"], text=True).strip()
            with patch(
                "scripts.verify_code_only_release._github_api_json",
                return_value={"total_count": 0, "workflow_runs": []},
            ):
                with self.assertRaisesRegex(ReleaseError, "No unique successful workflow run"):
                    validate_publisher_tree(repo, expected={"commit": commit, "tree": tree, "run_id": 123})

    def test_fabricated_sibling_with_matching_parent_metadata_and_run_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "base"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "base@example.invalid"], check=True)
            (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "seed.txt"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "-m", "base"], check=True)
            parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            data = repo / "docs/data"
            data.mkdir(parents=True)
            (data / "snapshot.json").write_text("verified snapshot", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Scarb.TO data publisher"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
                check=True,
            )
            env = dict(os.environ)
            env["GIT_AUTHOR_DATE"] = "2026-11-01T16:51:45+00:00"
            env["GIT_COMMITTER_DATE"] = "2026-11-01T16:51:45+00:00"
            subprocess.run(["git", "-C", str(repo), "add", "docs/data"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "--quiet", "-m", "data: refresh validated Scarborough DineSafe snapshot"],
                check=True,
                env=env,
            )
            verified = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            verified_tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD:docs/data"], text=True).strip()
            verified_time = subprocess.check_output(["git", "-C", str(repo), "show", "-s", "--format=%cI", "HEAD"], text=True).strip()
            subprocess.run(["git", "-C", str(repo), "checkout", "--quiet", parent], check=True)
            data.mkdir(parents=True, exist_ok=True)
            (data / "snapshot.json").write_text("fabricated sibling", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "docs/data"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "--quiet", "-m", "data: refresh validated Scarborough DineSafe snapshot"],
                check=True,
                env=env,
            )
            sibling = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            sibling_parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^"], text=True).strip()
            sibling_time = subprocess.check_output(["git", "-C", str(repo), "show", "-s", "--format=%cI", "HEAD"], text=True).strip()
            self.assertEqual(sibling_parent, parent)
            self.assertEqual(sibling_time, verified_time)
            self.assertNotEqual(sibling, verified)
            with patch("scripts.verify_code_only_release._github_api_json") as api:
                with self.assertRaisesRegex(ReleaseError, "not the independently verified release baseline"):
                    validate_publisher_tree(
                        repo,
                        expected={"commit": verified, "tree": verified_tree, "run_id": 123},
                    )
            api.assert_not_called()

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
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("if: inputs.release_mode != 'code_only'", workflow)
        self.assertIn("if: inputs.release_mode == 'code_only'", workflow)
        self.assertIn("run: python scripts/update_dinesafe.py", workflow)
        self.assertIn("run: python scripts/verify_snapshot.py", workflow)
        self.assertIn("run: python scripts/verify_code_only_release.py", workflow)
        self.assertIn("run: python scripts/verify_live_overlay.py", workflow)


if __name__ == "__main__":
    unittest.main()
