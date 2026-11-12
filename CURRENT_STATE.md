# Scarb.TO — current verified state

**Current checkpoint:** 12 November 2026. This is a point-in-time record, not a live monitor.

## Current release status - 12 November 2026

The integrated resident release remains in progress across the approved packages P0-P8. Do not confuse the released increments below with completion of site-wide voice, source qualification or stabilization.

- **Latest verified production:** main `38709dd5d59c5eca4c3aeb9bb75d2b89a63e815c`, following PR #46 merge `a62efe549e13e3ad171b171102e9b930cfeae96c`. Existing code-only run [43240197245](https://github.com/justinpfisher/ScarbTO/actions/runs/43240197245) passed trusted-main tests, unchanged-data provenance, publication and live HTTP verification. The weekly index, November 2-8 edition and registry were separately verified live: 115 recorded changes, revision 1. Original edition generation time is `2026-11-12T14:45:26.036328+00:00`; it is not the source date or deployment time.
- **PR #49 branding/partial voice:** merged as `2d13af48931e68cd39564b5631cdca71e4ddbc8a`; connected desktop lockup and standalone mobile mark passed isolated rendered tests and live asset hash checks. Code-only run [43238577797](https://github.com/justinpfisher/ScarbTO/actions/runs/43238577797) succeeded. This was a partial voice increment, not site-wide conversion.
- **PR #42 RSS and PR #47 sharing/print:** merged. RSS was separately verified live with 50 source-linked items. Neighbourhood routes include the canonical `/west-rouge/` and `/westrouge/` forwarding alias.
- **Unchanged last-good data:** 3,345 establishments; stored `published_at=2026-11-10T17:56:54+00:00`, upstream `last_refreshed=2026-11-10 08:17:15.620381`. These editorial releases did not refresh City data or invent newer source timestamps. Snapshot SHA-256: `c21ca4c05c3f45821ce471475ed05646ce48b5e9f1f741fce1bade73270874d4`.
- **Upstream refresh:** normal run 43238018054 passed tests, then failed closed on City ward-geography HTTP 503. The code-only route preserves the last-good data rather than repeatedly calling the failed upstream service to publish copy.
- **Site-wide editorial assignment:** the owner explicitly assigned Dot implementation, qualification, independent review, release and full live verification on 12 November. Scope includes every authored sentence and the weekly-brief copy-only revision/hash defect identified in PR #49's latest comments. One coordinated writer owns shared files. This working branch is not yet a verified release.
- **Planning and permits remain unqualified and unpublished.** Public permit export stays disabled. The earlier OAR tunnel-layer HTTP 403 remains a separate access boundary; do not retry or route around it. No editorial change qualifies a new source.
- **Stabilization remains outstanding:** assess consecutive scheduled validated refreshes, a real weekly publication cycle, full deployed resident journeys, recovery and operating time against the original acceptance criteria. Successful code-only runs do not establish source-refresh continuity.

## Approved integrated release — execution started

The owner approved the integrated resident-release plan and instructed **"Okay. Lock this in. And get started."** The enduring decisions, required packages P0–P8, acceptance criteria and retained brand-adoption boundary are recorded in [ARCHITECTURE.md](ARCHITECTURE.md). They include the complete resident experience, independently qualified planning applications and the permit companion, permanent neighbourhood pages, website briefs and RSS; email is later. Publish useful working stages while the integrated release remains open.

The owner specifically raised a permanent address such as `scarb.to/westrouge`. West Rouge is City neighbourhood 143 and exists in the qualified overlay. P3 now publishes all 30 qualified neighbourhood pages from one reusable template, with canonical routes and the `/westrouge/` forwarding alias. Both `/west-rouge/` and `/westrouge/` returned HTTP 200 in the bounded production route check recorded above.

## Historical public release and source refresh - 1 November snapshot

