# Scarb.TO — current verified state

**Audit time:** 31 October 2026, approximately 20:46 UTC. This is a point-in-time checkpoint, not a live monitor. Refresh GitHub, Actions, published data and domain status before acting.

## Live product and latest refresh

- Repository: [justinpfisher/ScarbTO](https://github.com/justinpfisher/ScarbTO), public, `main`. The verified 31 October refresh left `main` at data publication commit `9d0e828a66fee0de947565e5fea4bf4877bf20ea`, after [PR #24](https://github.com/justinpfisher/ScarbTO/pull/24) merged at `52dfaa464f4e8fd69b3425148112a95788b25a3c`. Recheck before using either SHA as current.
- [Publisher run 41240217550](https://github.com/justinpfisher/ScarbTO/actions/runs/41240217550) succeeded: Python/JavaScript source and UI tests (including 13 rendered desktop/mobile browser cases), official City feed validation, snapshot verification, Pages deployment, and independent production-HTTP smoke verification. The importer validated 125,007 source rows, geocoded all 125,007, retained 19,097 Scarborough inspection rows, 3,324 establishments, zero unassigned neighbourhoods and 115 retained activity entries (not 115 newly observed events). The deployment reported 2026-10-31 20:44:45 UTC publication.
- The 31 October post-deploy GET check confirmed [https://scarb.to/](https://scarb.to/), the new area UI modules, the six City ward and 30 source-qualified neighbourhood GeoJSON assets and the populated DineSafe snapshot; the smoke-check log explicitly reports **LIVE VERIFIED**. Publication at 20:44:45 UTC is **not** proof of a City-side source update. The City catalogue source refresh timestamp remains separate in the published snapshot and may omit a timezone.
- [PR #24](https://github.com/justinpfisher/ScarbTO/pull/24) implemented the approved optional neighbourhood and municipal ward explorer (off by default, mutually exclusive boundaries, persisted single-area filtering for DineSafe, visible clear chip, keyboard area selector, desktop panel and mobile bottom sheet). The exact PR head `23ebb0a990bb369916155b3de3aa76c54310e814` passed [CI 41239863295](https://github.com/justinpfisher/ScarbTO/actions/runs/41239863295); an independent Codex re-review on that head completed with no findings after two functional fixes. The live data release has official 6-ward and selected 30-neighbourhood files.
- The live site `https://scarb.to/` was HTTP-verified after this release, not merely inferred from CI. The source-linked monthly history remains file-based. Physical-device usability remains unverified; rendered desktop/mobile browser tests passed.

## Integrated feeds and research boundaries

- DineSafe is the production data feed. PR #20 normalized missing address placeholders, labels inspection-detail text correctly, separates source freshness from collection/publication times, and adds monthly observed-change history. The area explorer filters the **existing** establishments without changing the six-ward geographic inclusion. The optional 30-area overlay follows the pinned TPS/City majority-area crosswalk and must not be mistaken for complete administrative containment; an adjacent thirty-first DineSafe-assigned neighbourhood polygon is a different inclusion decision.
- The selected-police-calls interface is grouped and on demand for Toronto Divisions 41–43. It is not individual calls, confirmed crimes, or a neighbourhood incident map. Do not display stale source counts as current.
- Beach information is a dated historical sample preview, not present swimming advice. Toronto results currently have a seasonal limitation; an old sample cannot be presented as today's safety status. [PR #4](https://github.com/justinpfisher/ScarbTO/pull/4) remains an open draft for a synthetic status adapter and is not a live status feed.
- Permit/development code is research-only. The cleared-record traversal downloaded 106,000 of 446,979 rows from generation `2026-10-28T11:19:44.437505`; the final 6,000 downloaded rows lack post-batch generation verification, so the traversal is not certified complete. OAR spatial acquisition returned zero rows because the source request received a tunnel-level HTTP 403. Public permit export remains disabled. Do not infer construction completion from permit/application status or publish unqualified locations.
- Historical police neighbourhood export also remains disabled; aggregate projection and source-contract safeguards do not by themselves qualify a public feed. The area panel explicitly does **not** prorate quarterly neighbourhood counts into wards or display invented ward crime totals. PR #23 is a separate draft protecting the exact CSI registry-contract bytes on Windows checkouts; do not disturb it.

## Runner policy — unresolved

- Main `.github/workflows/refresh-and-publish.yml` still runs both test and publish jobs on `ubuntu-latest`. The test job also runs PR validation; the publish job is restricted to main/non-PR events and carries write permissions. The 31 October verified live release used hosted Ubuntu. The new post-deploy public HTTP smoke check is part of this existing essential publication path; it is not a GMKtec runner migration.
- **November Actions usage guard:** The owner's 1,000-minute stop threshold applies only to Actions minutes that consume the account's included or billed allowance. GitHub documents standard hosted runners in public repositories, Pages, and self-hosted runners as free; this public repository's standard hosted Ubuntu jobs and Pages deployment therefore must not be counted from raw job durations as allowance usage. Repository-level run metadata does not establish account-wide allowance consumption. No account-wide usage total or automated cap enforcement is verified here. Before enabling any job that may consume included compute, require an authorized account-level billing reading and stop at the 1,000 qualifying-minute threshold for November.
- [PR #1](https://github.com/justinpfisher/ScarbTO/pull/1) is open and draft at head `ab0a189f0c2d5327d519d0d56cd5289c02f6bad3`, based on old main commit `d61c7babc241aec890a88112678828c26a040a5e`; GitHub currently reports it unmergeable. Its proposed runner labels and its own last state report must not be treated as proof of an installed or authorized runner.
- The connected GitHub fetch tool rejected the repository runner-inventory endpoint as unsupported. Current registration, exact labels, repository scope, service/reboot behavior and offline queue behavior therefore have not been verified by this audit. No runner, credentials, VM, workflow, or security settings were changed.
- Do not migrate the workflow or merge PR #1 until the ScarbTO runner is directly verified on GMKtec and the workflow is reconciled with current main. Do not run untrusted PR code on a persistent self-hosted runner. Preserve the existing refresh and deployment path until a tested migration/rollback plan exists. The current hosted test job also conflicts with the GMKtec-first repository policy and needs an explicitly approved, narrowly documented exception or a verified safe replacement before routine PR validation is changed.

## Next steps

1. Verify ScarbTO runner registration and actual labels, repository-only scope, service start/recovery and reboot persistence through the established authorized GMKtec path. Then rebase/reconcile PR #1 with current main and test queue/no-fallback behavior without executing untrusted code on the persistent runner. Do not guess missing runner state from the unsupported API response.
2. Keep the DineSafe production refresh operating safely while resolving the runner transition. Do not remove the currently working workflow before a verified replacement is ready.
3. Complete independently source-qualified provincial/federal electoral-district intersections and term/vacancy checks for the area panel, retaining the existing official address-lookup links until geographic assignments can be verified. No resident address collection.
4. Finish full permit/development source-generation, record-identity and spatial qualification before considering public output. The existing resumable collector and quarantine tests (including PR #22) are foundational, not a qualified complete feed.
5. Keep historical police neighbourhood export disabled until the already-approved full-quarter five-category crosswalk, grouped-query validation, privacy controls and public projection are qualified together. Keep selected-call counts fail-closed on staleness. Never invent or apportion ward crime figures.
6. Do not turn the beach historical preview into current health advice; qualify any operational advisory reuse separately.

## Operational links

- [Open pull requests](https://github.com/justinpfisher/ScarbTO/pulls)
- [Actions and refresh history](https://github.com/justinpfisher/ScarbTO/actions)
- [Published source snapshot](https://scarb.to/data/snapshot.json)
- [Toronto DineSafe source](https://open.toronto.ca/dataset/dinesafe/)
- [Toronto Open Government Licence](https://open.toronto.ca/open-data-licence/)

Do not record unverified work as tested, merged, deployed or live.
