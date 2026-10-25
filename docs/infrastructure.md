# GitHub Actions and GMKtec runner

## Intended execution policy

Trusted Scarb.TO jobs select the repository-authorised runner using the exact
labels below. There is no hosted-runner fallback: if the runner is offline,
jobs remain queued until it returns or are cancelled. Do not change a job to a
hosted label to clear a queue. A hosted-compute exception needs explicit user
approval and a narrowly scoped workflow change.

```yaml
runs-on: [self-hosted, linux, x64, scarbto-gmktec]
```

`python scripts/check_workflow_policy.py` checks every workflow job, rejects
missing or different runner declarations, matrix-selected runners, and
reusable-workflow calls. Its unit tests include hosted, matrix, reusable, and
missing-runner cases. This repository policy is a guardrail, not a GitHub
platform prohibition: repository administrators can change workflow files,
and this personal repository currently has no branch protection. GitHub's
repository Actions permissions endpoint exposes allowed actions and default
`GITHUB_TOKEN` permissions, but no setting to prohibit hosted runners for an
individual personal repository. Do not claim that the policy script is
equivalent to a platform-level compute restriction.

GitHub repository settings now allow only GitHub-owned Actions; third-party
and unverified-publisher Actions are blocked. The current workflows use only
`actions/*`. Actions remain enabled, SHA pinning is not required, and the
default workflow token permission is read-only. These restrictions do not
prevent an administrator from writing a workflow that selects hosted compute.

## Verified provider state (2026-10-25)

The GitHub Actions runner API reported:

| Repository | Runner | Status | Labels |
| --- | --- | --- | --- |
| `justinpfisher/ScarbTO` | none | no runner registered | — |
| `justinpfisher/thefish` | `thefish-gmktec` | online | `self-hosted`, `Linux`, `X64`, `thefish-gmktec` |
| `justinpfisher/Stammtisch` | none | no runner registered | — |
| `Curriculum-Mapping-Initiative/lcrs-poc` | `lcrs-gmktec-01` | online | `self-hosted`, `Linux`, `X64`, `lcrs-gmktec` |

The Scarb.TO registration, actual host environment, service startup, recovery,
permissions, and resource headroom have **not** been verified. The expected
custom label is `scarbto-gmktec`; confirm it in GitHub's runner API after
registration before merging workflows that target it. The project runner must
be registered only to `justinpfisher/ScarbTO`, use its own Linux identity and
work directory, and never reuse or alter the TheFish or LCRS registrations.

The Windows machine running this Codex task could not reach either recorded
GMKtec IP over SSH. Its only listed WSL distribution was a stopped Podman
machine. Thus no claim is made here about the mini PC's current Linux
environments, runner services, or Windows/WSL startup persistence.

## Workflows and trust boundary

- `refresh-and-publish.yml` runs the existing tests and validated DineSafe
  refresh/publish on the GMKtec labels. It has no `pull_request` trigger, so
  code from fork pull requests is not checked out or executed on the persistent
  runner. Pushes to `main`, the existing daily schedule, and manual runs are
  trusted events.
- `workflow-policy.yml` checks workflow declarations on `main` and on manual
  dispatch, using the same runner.
- `runner-diagnostic.yml` is manually dispatched and reports the runner name,
  OS, and architecture without checking out repository code.
- `.github/CODEOWNERS` assigns workflow and policy files to the repository
  owner. CODEOWNERS review is enforced only if GitHub branch/ruleset protection
  requires code-owner review; `main` currently has no branch protection.

All jobs use read-only token permissions except the existing publisher, which
needs `contents: write`, Pages write, and identity-token write to publish. Do
not grant those permissions to tests or diagnostics. Do not add PR triggers to
the persistent-runner workflows. If PR validation is needed later, design a
separate approach that never executes untrusted code on GMKtec.

## Setup and maintenance

Provision only from the GMKtec Linux environment after inspecting the existing
VMs/containers, runner services, and startup chain. Use a dedicated `scarbto`
Linux account, a separate runner directory, and a repository-scoped
registration token obtained just in time. Never commit or log the token. Use
the currently supported GitHub Actions runner release and its service
installer for automatic startup/recovery. If Linux runs under WSL, verify the
Windows startup mechanism starts the exact distro and runner after a host
reboot; `systemctl` enablement alone does not start a stopped WSL distro.

Before enabling this configuration, verify in GitHub that the ScarbTO runner
is online with `self-hosted`, `Linux`, `X64`, and `scarbto-gmktec` labels, and
that its repository scope is only ScarbTO. Then run the manual diagnostic and
observe a real workflow job's runner name/labels in the Actions run. Temporarily
disable only the ScarbTO runner and dispatch the diagnostic: it must stay
queued. Restore it and confirm a subsequent run succeeds. Test service restart
and host-reboot startup separately; distinguish observed tests from service
configuration inspection.

The current repository is public and its Pages staging site is public. No
visibility change is included because that could affect the existing Pages
publication. GitHub Free personal accounts can publish Pages only from public
repositories; private-repository Pages require GitHub Pro or higher. The
account tier was not available from the GitHub API in this session, so verify
the plan or choose another hosting path before converting this repo to private.
No paid plan was enabled. Review a safe migration path before changing
repository visibility.
Until a public-contribution security design exists, keep fork pull-request
workflows off the persistent runner. GitHub currently reports Actions enabled,
allowed actions set to `all`, default workflow token permissions `read`, and
no `main` branch protection. Revisit these platform controls with the owner;
the repository YAML checker cannot stop a repository administrator from
rewriting a workflow.

## Troubleshooting

- A job waiting for a runner means the ScarbTO runner is offline, unregistered,
  or missing one of the four exact labels. Inspect its repository-scoped runner
  record and service logs; do not add hosted labels.
- A policy failure means a job is missing the canonical inline `runs-on` list,
  or uses runner indirection. Run the checker locally and fix the workflow.
- A runner that returns only after manually opening WSL is not persistent.
  Repair and reboot-test the Windows-to-Linux startup chain before relying on
  scheduled refreshes.
- Confirm TheFish and LCRS registrations independently after runner changes;
  ScarbTO must have its own repository registration, identity, and directory.
