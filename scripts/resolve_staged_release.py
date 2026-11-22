"""Select the unchanged-data path for one independently pinned release projection."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

BASE = "35334d6d2cc47aaf0a2dbf8b98b497a54ea89369"
CLAIM = "[scarb-stage:community-copy-limits-recovery-v1]"
BROWSER_TEST = "tests/browser.integration.test.mjs"
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
    "docs/community-editor.mjs": "a6af88ffb8d145ba43e821c725ce0ba7dad29f18",
    "docs/community-publishing.mjs": "48c52d9c9960d0e4c870d8a39f84eac5c1db3d38",
    "docs/community/index.html": "93804c11a87215179971c553587a3a4dad77eb01",
    "docs/reader-date.mjs": "2d8aaf7251a2748cfcc500815da64da3e261b27a",
    "scripts/build_community_publishing.py": "d60c3d50b07eb01c89dfc3e71687544bbdc98a12",
    "scripts/verify_code_only_release.py": "c26843e11e06cedfe83b247c15b05e3d40b0157a",
    "tests/browser.integration.test.mjs": "060e002d4671c6ea3ee1fe491eae8219423e073c",
    "tests/community-publishing.test.mjs": "62e26430b90817ac7e79b7f76b18a13652871a81",
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
        or any(_git(repo, "rev-parse", f"HEAD:{path}") != tree for path, tree in PROTECTED_TREES.items())
    ):
        raise StageError("Claimed Community copy-limit recovery does not match the required exact main push")
    changed = set(_git(repo, "diff", "--name-only", "--no-renames", BASE, sha).splitlines())
    if changed != {SELF, BROWSER_TEST}:
        raise StageError("Claimed Community copy-limit recovery has unexpected accompanying changes")
    for path, blob in PROJECTION.items():
        if _git(repo, "ls-tree", sha, "--", path) != f"100644 blob {blob}\t{path}":
            raise StageError(f"Claimed Community copy-limit recovery has non-approved bytes or mode: {path}")
    if not re.fullmatch(r"100644 blob [0-9a-f]{40}\t" + re.escape(SELF),
                        _git(repo, "ls-tree", sha, "--", SELF)):
        raise StageError("Claimed Community copy-limit recovery resolver is not a regular committed source file")
    if _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise StageError("Claimed Community copy-limit recovery checkout contains uncommitted input")
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
