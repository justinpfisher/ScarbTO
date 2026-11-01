#!/usr/bin/env python3
"""Safely publish code with the unchanged last-good DineSafe data tree."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:  # Support both `python scripts/...` and unittest package imports.
    from .snapshot_integrity import SnapshotIntegrityError, validate_snapshot_integrity
except ImportError:
    from snapshot_integrity import SnapshotIntegrityError, validate_snapshot_integrity

PUBLISHER = "Scarb.TO data publisher"
PUBLISH_SUBJECT = "data: refresh validated Scarborough DineSafe snapshot"


class ReleaseError(ValueError):
    pass


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=False, capture_output=True, text=True
    )
    if result.returncode:
        raise ReleaseError("Unable to verify repository history for code-only release")
    return result.stdout.strip()


def validate_publisher_tree(repo: str | Path) -> str:
    """Require current docs/data to be exactly the latest validated publisher tree."""
    root = Path(repo)
    if _git(root, "status", "--porcelain", "--untracked-files=all", "--", "docs/data"):
        raise ReleaseError("Working tree contains uncommitted or untracked docs/data files")
    record = _git(root, "log", "-1", "--format=%H%x00%an%x00%s", "--", "docs/data")
    parts = record.split("\x00")
    if len(parts) != 3 or parts[1:] != [PUBLISHER, PUBLISH_SUBJECT]:
        raise ReleaseError("Latest docs/data change is not a validated publisher commit")
    commit = parts[0]
    published_tree = _git(root, "rev-parse", f"{commit}:docs/data")
    current_tree = _git(root, "rev-parse", "HEAD:docs/data")
    if published_tree != current_tree:
        raise ReleaseError("docs/data differs from the last validated publisher snapshot")
    return commit


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
    data_commit = validate_publisher_tree(root)
    summary = validate_snapshot_integrity(root / "docs" / "data")
    summary["data_commit"] = data_commit
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
        f"{summary['data_commit']}; published_at={summary['published_at']}; "
        f"source_last_refreshed={summary['source_last_refreshed']}; "
        f"establishments={summary['establishments']}; "
        f"activity_records={summary['activity_records']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
