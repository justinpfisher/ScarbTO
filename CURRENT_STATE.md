# Scarb.TO — current verified state

**Audit time:** 28 October 2026, 13:48 UTC. This is a point-in-time checkpoint, not a live monitor. Refresh GitHub, Actions, published data and domain status before acting.

## Live product and latest refresh

- Repository: [justinpfisher/ScarbTO](https://github.com/justinpfisher/ScarbTO), public, `main`. Latest main commit is data refresh `63caaa8e5a709b88203c58ff14ce1457a16d46f6`, following the DineSafe quality/freshness implementation merged in [PR #20](https://github.com/justinpfisher/ScarbTO/pull/20) at `ce0561e9f0282ee6d74ca0693a94f72ed08f5db4`).
- Latest observed publisher run [40698504507](https://github.com/justinpfisher/ScarbTO/actions/runs/40698504507) succeeded: tests, validated DineSafe refresh, snapshot verification, and Pages deployment. At that run the importer validated 124,150 source rows, geocoded 124,150, retained 18,959 Scarborough rows, and reported 3,301 establishments, zero unassigned neighbourhoods, and 44 observed change events.
- The published snapshot records Scarb.TO publication at **2026-10-28 13:41:14 UTC** and City source refresh at **2026-10-28 08:18:45.891883** (the source timestamp has no timezone in its value). These are different events; a successful check is not itself a new City inspection.
- This current-state correction is tracked in [PR #21](https://github.com/justinpfisher/ScarbTO/pull/21); it removes the already-fixed DineSafe defects from the status list and records the latest permit-source qualification evidence below.
- The live site `https://scarb.to/` and normal HTTPS were verified after the reviewed DineSafe UI work. The live October history archive contains the validated observed changes. Physical-device usability remains unverified.

## Integrated feeds and research boundaries

- DineSafe is the production data feed. PR #20 normalized missing address placeholders, labels inspection-detail text correctly, separates source freshness from collection/publication times, and adds monthly observed-change history.
- The selected-police-calls interface is grouped and on demand for Toronto Divisions 41–43. It is not individual calls, confirmed crimes, or a neighbourhood incident map. Do not display stale source counts as current.
- Beach information is a dated historical sample preview, not present swimming advice. Toronto results currently have a seasonal limitation; an old sample cannot be presented as today's safety status. [PR #4](https://github.com/justinpfisher/ScarbTO/pull/4) remains an open draft for a synthetic status adapter and is not a live status feed.
- Permit/development code is research-only. The cleared-record traversal downloaded 106,000 of 446,979 rows from generation `2026-10-28T11:19:44.437505`; the final 6,000 downloaded rows lack post-batch generation verification, so the traversal is not certified complete. OAR spatial acquisition returned zero rows because the source request received a tunnel-level HTTP 403. Public permit export remains disabled. Do not infer construction completion from permit/application status or publish unqualified locations.
- Historical police neighbourhood export also remains disabled; aggregate projection and source-contract safeguards do not by themselves qualify a public feed.

## Runner policy — unresolved

- Main `.github/workflows/refresh-and-publish.yml` still runs both test and publish jobs on `ubuntu-latest`. The test job also runs PR validation; the publish job is restricted to main/non-PR events and carries write permissions. The latest successful run used hosted Ubuntu.
- **November Actions usage guard:** The owner's 1,000-minute stop threshold applies only to Actions minutes that consume the account's included or billed allowance. GitHub documents standard hosted runners in public repositories, Pages, and self-hosted runners as free; this public repository's standard hosted Ubuntu jobs and Pages deployment therefore must not be counted from raw job durations as allowance usage. Repository-level run metadata does not establish account-wide allowance consumption. No account-wide usage total or automated cap enforcement is verified here. Before enabling any job that may consume included compute, require an authorized account-level billing reading and stop at the 1,000 qualifying-minute threshold for November.
- [PR #1](https://github.com/justinpfisher/ScarbTO/pull/1) is open and draft at head `ab0a189f0c2d5327d519d0d56cd5289c02f6bad3`, based on old main commit `d61c7babc241aec890a88112678828c26a040a5e`; GitHub currently reports it unmergeable. Its proposed runner labels and its own last state report must not be treated as proof of an installed or authorized runner.
- The connected GitHub fetch tool rejected the repository runner-inventory endpoint as unsupported. Current registration, exact labels, repository scope, service/reboot behavior and offline queue behavior therefore have not been verified by this audit. No runner, credentials, VM, workflow, or security settings were changed.
- Do not migrate the workflow or merge PR #1 until the ScarbTO runner is directly verified on GMKtec and the workflow is reconciled with current main. Do not run untrusted PR code on a persistent self-hosted runner. Preserve the existing refresh and deployment path until a tested migration/rollback plan exists. The current hosted test job also conflicts with the GMKtec-first repository policy and needs an explicitly approved, narrowly documented exception or a verified safe replacement before routine PR validation is changed.

## Next steps

1. Verify ScarbTO runner registration and actual labels, repository-only scope, service start/recovery and reboot persistence through the established authorized GMKtec path. Then rebase/reconcile PR #1 with current main and test queue/no-fallback behavior without executing untrusted code on the persistent runner. Do not guess missing runner state from the unsupported API response.
2. Keep the DineSafe production refresh operating safely while resolving the runner transition. Do not remove the currently working workflow before a verified replacement is ready.
3. Finish full permit source-generation and spatial qualification before considering public permit output. The current adapter/collector tests are foundation evidence, not full-feed qualification.
4. Keep historical police output disabled until the source crosswalk, grouped-query validation and public projection are qualified together. Keep current selected-call counts fail-closed on source staleness.
5. Do not turn the beach historical preview into current health advice; qualify any operational advisory reuse separately.

## Operational links

- [Open pull requests](https://github.com/justinpfisher/ScarbTO/pulls)
- [Actions and refresh history](https://github.com/justinpfisher/ScarbTO/actions)
- [Published source snapshot](https://scarb.to/data/snapshot.json)
- [Toronto DineSafe source](https://open.toronto.ca/dataset/dinesafe/)
- [Toronto Open Government Licence](https://open.toronto.ca/open-data-licence/)

Do not record unverified work as tested, merged, deployed or live.
