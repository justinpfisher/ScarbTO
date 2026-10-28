# Scarb.TO — repository execution instructions

These rules apply to automated agents, contributors and development workflows. Read [CURRENT_STATE.md](CURRENT_STATE.md), this file, [ARCHITECTURE.md](ARCHITECTURE.md) and the actual current repository/Actions state before changing production. A plan, old handoff, or successful test is not evidence of a live release.

## Product and scope

- Build the Scarborough-first, source-linked, map-first neighbourhood change service. The opening view emphasises useful recent changes, with an accessible matching list, compact filters, mobile usability and official source links.
- Prioritise public usefulness and verified freshness over expanding research prototypes. First maintain a correct DineSafe feed; advance one source-qualified additional feed at a time. Historical beach samples are not current swimming advice; police division counts are not neighbourhood incidents.
- No invented records, locations, status interpretations or update times. Preserve official identifiers, source terms, source URLs, original event/inspection dates, upstream publication dates, collection/detection times, and explicit source limitations.
- `typeDesc` in the current DineSafe resource is inspection-detail text, not an establishment category; do not present it as a category. Normalise missing-value placeholders without inventing addresses.
- Keep validated changes reusable across lists, maps and future neighbourhood briefs. Prefer small file-based history archives over a database while that remains adequate.
- Keep incremental infrastructure at or below C$25/month (target C$0) and routine maintenance at 2–4 hours/week. Avoid unnecessary servers, credentials, accounts, paid APIs or approval ceremonies.

## Mandatory GMKtec-first execution policy

- GMKtec is the default authorised computer for development automation, ingestion, builds, testing, scheduled processing and trusted GitHub Actions.
- Every applicable trusted Actions job must explicitly select a *verified*, project-authorised GMKtec runner using its actual labels. Do not assume a runner has been provisioned from a proposed label in a PR.
- Do not use `ubuntu-latest`, other GitHub-hosted runners, dynamic hosted-runner matrices or silent hosted fallback for routine jobs. An unavailable GMKtec runner means queue or hold, **not** automatic reassignment.
- Never run untrusted public pull-request code on a persistent GMKtec runner. Use restricted repository-scoped runner identity, isolated work directory, minimal token permissions and secret separation.
- Essential public data refresh or static hosting can receive a narrow, documented hosted exception only when reliability or public availability justifies it. Document cost, permission scope, and why GMKtec-only processing is insufficient. This does not authorise hosted development or test jobs.
- **Transition warning:** As of the 28 October 2026 audit, the existing refresh/publish workflow still uses `ubuntu-latest`. PR #1 is **not merged** and the project runner has not been newly verified. Do not present the policy as implemented or merge a runner-only workflow that would strand the production refresh without a verified replacement. Complete the authorised migration safely.

## Delivery and data integrity

- Verify current source schema, licensing, geographic boundaries, duplicates, meaningful count changes and safe publication. Fail closed and retain the last good public release on anomalies. Surface staleness and support rollback.
- Keep upstream source freshness distinct from Scarb.TO's successful check/publication time. A successful unchanged re-download is not new City information.
- For ordinary authorised work follow **implement → relevant tests → merge → deploy → verify live**. A green CI run is not proof of live operation; report distinctions accurately.
- Use focused tests for isolated edits and full rendered-browser/integration checks for relevant UI changes. Do not repeatedly run every research prototype for unrelated documentation changes.
- Do not modify domain DNS, unrelated mail records, repository visibility or private credentials merely to advance an ordinary feature.
- Work independently through manageable blockers. If physical GMKtec/provider access is unavailable, complete safe independent changes and record the precise outstanding owner action in CURRENT_STATE.md. Do not repeatedly ask for an approval already granted.
- Retire superseded branches/PRs after confirming that newer merged work covers them. Keep one primary integration queue; the GitHub repository is the source of truth.

