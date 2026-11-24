# OpenClaw autonomous-continuation pilot — Scarb.TO

**State:** fixture prepared on pilot-only branch. The OpenClaw Gateway, worker dispatch, reboot recovery, and 48-hour run have **not** been installed or verified by this GitHub change.

This is synthetic source-free work, not a change to the Scarb.TO application. Do **not** merge into main. Root AGENTS.md and ARCHITECTURE.md still govern the real project. Dot remains its sole release coordinator. OpenClaw may coordinate only this fixture until the pilot passes and ownership is explicitly transferred.

## Operator sequence

1. Read OPERATING_CONTRACT.md and WORK_QUEUE.json. Check actual GMKtec and existing worker state before installing anything.
2. Install OpenClaw from the official Windows Hub stable release if absent (native Gateway when supported, otherwise app-owned WSL); do not modify the existing GitHub runner VM or Node 22 Scarb.TO toolchain. Connect an existing eligible ChatGPT/Codex login; no additional paid services.
3. Keep the Gateway local/private. No Telegram, public channels, new skills, external model API purchases, or credentials in this branch. Run the OpenClaw security audit and record the result privately.
4. Clone just this branch to an isolated local directory. Confirm branch and clean Git status. Execute the baseline from this folder: `python -m unittest discover -s tests -v`. **Baseline tests deliberately fail**.
5. Use OpenClaw to dispatch at least three of P1–P4 to independent Codex workers concurrently, with distinct worktrees and no overlapping file ownership. Verify native worker receipts, test outputs and commits.
6. Immediately on worker completion, reconcile the result and launch the next ready item. P5 must wait until P1–P4 pass. P6 must remain a hypothetical owner-only decision.
7. Record native session IDs, UTC actual timestamps, task claims, commit hashes, test results, latency, recoveries, and proof that no human re-prompt occurred. Keep raw logs local and separate from Git.
8. Test a controlled Gateway-only stop/restart and recovery without interrupting other GMKtec services.
9. Test a newly committed approved pilot instruction arriving via GitHub without a direct OpenClaw prompt. Do not mark handoff tested until this is observed.
10. Observe for 48 hours. Genuine idle with no ready tasks is allowed; idle with eligible work and free capacity is an error to investigate.

## Verification

Full suite: `cd pilot/openclaw && python -m unittest discover -s tests -v`. Twelve cases, intentionally failing at baseline. A reference implementation was tested separately with all twelve passing; that reference is not included.

Pass requires native evidence of >=3 overlapping workers, event-driven follow-up, recovered P4 regression, P5 dependency gating, zero unauthorized actions, successful Gateway restart reconciliation, the GitHub handoff, and traceable accurate reporting. An untested gate is **NOT VERIFIED**, not a pass. The test must not deploy, publish, fetch live source data or run production CI.

If a mandatory login or authorization cannot be performed unattended, report exactly that owner step while completing independent setup. Rollback: stop only the pilot Gateway/agents and remove the isolated checkout; all real project coordinators remain unchanged.
