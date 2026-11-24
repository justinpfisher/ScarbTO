# Pilot operating contract

## Intended division of responsibility

Dot: original project decisions, real release coordination and reporting.

GitHub: source of approved outcomes and evidence. This pilot branch is an isolated experiment, **not** an approved production change.

OpenClaw: sole coordinator for the synthetic pilot fixture; never a competing Scarb.TO release coordinator.

Codex: individual isolated workers working on the files named in WORK_QUEUE.json.

## Rules

- The user authorized this source-free, reversible evaluation, not a production migration. No new charges, outreach, protected-source processing, unapproved credentials, production deployments, or modifications to other agents.
- Always read the actual task state and existing workers before launch. A worker claim requires matching native session/turn ID, timestamps, Git commit, scoped test output and complete diff.
- P1–P4 are independent; allocate separate worktrees and allow >=3 overlapping lightweight sessions if host capacity permits. Only one heavy GMKtec build/test operation at a time.
- P5 becomes ready only after P1–P4 pass and are integrated. P6 is a simulation of an owner-reserved decision: explain the request, do not execute it.
- On completion or failure, immediately decide and start the next authorized action; a scheduled watchdog is only a recovery mechanism. If scheduling is the *only* continuation mechanism, record this as a limitation.
- Reconcile uncertain or interrupted dispatches before retry. No idempotency guessing; never bypass product or security denials.
- Record statuses ready/running/done/waiting_dependency/awaiting_owner/failed/not_verified and exact receipts. An agent's prose is not evidence. Do not record credentials or sensitive paths in public GitHub.
- Test a Gateway-only restart, never a reboot of the existing GMKtec runners. Log all recovery observations.
- If a required step needs a login or owner authority, stop only that step and continue independent work. Keep actual incident/error and report the exact owner action.
- The acceptance report must include UTC timeline, overlapping worker intervals, worker and test receipts, commits, idle gaps with eligible capacity, GitHub handoff observation, decision boundary, provider usage/cost and a pass/fail/untested verdict per criterion.

## Fail-safe

Any false claim of execution, conflicting release change, unauthorized spending, duplicate consequential dispatch, or disregard of owner review is a failed pilot. Do not make or merge a pull request to main. Preserve existing Dot and production automations.
