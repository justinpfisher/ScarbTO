#!/usr/bin/env python3
"""Safely publish code with the unchanged last-good DineSafe data tree."""
from __future__ import annotations

import os
import http.client
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

try:  # Support both `python scripts/...` and unittest package imports.
    from .snapshot_integrity import SnapshotIntegrityError, validate_snapshot_integrity
except ImportError:
    from snapshot_integrity import SnapshotIntegrityError, validate_snapshot_integrity

PUBLISHER = "Scarb.TO data publisher"
PUBLISHER_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
PUBLISH_SUBJECT = "data: refresh validated Scarborough DineSafe snapshot"
WORKFLOW_PATH = ".github/workflows/refresh-and-publish.yml"
REQUIRED_PUBLISH_STEPS = {
    "Retrieve and validate official Toronto data",
    "Validate output is public and usable",
    "Persist only validated data and recoverable release baseline",
    "Deploy last validated snapshot",
    "Verify Scarb.TO production HTTP response and official boundary assets",
}
MAX_API_BYTES = 1_000_000
# Exact last-good baseline independently verified for this code-only rollout.
# Update only alongside a separately verified successful publisher run.
PINNED_BASELINE = {
    "commit": "e15bdcd3f922f918a0090df0209b0c8497ed5460",
    "tree": "2cb70e87eab0cb92601150a2d43e002f41fa87ec",
    "run_id": 41328319131,
}


class ReleaseError(ValueError):
    pass


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=False, capture_output=True, text=True
    )
    if result.returncode:
        raise ReleaseError("Unable to verify repository history for code-only release")
    return result.stdout.strip()


