# Scarb.TO — current verified state

**Repository audit:** 28 October 2026, after PR #18 merged. This is a point-in-time checkpoint, **not** a live monitor. Refresh repository, Actions, dataset and domain facts before acting.

## Implemented and merged

- Public GitHub repository: [justinpfisher/ScarbTO](https://github.com/justinpfisher/ScarbTO), branch `main`. Functional-code checkpoint `6a06927c91572d07cda6b9f6c2803f911fc5ca91` merged [PR #18](https://github.com/justinpfisher/ScarbTO/pull/18). Repository documentation was subsequently merged in [PR #19](https://github.com/justinpfisher/ScarbTO/pull/19) (`0aefa15c50d43ff3ecf4d3b9a36ca74379849395`).
- DineSafe importer consumes official City of Toronto CKAN data, validates Scarborough geographic assignments, writes a current JSON snapshot and downloadable CSV, and records observed changes between validated snapshots. The existing GitHub Pages workflow has had successful test/publish and scheduled-refresh runs.
- On the last inspected published snapshot (`docs/data/snapshot.json`, published **28 October 2026, 03:22:54 UTC**): **123,869** official source rows, **3,297** Scarborough establishments, zero unassigned neighbourhoods, and **21** observed change events. These figures are historical audit observations; use the live snapshot for current counts.
- Map/list UI, neighbourhood filtering, recent-versus-all DineSafe views, source links, responsive boundary display and accessible list fallback have been implemented. Rendered desktop/mobile browser checks have passed in recorded GitHub Actions runs.
- The selected Toronto Police calls UI is integrated, but requests only division-level grouped counts for Divisions 41–43 on demand. It is **not** a map of individual calls or neighbourhood incidents; live availability was not independently verified in this audit.
- Beach information is a **dated historical sample preview**, not current swimming advice. Permit/development adapters are merged as research-only modules, including [PR #18](https://github.com/justinpfisher/ScarbTO/pull/18); full real-source qualification and public export remain outstanding.
- GitHub Pages preview: https://justinpfisher.github.io/ScarbTO/ . `scarb.to` is the intended public domain, and project history reports a cutover; this audit **could not independently retrieve the live domain or verify HTTPS and current client rendering**. Verify before claiming production is live.

## Confirmed gaps and release safeguards

1. **Runner policy not yet implemented:** `.github/workflows/refresh-and-publish.yml` on main still has both jobs on `ubuntu-latest`. [PR #1](https://github.com/justinpfisher/ScarbTO/pull/1) proposes GMKtec execution but remains open; its last documented registration check found no Scarb.TO runner. Verify registration/labels/permissions/startup on the actual GMKtec before any migration. Avoid breaking the existing public refresh; a hosted essential-feed exception requires explicit, documented justification.
2. **DineSafe public data presentation:** audit found **2,036** addresses including literal `None` and **2,092** records with `type` equal to `None`. Current `typeDesc` maps to inspection findings, not establishment type. Fix ingestion and UI with representative official-record comparisons and regression tests; do not fabricate addresses/categories.
3. **Freshness semantics:** the visible 48-hour staleness warning currently measures `published_at` (Scarb.TO publication), not verified upstream freshness. Distinguish source refresh, collection, change detection and inspection dates without misleading users.
4. **Usability:** actual physical-device and small-resident-sample validation remain to be independently documented. Synthetic browser checks do not prove user comprehension or live basemap reachability.
5. **Research readiness:** permit semantic identities, full pagination/generation completeness, spatial joins and licensing need real-source qualification before public display. Police neighbourhood-level usefulness and beach seasonal feed readiness remain open.
6. **Backlog hygiene:** superseded draft PRs #6, #7, #8 and #11 were checked and closed on 28 October 2026; desktop-clipping issue #14 was closed as resolved by PR #16. PR #1 remains open until actual runner verification. The distinct synthetic beach-status PR #4 remains open pending a justified seasonal integration.

## Next delivery order

1. **Completed:** repository policy/current-state documentation merged via PR #19; superseded PRs #6, #7, #8, #11 and resolved issue #14 closed.
2. **Blocked on verified runner:** provision, register and isolate the repository-specific GMKtec runner; finish PR #1 or a safer refreshed variant with no hosted fallback. Preserve essential public feed refresh through an explicitly documented narrow reliability exception where needed.
3. **Prepared on branch, not merged:** [DineSafe quality and freshness correction](https://github.com/justinpfisher/ScarbTO/tree/chat/dinesafe-quality-freshness-20261028) normalises literal address placeholders, distinguishes inspection details from establishment category, clarifies source timestamps and adds monthly observed-change archives with tests. Seven read-only pure-JavaScript assertions passed in an isolated code sandbox, but the actual Python, full browser and GMKtec suites have **not** run. Keep this branch unmerged until approved execution and release verification are possible; do not trigger current hosted PR tests by opening a PR first.
4. Qualify one useful building/development source with real source evidence before public integration.
5. Validate resident usability and, after enough sourced changes accumulate, consider static neighbourhood update pages.

## Operational links

- [Open PRs](https://github.com/justinpfisher/ScarbTO/pulls)
- [Actions and refresh history](https://github.com/justinpfisher/ScarbTO/actions)
- [Published source snapshot](docs/data/snapshot.json)
- [Source dataset](https://open.toronto.ca/dataset/dinesafe/)
- [Toronto Open Government Licence](https://open.toronto.ca/open-data-licence/)

Do not record unverified work as tested, merged, deployed or live.