- Product code revision: `39ccb989a657ebd00f3dbf3ff69882645b4a53e7`. The code-only [run 41363084003](https://github.com/justinpfisher/ScarbTO/actions/runs/41363084003) completed successfully at 6:40 p.m. EST, preserving the exact last-good data from `e15bdcd3f922f918a0090df0209b0c8497ed5460` and its original timestamps. It did not fetch fresh source data.
- The ordinary refresh at the same code revision, [run 41362786746](https://github.com/justinpfisher/ScarbTO/actions/runs/41362786746), initially passed trusted tests but failed closed on HTTP 503 retrieving the official City ward geography. Persistence and deployment were held. After a bounded retry of the failed publisher, **attempt 2 succeeded**: official retrieval, data validation, persistence, Pages deployment and production HTTP verification all passed.
- That retry created data commit **`55fb6dde7b2e02acc34244b2074d7b10c20aa96c`**, the main data commit at that historical checkpoint. The publisher validated **125,022 source rows**, all geocoded, **19,097 Scarborough inspection rows**, **3,324 establishments**, zero unassigned neighbourhoods and **115 retained change events**. The collector's `new_activity: 115` log label reports retained activity, not 115 newly observed events.
- [Successful publisher job 125022450132](https://github.com/justinpfisher/ScarbTO/actions/runs/41362786746/job/125022450132) reports **LIVE VERIFIED** for `https://scarb.to/`, required modules, six official wards, 30 qualified overlay neighbourhoods and the populated snapshot. The stored `published_at=2026-11-01T23:59:37+00:00` is the collector-run start under the existing contract; it is not the City publication time or the actual Pages deployment time. Preserve distinct source/observation/publication meanings.
- Trusted GMKtec tests passed at the deployed code revision: 28 root Python tests, 32 core JavaScript tests, 55 CSI tests, 96 permit tests, 28 selected-calls JavaScript tests, 16 rendered browser cases and standalone beach-history integration. These tests qualify their tested behaviours; they do not qualify an uncollected source or establish physical-device usability.
- A separate public-browser inspection confirmed the new inspection/first-observed date wording, West Rouge selection, visible area chip/panel and the matching accessible results. The cloud browser reported map unavailability and exercised the fallback; it does **not** provide proof of real WebGL map interaction. Full deployed interactive/device acceptance and the three scheduled-refresh/weekly-publication stabilization window remain outstanding.

## Approved UX now in the deployed code

The existing implementation writer released the compact contextual Key, phone-default collapsed Key, desktop area information in the results column, closeable mobile area sheet, focus handling, useful clear/fit empty-state controls, distinct inspection and first-observed dates, placeholder-detail cleanup, separate geographic layers, MapLibre 6.4.1 and library/WebGL fallback. Independent rendered tests and public HTTP checks passed.

The approved 1 November UX follow-up clears an incompatible selected area when switching between neighbourhood and ward overlays and explains the reset. Closing the information panel or hiding outlines still retains the selected area. This refines the older 31 October switching rule; no hidden incompatible geographic filter should remain. The broader P2 work, including stable public record/area URLs and complete resident journey acceptance, is not thereby complete.

## Feed coverage and source boundaries

- **DineSafe is the production feed.** Keep `typeDesc` as inspection detail; preserve official outcomes and missing-value normalization. Area selection does not change the six-ward inclusion rule. The optional 30-area majority crosswalk is not complete administrative containment; the adjacent thirty-first DineSafe-assigned neighbourhood is a separate geographic inclusion fact.
- Selected police calls remain grouped, on demand and division-level for Divisions 41–43. They are not individual calls, confirmed crimes or neighbourhood incidents. Keep source-specific stale/unavailable handling.
- Beach content remains a dated historical sample preview, not current swimming advice. Draft PR #4 is not a qualified live operational advisory feed.
- Planning and permit public exports remain disabled. No complete capture, full identity/geographic reconciliation or public projection was certified by this investigation. Do not infer construction completion from source status.
- Historical police neighbourhood publication remains in its separate, already-approved conditional lane. Preserve complete nonoverlapping Toronto quarters, five approved categories, counts 0–4 grouped and exact 5+, qualified crosswalk/reconciliation, no addresses/incidents/rankings, no ward proration and its independent source/privacy conditions.

## Historical P4 source feasibility - 1 November bounded research

On 1 November at approximately 5:09 p.m. EST, the existing allowlisted City routes returned bounded samples with matching before/after generation and exact-count metadata. These are **publisher-advertised totals, not completed captures**:

| Collection | Advertised rows at probe | Qualification status |
| --- | ---: | --- |
| [Development Applications](https://open.toronto.ca/dataset/development-applications/) | 26,648 address rows | Reachable; full capture, identity and planning geography outstanding |
| [Active permits](https://open.toronto.ca/dataset/building-permits-active-permits/) | 200,066 | Reachable; full capture and geographic/accounting qualification outstanding |
| [Cleared permits since 2017](https://open.toronto.ca/dataset/building-permits-cleared-permits/) | 448,339 | New generation; inspect old checkpoint before any reuse |
| [One Address Repository](https://open.toronto.ca/dataset/address-points-municipal-toronto-one-address-repository/) | 525,381 | Reachable; coordinate interpretation and source-wide geography outstanding |

All four metadata responses identified the Open Government Licence – Toronto. Small controls reconfirmed multi-address planning identity and the approved `GEO_ID` to `ADDRESS_POINT_ID` join. The documented official 4326 CSV accepted a 4 KiB HTTP 206 request; its first allowed projection matched the datastore control. This did not qualify all datastore geometry. The older OAR tunnel failure was not reproduced in this research environment; trusted-worker access must still be checked.

The older state record described 106,000 of 446,979 cleared rows from an October 28 generation, including an uncertified final 6,000 rows. Those private staging files were not inspected here. The 1 November probe reported a different generation: do not append into that old candidate. Validate/quarantine the preserved prefix using the existing resumable rules before starting a new generation.

Remaining engineering work is specific: planning lacks qualified map locations; reduced OAR lookup/accounting can confuse known outside-Scarborough records with genuinely unlocated records; record-specific planning links and safe public descriptions require qualification; production export/history/retention are not yet established. Preserve all count, generation, hash, overlap, EOF, identity, geography, privacy and licence gates. Full acquisition supports validation, not an obligation to send every historical record to a phone.

## P1 identity and voice — direction adopted; lockup under review

The owner adopted the Lake & Land visual direction and original three-line wave/cliff mark, and selected “Scarborough. I looked into it.” The connected-contour treatment is the working lockup direction; the production artwork still needs visual qualification. The approved Scarb editorial voice is prepared on a local branch, including homepage/footer, DineSafe captions, neighbourhood pages and the RSS channel description. It is not deployed.

The eight-record main specimen uses frozen, attributed records from the 1 November 11:51 a.m. snapshot; it is not current public data. Its source/date statements and 27 contrast calculations were independently checked. Prototype browser checks are not production WCAG certification or resident research. Existing approved UX work can continue independently of brand adoption.

## Execution policy - 1 November checkpoint; recheck before execution

- Main's trusted test job runs on **`gmktec-scarbto-01`**, runner ID 22, labels **`self-hosted`, `Windows`, `X64`, `scarbto-gmktec`**. Job evidence establishes assignment and substantive execution. There is no normal `pull_request` execution on the persistent runner and no ordinary hosted fallback.
- The hosted publish job remains the existing narrow essential public-refresh/Pages exception, gated by the trusted tests. The static site remains served when GMKtec is offline, but new refreshes are held while required tests cannot run. On 7 November 2026 the owner separately authorized one conditional, **test-only** fallback when fresh host/workload evidence shows the specific full test cannot safely run on GMKtec: manually dispatch `.github/workflows/hosted-tests-only.yml` from `main` for PR #41 or #42 with `gmktec_unavailable=true`. It uses an ephemeral `windows-latest` runner, `contents: read`, no persisted checkout credentials or secrets, no live-source fetch, no publisher, and no reduced test coverage. Normal trusted-main tests and the publisher gate remain unchanged. This is not routine hosted testing; the combined outside-processing cap is $10/month across all projects.
- PRs #25-#32 repaired the Windows trusted-main route while preserving exact fixture hashes and failure checks. Reboot persistence, unattended service recovery, offline queue recovery and the complete multi-cycle stabilization window have not been newly demonstrated. Do not call one successful retry full stabilization.
- The workflow includes an explicitly dispatched code-only release with exact last-good data/provenance validation. The successful 6:40 p.m. release used the pinned `e15bdcd…` baseline. The subsequent normal refresh created `55fb6dde…`, so another code-only release requires an independently reviewed baseline-pin update; it must not bypass that safeguard. Ordinary refreshes remain available and preserve their existing validation. A code-only release does not invent a source refresh or change original data timestamps.
- **November Actions usage guard:** The owner's 1,000-minute stop threshold applies only to Actions minutes that consume the account's included or billed allowance. GitHub documents standard hosted runners in public repositories, Pages, and self-hosted runners as free; this public repository's standard hosted Ubuntu jobs and Pages deployment therefore must not be counted from raw job durations as allowance usage. Repository-level run metadata does not establish account-wide allowance consumption. No account-wide usage total or automated cap enforcement is verified here. Before enabling any job that may consume included compute, require an authorized account-level billing reading and stop at the 1,000 qualifying-minute threshold for November.
- Older draft PRs #1 and #23 may now overlap merged migration/fixture work. Compare their complete remaining scope before closing; do not merge their stale branches or assume every proposed diagnostic is already implemented. Draft PR #4 remains a separate beach prototype.

## Current next actions and blocked work

1. **P3 neighbourhood pages:** released with PR #41 and verified on 31 canonical/alias production routes. Continue using the published template and qualified identifiers; do not reopen the completed P3 route task.
2. **PR #42 RSS:** the current source candidate is locally qualified on the current main base. The independent reviewer found no blocking source or test issue and requested only the status corrections in this update. After reviewer verification, follow the ordinary merge, trusted-main CI/publisher, and live RSS verification path. The local 50-item render is not a public feed release.
3. **Refresh continuity:** trusted-main run 42649253851 recovered the earlier failed publisher and verified one deployment. Continue checking the scheduled refreshes and weekly publication against the original stabilization criteria; do not call one successful run a completed stabilization window.
4. **P4 planning/permit qualification:** PR #44 only corrected CKAN metadata. Continue source-generation/count, row-identity, complete-capture, licence and geographic qualification using the established resumable controls when the permitted source/runner path is available. Keep all permit exports disabled; the OAR tunnel 403 remains an access boundary.
5. **Remaining P0-P8 scope:** finish P2 resident journeys, planning and permit qualification, P5/P6 development representation and integrated briefs/change history, and the remaining stabilization checks. Keep each source's gaps visible until qualified; preserve the adopted direction and standalone mark; do not use an unqualified lockup.

The historical 1 November P4 research above is not a current dispatch or proof that a capture is prepared for immediate execution. This record itself is source-free; no source rows, private staging material or heavy tests were run for this update.

## Operational links

- [Open pull requests](https://github.com/justinpfisher/ScarbTO/pulls)
- [Actions and refresh history](https://github.com/justinpfisher/ScarbTO/actions)
- [Published source snapshot](https://scarb.to/data/snapshot.json)
- [Toronto Open Government Licence](https://open.toronto.ca/open-data-licence/)

Do not record prepared, reviewed, tested, merged, deployed or live work as interchangeable states. The integrated resident release remains in progress.
