#!/usr/bin/env python3
"""Reject workflows that can select anything except the Scarb.TO GMKtec runner.

This deliberately accepts a small YAML subset for job runner declarations:
each job must use the exact inline runner label list. That keeps matrices,
expressions, and reusable-workflow indirection from weakening the policy.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXPECTED_RUNNER = "[self-hosted, linux, x64, scarbto-gmktec]"
JOB_START = re.compile(r"^  ([A-Za-z0-9_-]+):\s*(?:#.*)?$")
RUNS_ON = re.compile(r"^\s+runs-on:\s*(.*?)\s*(?:#.*)?$", re.IGNORECASE)
MAIN_REF_GUARD = re.compile(
    r"^\s+if:\s*github\.ref\s*==\s*['\"]refs/heads/main['\"]\s*$",
    re.IGNORECASE,
)
REUSABLE_WORKFLOW = re.compile(
    r"^\s+uses:\s*[^\s#]+/\.github/workflows/[^\s#]+@[^\s#]+\s*(?:#.*)?$",
    re.IGNORECASE,
)


def validate_workflow_text(text: str, source: str = "workflow") -> list[str]:
    lines = text.splitlines()
    try:
        jobs_index = next(i for i, line in enumerate(lines) if line.strip() == "jobs:")
    except StopIteration:
        return [f"{source}: missing top-level jobs section"]

    jobs: list[tuple[str, list[str]]] = []
    current_name: str | None = None
    current_lines: list[str] = []
    for line in lines[jobs_index + 1 :]:
        if line and not line[0].isspace():
            break
        match = JOB_START.match(line)
        if match:
            if current_name is not None:
                jobs.append((current_name, current_lines))
            current_name, current_lines = match.group(1), []
        elif current_name is not None:
            current_lines.append(line)
    if current_name is not None:
        jobs.append((current_name, current_lines))

    if not jobs:
        return [f"{source}: jobs section contains no jobs"]

    errors: list[str] = []
    for name, body in jobs:
        main_ref_guard = any(MAIN_REF_GUARD.match(line) for line in body)
        if not main_ref_guard:
            errors.append(
                f"{source}: job '{name}' must be restricted to refs/heads/main"
            )
        runner_declarations = [
            (index, match.group(1).strip())
            for index, line in enumerate(body, start=1)
            if (match := RUNS_ON.match(line))
        ]
        reusable = any(REUSABLE_WORKFLOW.match(line) for line in body)
        if reusable:
            errors.append(f"{source}: job '{name}' calls a reusable workflow")
        if len(runner_declarations) != 1:
            errors.append(
                f"{source}: job '{name}' must declare exactly one explicit runs-on value"
            )
            continue
        _, runner_value = runner_declarations[0]
        if runner_value != EXPECTED_RUNNER:
            errors.append(
                f"{source}: job '{name}' has unapproved runs-on value {runner_value!r}; "
                f"expected {EXPECTED_RUNNER!r}"
            )
    return errors


def check_repository(workflows_dir: Path) -> list[str]:
    files = sorted((*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")))
    if not files:
        return [f"{workflows_dir}: no workflow files found"]
    errors: list[str] = []
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{path}: cannot read workflow: {exc}")
            continue
        errors.extend(validate_workflow_text(content, str(path)))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".github" / "workflows",
    )
    args = parser.parse_args()
    errors = check_repository(args.workflows_dir)
    if errors:
        print("Workflow runner policy FAILED:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Workflow runner policy passed for {args.workflows_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
