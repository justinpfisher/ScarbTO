"""Select the unchanged-data path for one independently pinned release projection."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

if __package__:
    from . import scarb_notebook_release as notebook
else:
    import scarb_notebook_release as notebook

# Enroll only an exact independently verified private stage and public projection.
NOTEBOOK_APPROVAL = None

BASE = "622a82fdf5c8b35f29cdd3e1831a25d8d15da048"
CLAIM = "[scarb-stage:finding-wording-v2]"
APPLICATION = "docs/inspection-translations.mjs"
PROTECTED_TREES = {
    "docs/data": "650a9120c3c5a8a8495a9183669e5dbe2f959076",
    "docs/briefs": "39b3b3c95ff0eaf3271711f46e0e8a95f0158edd",
    "docs/community-data": "bb67fc65a5a4f0d757056400002a92325c27b731",
}
SELF = "scripts/resolve_staged_release.py"
# Git blob identities are of canonical committed bytes, not native worktree bytes.
# The resolver's own exact bytes are independently reviewed as part of the commit,
# not self-hashed. Its workflow and all separate production controls are pinned here.
PROJECTION = {
    ".github/workflows/refresh-and-publish.yml": "8864aea26cbfc4b074d9bbaef9528d52095f1cad",
    "docs/app.mjs": "f74f37883a38691745eea083f841bb6775c11a35",
    "docs/inspection-findings.mjs": "1d90f1aa060efa2fffa8638d5e3bebab36232153",
    "docs/inspection-translations.mjs": "897a8d887bf2733404cba3d9824d046ad250cb24",
    "docs/neighbourhood-page.mjs": "13b26c60f614695b85e366062c6d2aed5c9b3b27",
    "scripts/verify_code_only_release.py": "c26843e11e06cedfe83b247c15b05e3d40b0157a",
    "tests/test_code_only_release.py": "502ffc7041e07f85a8db3f93e2aba227301171d4",
}


class StageError(ValueError):
    pass


def _git(repo, *args):
    result = subprocess.run(["git", *args], cwd=repo, check=False, capture_output=True, text=True)
    if result.returncode:
        raise StageError("Cannot verify exact staged commit and data ancestry")
    return result.stdout.strip()


def _approved_notebook(repo):
    try:
        return notebook.approved_output(repo, NOTEBOOK_APPROVAL, _git, PROTECTED_TREES)
    except (notebook.NotebookError, json.JSONDecodeError, UnicodeError) as exc:
        raise StageError(str(exc)) from exc


def apply_notebook(repo):
    approved = _approved_notebook(repo)
    if approved is not None:
        _, path, output = approved
        path.write_bytes(output)


def resolve(repo: Path, environ: dict[str, str]) -> str:
    approved = _approved_notebook(repo)
    event = environ.get("GITHUB_EVENT_NAME")
    if event == "workflow_dispatch":
        return "code_only" if environ.get("MANUAL_RELEASE_MODE") == "code_only" else "refresh"
    if event != "push":
        return "refresh"
    try:
        payload = json.loads(Path(environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        head_commit = payload.get("head_commit") or {}
        message = head_commit.get("message", "")
        if not isinstance(message, str):
            raise TypeError()
    except (AttributeError, KeyError, OSError, TypeError, ValueError) as exc:
        raise StageError("Cannot verify authenticated push event") from exc
    if notebook.CLAIM in message:
        if approved is None:
            raise StageError("No independently approved Notebook release")
        activation = approved[0]
        if (
            message.count("[scarb-stage:") != 1
            or environ.get("GITHUB_REPOSITORY") != "justinpfisher/ScarbTO"
            or environ.get("GITHUB_REF") != "refs/heads/main"
            or payload.get("ref") != "refs/heads/main"
            or payload.get("before") != NOTEBOOK_APPROVAL["base"]
            or payload.get("after") != activation
            or head_commit.get("id") != activation
            or payload.get("forced") is not False
            or environ.get("GITHUB_SHA") != activation
            or _git(repo, "rev-parse", "HEAD") != activation
            or _git(repo, "show", "-s", "--format=%s", activation) != message.splitlines()[0]
            or _git(repo, "status", "--porcelain", "--untracked-files=all")
        ):
            raise StageError("Claimed Notebook stage does not match the exact main push")
        return "code_only"
    if approved is not None and _git(repo, "rev-parse", "HEAD") == approved[0]:
        raise StageError("The activation push requires the exact Notebook marker")
    if CLAIM not in message:
        return "refresh"
    sha = environ.get("GITHUB_SHA", "")
    if (
        environ.get("GITHUB_REPOSITORY") != "justinpfisher/ScarbTO"
        or environ.get("GITHUB_REF") != "refs/heads/main"
        or payload.get("ref") != "refs/heads/main"
        or payload.get("before") != BASE
        or payload.get("after") != sha
        or head_commit.get("id") != sha
        or payload.get("forced") is not False
        or not re.fullmatch(r"[0-9a-f]{40}", sha)
        or _git(repo, "rev-list", "--parents", "-n", "1", "HEAD") != f"{sha} {BASE}"
        or any(_git(repo, "rev-parse", f"HEAD:{path}") != tree for path, tree in PROTECTED_TREES.items())
    ):
        raise StageError("Claimed finding wording stage does not match the required exact main push")
    changed = set(_git(repo, "diff", "--name-only", "--no-renames", BASE, sha).splitlines())
    if changed != {SELF, APPLICATION, "docs/inspection-findings.mjs"}:
        raise StageError("Claimed finding wording stage has unexpected accompanying changes")
    for path, blob in PROJECTION.items():
        if _git(repo, "ls-tree", sha, "--", path) != f"100644 blob {blob}\t{path}":
            raise StageError(f"Claimed finding wording stage has non-approved bytes or mode: {path}")
    if not re.fullmatch(r"100644 blob [0-9a-f]{40}\t" + re.escape(SELF),
                        _git(repo, "ls-tree", sha, "--", SELF)):
        raise StageError("Claimed finding wording stage resolver is not a regular committed source file")
    if _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise StageError("Claimed finding wording stage checkout contains uncommitted input")
    return "code_only"


def main() -> int:
    try:
        repo = Path(__file__).resolve().parent.parent
        if sys.argv[1:] == ["--apply-notebook"]:
            apply_notebook(repo)
            return 0
        if sys.argv[1:]:
            raise StageError("Unknown release resolver option")
        mode = resolve(repo, dict(os.environ))
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"mode={mode}\n")
    except (StageError, KeyError, OSError) as exc:
        print(f"Release mode blocked: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