def _github_api_json(path: str) -> dict:
    """Read bounded public workflow evidence over normal TLS, without credentials."""
    if not path.startswith("/repos/justinpfisher/ScarbTO/actions/") or "#" in path:
        raise ReleaseError("Unexpected GitHub workflow evidence path")
    connection = http.client.HTTPSConnection("api.github.com", timeout=10)
    try:
        connection.request(
            "GET",
            path,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ScarbTO-code-only-release-verifier",
            },
        )
        response = connection.getresponse()
        if response.status != 200 or "application/json" not in (response.getheader("Content-Type") or ""):
            raise ReleaseError("GitHub public workflow evidence is unavailable")
        body = response.read(MAX_API_BYTES + 1)
        if len(body) > MAX_API_BYTES:
            raise ReleaseError("GitHub public workflow evidence exceeds the response limit")
        try:
            value = json.loads(body)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ReleaseError("GitHub public workflow evidence is invalid JSON") from exc
        if not isinstance(value, dict):
            raise ReleaseError("GitHub public workflow evidence has an unexpected shape")
        return value
    except (OSError, http.client.HTTPException):
        raise ReleaseError("GitHub public workflow provenance lookup failed") from None
    finally:
        connection.close()


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ReleaseError("Publisher timestamp metadata is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReleaseError("Publisher timestamp metadata is malformed") from exc
    if parsed.tzinfo is None:
        raise ReleaseError("Publisher timestamp metadata lacks a timezone")
    return parsed.astimezone(timezone.utc)


def _verify_successful_publisher_run(parent_sha: str, commit_time: datetime) -> int:
    if len(parent_sha) != 40 or any(ch not in "0123456789abcdef" for ch in parent_sha):
        raise ReleaseError("Publisher commit parent is malformed")
    # Bound the public search to the UTC day around the data commit. A missing,
    # paginated, ambiguous, or unavailable record fails closed.
    day = commit_time.date()
    lower = (day - timedelta(days=1)).isoformat()
    upper = (day + timedelta(days=1)).isoformat()
    query = urlencode({"head_sha": parent_sha, "created": f"{lower}..{upper}", "per_page": 100})
    runs_response = _github_api_json(
        f"/repos/justinpfisher/ScarbTO/actions/workflows/refresh-and-publish.yml/runs?{query}"
    )
    runs = runs_response.get("workflow_runs")
    total = runs_response.get("total_count")
    if not isinstance(runs, list) or type(total) is not int or total != len(runs):
        raise ReleaseError("GitHub workflow run list is incomplete")
    matching: list[dict] = []
    for run in runs:
        if not isinstance(run, dict):
            raise ReleaseError("GitHub workflow run evidence is malformed")
        if (
            run.get("path") == WORKFLOW_PATH
            and run.get("head_sha") == parent_sha
            and run.get("head_branch") == "main"
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            and run.get("event") in {"schedule", "push", "workflow_dispatch"}
        ):
            started = _timestamp(run.get("run_started_at"))
            completed = _timestamp(run.get("updated_at"))
            if started <= commit_time <= completed:
                matching.append(run)
    if len(matching) != 1:
        raise ReleaseError("No unique successful workflow run proves the last-good data commit")
    run = matching[0]
    run_id = run.get("id")
    attempt = run.get("run_attempt")
    if type(run_id) is not int or type(attempt) is not int or attempt < 1:
        raise ReleaseError("Successful publisher workflow identity is malformed")
    jobs_response = _github_api_json(
        f"/repos/justinpfisher/ScarbTO/actions/runs/{run_id}/jobs?{urlencode({'per_page': 100})}"
    )
    jobs = jobs_response.get("jobs")
    job_total = jobs_response.get("total_count")
    if not isinstance(jobs, list) or type(job_total) is not int or job_total != len(jobs):
        raise ReleaseError("GitHub workflow job evidence is incomplete")
    publishers = [job for job in jobs if isinstance(job, dict) and job.get("name") == "publish"]
    if len(publishers) != 1:
        raise ReleaseError("Successful refresh run has no unique publisher job")
    publisher = publishers[0]
    if publisher.get("status") != "completed" or publisher.get("conclusion") != "success":
        raise ReleaseError("Last-good publisher job did not complete successfully")
    steps = publisher.get("steps")
    if not isinstance(steps, list):
        raise ReleaseError("Publisher workflow step evidence is missing")
    successful_steps = {
        step.get("name")
        for step in steps
        if isinstance(step, dict) and step.get("status") == "completed" and step.get("conclusion") == "success"
    }
    if not REQUIRED_PUBLISH_STEPS.issubset(successful_steps):
        raise ReleaseError("Publisher run lacks successful retrieval, validation, persistence, or deployment evidence")
    return run_id


def validate_publisher_tree(
    repo: str | Path, *, expected: dict[str, str | int] | None = None
) -> dict[str, str | int]:
    """Require current docs/data to match a successful, independently recorded publisher run."""
    root = Path(repo)
    checkpoint = expected if expected is not None else PINNED_BASELINE
    if _git(root, "rev-parse", "--is-shallow-repository") != "false":
        raise ReleaseError("Full repository history is required to verify snapshot provenance")
    if _git(root, "status", "--porcelain", "--untracked-files=all", "--", "docs/data"):
        raise ReleaseError("Working tree contains uncommitted or untracked docs/data files")
    record = _git(
        root,
        "log",
        "-1",
        "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%s%x00%cI%x00%P",
        "--",
        "docs/data",
    )
    parts = record.split("\x00")
    if len(parts) != 8 or parts[1:6] != [PUBLISHER, PUBLISHER_EMAIL, PUBLISHER, PUBLISHER_EMAIL, PUBLISH_SUBJECT]:
        raise ReleaseError("Latest docs/data change is not a validated publisher commit")
    commit = parts[0]
    if commit != checkpoint.get("commit"):
        raise ReleaseError("Last-good data commit is not the independently verified release baseline")
    parents = parts[7].split()
    if len(parents) != 1:
        raise ReleaseError("Last-good data commit has unexpected ancestry")
    run_id = _verify_successful_publisher_run(parents[0], _timestamp(parts[6]))
    published_tree = _git(root, "rev-parse", f"{commit}:docs/data")
    current_tree = _git(root, "rev-parse", "HEAD:docs/data")
    if published_tree != checkpoint.get("tree") or current_tree != checkpoint.get("tree"):
        raise ReleaseError("Last-good data tree does not match the independently verified release baseline")
    if published_tree != current_tree:
        raise ReleaseError("docs/data differs from the last validated publisher snapshot")
    if run_id != checkpoint.get("run_id"):
        raise ReleaseError("Publisher run does not match the independently verified release baseline")
    return {"commit": commit, "tree": current_tree, "run_id": run_id}


def validate_dispatch_environment(environ: dict[str, str]) -> str:
    if environ.get("GITHUB_REPOSITORY") != "justinpfisher/ScarbTO":
        raise ReleaseError("Code-only release is restricted to justinpfisher/ScarbTO")
    if environ.get("GITHUB_REF") != "refs/heads/main":
        raise ReleaseError("Code-only release is restricted to the main branch")
    if environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise ReleaseError("Code-only release requires an explicit workflow dispatch")
    expected_sha = environ.get("GITHUB_SHA", "").lower()
    if len(expected_sha) != 40 or any(ch not in "0123456789abcdef" for ch in expected_sha):
        raise ReleaseError("Workflow commit identity is missing or malformed")
    return expected_sha


def verify(repo: str | Path, environ: dict[str, str]) -> dict[str, object]:
    root = Path(repo)
    expected_sha = validate_dispatch_environment(environ)
    actual_sha = _git(root, "rev-parse", "HEAD").lower()
    if actual_sha != expected_sha:
        raise ReleaseError("Checked-out code does not match the dispatched main commit")
    publisher = validate_publisher_tree(root)
    summary = validate_snapshot_integrity(root / "docs" / "data")
    summary["data_commit"] = publisher["commit"]
    summary["data_tree"] = publisher["tree"]
    summary["publisher_run_id"] = publisher["run_id"]
    return summary


def main() -> int:
    try:
        summary = verify(Path(__file__).resolve().parent.parent, dict(os.environ))
    except (ReleaseError, SnapshotIntegrityError) as exc:
        print(f"Code-only release blocked: {exc}", file=sys.stderr)
        return 1
    # Deliberately print only provenance and counts, never public row contents.
    print(
        "Verified unchanged data tree from "
        f"{summary['data_commit']} (tree={summary['data_tree']}, "
        f"successful publisher run={summary['publisher_run_id']}); "
        f"published_at={summary['published_at']}; "
        f"source_last_refreshed={summary['source_last_refreshed']}; "
        f"establishments={summary['establishments']}; "
        f"activity_records={summary['activity_records']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
