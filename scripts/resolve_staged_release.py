"""Select the unchanged-data path for one independently pinned release projection."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

BASE = "94b0835d9f7465d41736335424b3bf87fc567fc9"
DATA_TREE = "650a9120c3c5a8a8495a9183669e5dbe2f959076"
CLAIM = "[scarb-stage:directory-voice-v2]"
SELF = "scripts/resolve_staged_release.py"
# Git blob identities are of canonical committed bytes, not native worktree bytes.
# The resolver's own exact bytes are independently reviewed as part of the commit,
# not self-hashed. Its workflow and all separate production controls are pinned here.
PROJECTION = {
    ".github/workflows/refresh-and-publish.yml": "8864aea26cbfc4b074d9bbaef9528d52095f1cad",
    "docs/neighbourhoods/index.html": "5488e75958c3be33bd1f675be94c8326d9be814c",
    "scripts/build_neighbourhood_pages.mjs": "1272a68e9b565d3544a5e56dda66bed13090f8ea",
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


def resolve(repo: Path, environ: dict[str, str]) -> str:
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
        or _git(repo, "rev-parse", "HEAD:docs/data") != DATA_TREE
    ):
        raise StageError("Claimed directory stage does not match the required exact main push")
    changed = set(_git(repo, "diff", "--name-only", "--no-renames", BASE, sha).splitlines())
    if changed != {SELF, "docs/neighbourhoods/index.html", "scripts/build_neighbourhood_pages.mjs"}:
        raise StageError("Claimed directory stage has unexpected accompanying changes")
    for path, blob in PROJECTION.items():
        if _git(repo, "ls-tree", sha, "--", path) != f"100644 blob {blob}\t{path}":
            raise StageError(f"Claimed directory stage has non-approved bytes or mode: {path}")
    if not re.fullmatch(r"100644 blob [0-9a-f]{40}\t" + re.escape(SELF),
                        _git(repo, "ls-tree", sha, "--", SELF)):
        raise StageError("Claimed directory stage resolver is not a regular committed source file")
    if _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise StageError("Claimed directory stage checkout contains uncommitted input")
    return "code_only"


def main() -> int:
    try:
        mode = resolve(Path(__file__).resolve().parent.parent, dict(os.environ))
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"mode={mode}\n")
    except (StageError, KeyError, OSError) as exc:
        print(f"Release mode blocked: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
