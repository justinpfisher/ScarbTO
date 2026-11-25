from __future__ import annotations

import json
from copy import deepcopy
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
    PINNED_BASELINE,
    PRODUCER_STEPS,
    DEPLOY_STEPS,
    _verify_successful_publisher_run,
    ReleaseError,
    validate_dispatch_environment,
    validate_publisher_tree,
)

ROOT = Path(__file__).resolve().parents[1]


class CodeOnlyReleaseTests(unittest.TestCase):
    def test_pinned_baseline_matches_latest_verified_publisher(self) -> None:
        self.assertEqual(
            PINNED_BASELINE,
            {
                "commit": "08af44cd8ba935a9752bf665d2100ad898668e61",
                "tree": "650a9120c3c5a8a8495a9183669e5dbe2f959076",
                "run_id": 44593838514,
            },
        )

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
                "run_id": 123,
                "run_attempt": 1,
                "head_sha": parent,
                "name": "publish",
                "status": "completed",
                "conclusion": "success",
                "steps": [
                    {"name": name, "status": "completed", "conclusion": "success"}
                    for name in (
                        "Retrieve and validate official Toronto data",
                        "Validate output is public and usable",
                        "Persist only validated data and recoverable release baseline",
                        "Run actions/upload-pages-artifact@v3",
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

    def test_legacy_and_split_receipts_are_attempt_scoped_and_fail_closed(self) -> None:
        parent = "a" * 40
        timestamp = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
        run = {
            "id": 123, "run_attempt": 2, "head_sha": parent,
            "path": ".github/workflows/refresh-and-publish.yml",
            "head_branch": "main", "event": "schedule",
            "status": "completed", "conclusion": "success",
            "run_started_at": (timestamp - timedelta(minutes=1)).isoformat(),
            "updated_at": (timestamp + timedelta(minutes=1)).isoformat(),
        }

        def job(name: str, names: set[str]) -> dict:
            return {
                "name": name, "run_id": 123, "run_attempt": 2, "head_sha": parent,
                "status": "completed", "conclusion": "success",
                "steps": [{"name": name, "status": "completed", "conclusion": "success"}
                          for name in sorted(names)],
            }

        legacy = [job("publish", PRODUCER_STEPS | DEPLOY_STEPS)]
        split = [job("publish", PRODUCER_STEPS), job("deploy", DEPLOY_STEPS)]

        def verify(jobs: list[dict], total: int | None = None) -> int:
            def api(path: str) -> dict:
                if "/workflows/" in path:
                    return {"total_count": 1, "workflow_runs": [run]}
                self.assertEqual(path, "/repos/justinpfisher/ScarbTO/actions/runs/123/attempts/2/jobs?per_page=100")
                return {"total_count": len(jobs) if total is None else total, "jobs": jobs}
            with patch("scripts.verify_code_only_release._github_api_json", side_effect=api):
                return _verify_successful_publisher_run(parent, timestamp)

        for label, receipt in (("legacy", legacy), ("split", split)):
            with self.subTest(layout=label, case="valid"):
                self.assertEqual(verify(deepcopy(receipt)), 123)
            # Each required operation must occur exactly once, successfully,
            # in its own named job, not merely somewhere in the run.
            for index, original in enumerate(receipt):
                for step_index, step in enumerate(original["steps"]):
                    for failure in ("absent", "skipped", "failure", "duplicate", "unrelated"):
                        bad = deepcopy(receipt)
                        steps = bad[index]["steps"]
                        if failure == "absent":
                            del steps[step_index]
                        elif failure == "duplicate":
                            steps.append(deepcopy(steps[step_index]))
                        elif failure == "unrelated":
                            removed = steps.pop(step_index)
                            bad.append(job("unrelated", set()))
                            bad[-1]["steps"] = [removed]
                        else:
                            steps[step_index]["conclusion"] = failure
                        with self.subTest(layout=label, step=step["name"], failure=failure):
                            with self.assertRaises(ReleaseError):
                                verify(bad)
                for field, value in (("run_id", 456), ("run_attempt", 1),
                                     ("head_sha", "b" * 40), ("status", "in_progress"),
                                     ("conclusion", "skipped"), ("name", "unrelated")):
                    bad = deepcopy(receipt)
                    bad[index][field] = value
                    with self.subTest(layout=label, job=index, field=field):
                        with self.assertRaises(ReleaseError):
                            verify(bad)
                bad = deepcopy(receipt)
                bad.append(deepcopy(bad[index]))
                with self.subTest(layout=label, duplicate_job=index):
                    with self.assertRaises(ReleaseError):
                        verify(bad)
            with self.subTest(layout=label, case="incomplete_page"):
                with self.assertRaises(ReleaseError):
                    verify(receipt, len(receipt) + 1)
        for bad in ([], [split[0]], [split[1]], legacy + [split[1]],
                    [split[0], job("deploy", PRODUCER_STEPS | DEPLOY_STEPS)]):
            with self.subTest(case="missing_or_mixed_layout", receipt=bad):
                with self.assertRaises(ReleaseError):
                    verify(bad)

    def test_split_workflow_preserves_protected_persistence_and_exact_consumer(self) -> None:
        workflow = (ROOT / ".github/workflows/refresh-and-publish.yml").read_text(encoding="utf-8")
        before, consumer = workflow.split("\n  deploy:\n")
        test, producer = before.split("\n  publish:\n")
        self.assertIn("needs: test", producer)
        self.assertIn("needs: publish", consumer)
        self.assertIn("      - scarbto-gmktec", test)
        self.assertIn("      - Windows", test)
        self.assertEqual(workflow.count("group: scarbto-pages"), 1)
        self.assertIn("cancel-in-progress: false", workflow)
        for block in (producer, consumer):
            self.assertIn("github.event_name != 'pull_request' && github.ref == 'refs/heads/main'", block)
            self.assertIn("    environment:\n      name: github-pages\n", block)
        self.assertIn("      deployment: false", producer)
        self.assertNotIn("      url:", producer)
        self.assertNotIn("deployment: false", consumer)
        self.assertIn("      url: ${{ steps.deployment.outputs.page_url }}", consumer)
        self.assertIn("      contents: write", producer)
        self.assertNotIn("pages: write", producer)
        self.assertNotIn("id-token: write", producer)
        self.assertIn("    permissions:\n      contents: read\n      pages: write\n      id-token: write\n", consumer)
        self.assertIn("          ref: ${{ github.sha }}\n          persist-credentials: false", consumer)
        self.assertIn("uses: actions/setup-python@v5", consumer)
        self.assertIn("python-version: '3.12'", consumer)
        upload = "      - uses: actions/upload-pages-artifact@v3\n        with:\n          path: docs\n"
        self.assertEqual(workflow.count(upload), 1)
        self.assertIn(upload, producer)
        self.assertIn("git push origin HEAD:main", producer)
        self.assertNotIn("git push", consumer)
        self.assertLess(producer.index("git push origin HEAD:main"), producer.index(upload))
        for action in ("actions/configure-pages@v5", "actions/deploy-pages@v4"):
            self.assertEqual(workflow.count(action), 1)
            self.assertIn(action, consumer)
        self.assertLess(consumer.index("actions/configure-pages@v5"), consumer.index("actions/deploy-pages@v4"))
        self.assertIn('run: python scripts/verify_live_overlay.py "${{ github.sha }}"', consumer)
        self.assertNotIn("verify_live_overlay.py", producer)

    def test_workflow_keeps_tests_and_normal_refresh_path(self) -> None:
        workflow = (ROOT / ".github/workflows/refresh-and-publish.yml").read_text(encoding="utf-8")
        self.assertIn("default: refresh", workflow)
        self.assertIn("needs: test", workflow)
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("MANUAL_RELEASE_MODE: ${{ inputs.release_mode }}", workflow)
        self.assertEqual(workflow.count("inputs.release_mode"), 1)
        self.assertEqual(workflow.count("steps.release-mode.outputs.mode"), 6)
        self.assertEqual(workflow.count("if: steps.release-mode.outputs.mode != 'code_only'"), 2)
        self.assertEqual(workflow.count("if: steps.release-mode.outputs.mode == 'code_only'"), 1)
        self.assertLess(workflow.index("id: release-mode"),
                        workflow.index("run: python scripts/update_dinesafe.py"))
        self.assertIn("run: python scripts/update_dinesafe.py", workflow)
        self.assertIn("run: python scripts/verify_snapshot.py", workflow)
        self.assertIn("run: python scripts/verify_code_only_release.py", workflow)
        self.assertIn("run: python scripts/verify_live_overlay.py", workflow)


if __name__ == "__main__":
    unittest.main()
