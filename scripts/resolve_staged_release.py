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


RSS_BASE = "6cf293fcd50eeb6021721ba191e061345f246ec8"
RSS_CLAIM = "[scarb-stage:rss-stable-date-v1]"
RSS_PROJECTION = {
    ".github/workflows/refresh-and-publish.yml": "5476ff720dfd60ad3535b7564c75dfa583d764d1",
    "scripts/build_rss.py": "17c0816193cc038abc5e957dafcd0c65ec799100",
    "scripts/verify_code_only_release.py": "c26843e11e06cedfe83b247c15b05e3d40b0157a",
    "tests/test_build_rss.py": "be3224146f786bd5eb9ae9dbba81bd0ffb790e30",
    "tests/test_code_only_release.py": "502ffc7041e07f85a8db3f93e2aba227301171d4",
}
RSS_CHANGED = {SELF, ".github/workflows/refresh-and-publish.yml", "scripts/build_rss.py", "tests/test_build_rss.py"}


MOBILE_BASE = "13b67e0b5afb1a71842f1cf1ad042ba4e7cb4455"
MOBILE_CLAIM = "[scarb-stage:mobile-search-topics-v1]"
MOBILE_PROJECTION = {
    ".github/workflows/refresh-and-publish.yml": "5476ff720dfd60ad3535b7564c75dfa583d764d1",
    "docs/app.mjs": "871aa280aba39d80eba872d61f125c5ed0a45801",
    "docs/index.html": "dbcf17e5fd77c771edbb4f9c976e0dc3e456d539",
    "docs/styles.css": "ccbbb8102a830e1986b353c835898995ab88d789",
    "scripts/verify_code_only_release.py": "c26843e11e06cedfe83b247c15b05e3d40b0157a",
    "tests/browser.integration.test.mjs": "0d78c89922639c24bd38b0bc6dacd419cab6374c",
    "tests/test_code_only_release.py": "502ffc7041e07f85a8db3f93e2aba227301171d4",
}
MOBILE_CHANGED = {SELF, BROWSER_TEST, "docs/app.mjs", "docs/index.html", "docs/styles.css"}


LATEST_INSPECTION_BASE = "60e19cee52f64f8860f9ab7c31c678bf24df9445"
LATEST_INSPECTION_CLAIM = "[scarb-stage:latest-inspection-widget-print-v1]"
LATEST_INSPECTION_PROTECTED_TREES = {
    "docs/data": "b1a41ca26235dab25c74b57d02ce5f719f135159",
    "docs/briefs": "956f4729ce6a9e3aa84cc77d647b3d1143f8720a",
    "docs/community-data": "e0344eb810e69c6463779c0d3221ce66a9e2ceaa",
}
LATEST_INSPECTION_PROJECTION = {
    ".github/workflows/refresh-and-publish.yml": "1ff19728c6f038dac66c9649e121f3c00f5f8a96",
    "COMMUNITY_PUBLISHING.md": "8a16d83e8466d3f3265f359ea94e07a74081a97f",
    "docs/community-editor.mjs": "b3b64b09a84b10d0da25451060c7a07b5e3fa506",
    "docs/community-embed.mjs": "16c04dc06797d65cddd387b032bc48698a3e0965",
    "docs/community-exports.mjs": "015ff066c6c8f5f7034f86dde840934c2d9a46a9",
    "docs/community-latest.mjs": "cff5e2f3ed360fb5c957d038e20aa086115eea50",
    "docs/community/index.html": "e0661be7585989268f63dc882fa88fb400cca7b0",
    "docs/embed/index.html": "06073840b6e949d56880e6bfb119e4ed7ac07988",
    "scripts/verify_code_only_release.py": "47784c9ac62ae711b1bddfca51c8bbac8d14fa32",
    "tests/community-browser.mjs": "5156b91f0503e7a9ea92d427928a4e17b4c20e18",
    "tests/community-publishing.test.mjs": "f224c2040fcb51aaafa65a3064ea9d128d0588cb",
    "tests/test_code_only_release.py": "f5e31ad0ee6fbed6fc1e8338ec8ed00ce8fde52f",
}
LATEST_INSPECTION_CHANGED = {SELF, *LATEST_INSPECTION_PROJECTION} - {
    ".github/workflows/refresh-and-publish.yml",
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
    recovery_claimed = CLAIM in message
    rss_claimed = RSS_CLAIM in message
    mobile_claimed = MOBILE_CLAIM in message
    latest_inspection_claimed = LATEST_INSPECTION_CLAIM in message
    if sum((recovery_claimed, rss_claimed, mobile_claimed, latest_inspection_claimed)) > 1:
        raise StageError("Push contains conflicting staged release markers")
    protected_trees = PROTECTED_TREES
    if latest_inspection_claimed:
        base = LATEST_INSPECTION_BASE
        projection = LATEST_INSPECTION_PROJECTION
        expected_changed = LATEST_INSPECTION_CHANGED
        protected_trees = LATEST_INSPECTION_PROTECTED_TREES
        stage = "Latest inspection widget and print stage"
    elif mobile_claimed:
        base, projection, expected_changed = MOBILE_BASE, MOBILE_PROJECTION, MOBILE_CHANGED
        stage = "Mobile search and topics stage"
    elif rss_claimed:
        base, projection, expected_changed = RSS_BASE, RSS_PROJECTION, RSS_CHANGED
        stage = "RSS stage"
    elif recovery_claimed:
        base, projection, expected_changed = BASE, PROJECTION, {SELF, BROWSER_TEST}
        stage = "Community copy-limit recovery"
    else:
        return "refresh"
    sha = environ.get("GITHUB_SHA", "")
    if (
        environ.get("GITHUB_REPOSITORY") != "justinpfisher/ScarbTO"
        or environ.get("GITHUB_REF") != "refs/heads/main"
        or payload.get("ref") != "refs/heads/main"
        or payload.get("before") != base
        or payload.get("after") != sha
        or head_commit.get("id") != sha
        or payload.get("forced") is not False
        or not re.fullmatch(r"[0-9a-f]{40}", sha)
        or _git(repo, "rev-list", "--parents", "-n", "1", "HEAD") != f"{sha} {base}"
        or any(_git(repo, "rev-parse", f"HEAD:{path}") != tree for path, tree in protected_trees.items())
    ):
        raise StageError(f"Claimed {stage} does not match the required exact main push")
    changed = set(_git(repo, "diff", "--name-only", "--no-renames", base, sha).splitlines())
    if changed != expected_changed:
        raise StageError(f"Claimed {stage} has unexpected accompanying changes")
    for path, blob in projection.items():
        if _git(repo, "ls-tree", sha, "--", path) != f"100644 blob {blob}\t{path}":
            raise StageError(f"Claimed {stage} has non-approved bytes or mode: {path}")
    if not re.fullmatch(r"100644 blob [0-9a-f]{40}\t" + re.escape(SELF),
                        _git(repo, "ls-tree", sha, "--", SELF)):
        raise StageError(f"Claimed {stage} resolver is not a regular committed source file")
    if _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise StageError(f"Claimed {stage} checkout contains uncommitted input")
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
