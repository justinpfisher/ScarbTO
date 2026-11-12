# Scarb.TO — approved Community Publishing specification

**Decision date:** Thursday, November 12, 2026.  
**Status:** Owner-approved scope and implementation handoff; not a claim of implementation, source qualification, partnership, deployment or live verification.  
**Coordinator:** Dot, sole release coordinator and shared-file integration owner.  
**Relationship:** Approved follow-on to P3/P6/P7, alongside the existing resident-release commitments. This is not a new acceptance gate for the original November 1 release.

## 1. Authority, purpose and existing decisions

The owner selected a recurring, preferably free community editorial contribution; a combination of local updates and a neighbourhood snapshot; a publication-led feature powered by Scarb.TO; automatic generation with publisher approval; and a self-service feature for any supported neighbourhood. They subsequently approved reusable custom boundaries for community newspapers and organisations, website embeds, and an automatically composed Scarb update describing changes since the previous edition within a hard word or character limit. Final instruction: “Great. Let's lock this in. Do what you need to do within the chat. Save what's needed to lock it into the repository, and provide me a handoff prompt to give to Dot to coordinate the implementation.”

This document records that approved result. Dot chooses the smallest technical implementation consistent with [AGENTS.md](AGENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md), existing source contracts and current release evidence in [CURRENT_STATE.md](CURRENT_STATE.md). Field names and file organisation below describe required meanings, not a mandated new framework. Preserve source integrity, existing independent review, exact-candidate qualification, runner restrictions, ordinary merge, Pages deployment, live verification and stabilization.

Scarborough residents remain the primary audience. Community organisations and publishers reuse the same qualified information; this is not a separate newsroom, original-reporting programme, CMS or data-acquisition programme. DineSafe correctness and freshness remain the first source priority; qualify further feeds one at a time. Do not substitute this feature for the already-approved planning/permit commitments, repeat completed fixes, or hold unrelated improvements for newspaper specifications.

Target incremental recurring cost C$0; ceiling C$25/month. Preserve the overall 2–4-hour weekly maintenance target. No new paid APIs/services, monthly owner story-writing or content approval duty, external outreach, publication purchases, partner claims or access/security changes are authorised. Normal technical maintenance and required development review remain necessary. Publisher proof approval is the publisher's work, not a Scarb.TO curation queue.

Use the latest owner-approved Scarb voice for every generated heading, control, article, source explanation, legal/fine print and accessibility string. Use Canadian English and readable verified weekday dates where an individual date is shown; preserve precise structured timestamps separately. Adopt the separately approved visual identity through Dot's existing brand work; do not reopen the identity decision or invent a newspaper-specific replacement.

## 2. One information pipeline, three presentations

| Presentation | Required behaviour |
| --- | --- |
| Scarb.TO neighbourhood/community page | Prominent local map, matching accessible list, qualified updates and source/coverage details; no map dependency for essential information. |
| Print/editorial package | Publisher-selected geography, topics, period, copy length and dimensions; a frozen proof, ready-to-place PDF, editable text and useful separate assets. |
| Website embed | A lightweight responsive panel showing the same qualified facts, updating after validated Scarb.TO publication without a new owner approval each time. |

A map, newspaper feature and widget must not maintain different versions of a fact. Reuse normalised records, stable source identities, history and shared presentation rules. Presentation may differ; official outcomes, limitations, dates and attribution may not.

## 3. Reusable geography and coverage profiles

### 3.1 Keep geographic meanings separate

1. **Official City neighbourhoods:** preserve official identifiers, polygons and their source/version. Do not redefine them to fit an organisation.
2. **Community organisation territory:** a documented membership, representation or service area. Record which meaning applies; it is not automatically editorial coverage.
3. **Editorial coverage:** the territory a publisher chooses for a feature. It may include whole City neighbourhoods, a verified custom polygon, multiple polygons and optional nearby areas.
4. **Print distribution:** where copies circulate. Keep as separate optional metadata; do not automatically use it as a reporting filter.

Areas may overlap. A source entity/change appears once in a combined feature, using qualified identities rather than name/address guesses. Preserve separate core and nearby labels. The same genuine update may appropriately appear in different independent publications; do not impose global cross-publisher exclusion.

### 3.2 Implement custom boundaries, without a GIS editing platform

Support both saved sets of existing City neighbourhood IDs and independent, versioned GeoJSON Polygon/MultiPolygon boundaries. The reusable custom-boundary path is part of the approved deliverable, not indefinitely deferred. Use existing polygons where they adequately describe the requested coverage; do not manufacture a custom shape for every organisation.

Each independent boundary needs a stable ID, human-readable name, purpose, source URLs/document references, rights basis, source/review dates, version/hash, verification status and geometry. Keep effective dates when the source establishes them; never invent an effective date from the collection date. Preserve the prior version for historic editions. Separate an organisation-supplied/confirmed boundary from Scarb.TO's interpretation of a public description; source-verified does not mean organisational endorsement.

Validate coordinate reference/order, geometry validity, holes/multipart areas, plausible Scarborough extent, overlaps, border behaviour and known inside/outside examples. Establish one documented inclusion rule for points exactly on an edge. Check uncertain or borderline locations rather than implying address-level certainty. Store a full matching geometry separately from any simplified drawing geometry; display simplification must not change counts.

Do not alter DineSafe's qualified six-ward acquisition/inclusion rule. A custom area filters already-qualified records. Where a requested territory extends beyond available source geography, disclose the uncovered area or disable complete-area claims; never silently report partial coverage as a complete total. A blocked or ambiguous custom boundary must not block existing verified neighbourhood selections.

### 3.3 Data compatibility is source-specific

- Qualified point records can be matched to the custom polygon using their supported location. Historic changes require the relevant historic location/assignment; do not silently relocate old events using today's address.
- Whole-neighbourhood statistics cannot be split into partial areas by area/population proration. Combine non-overlapping aggregates only where definitions, periods, denominators, licence and suppression rules permit it. Do not reveal suppressed small counts through arithmetic or overlapping profiles.
- Division-level police calls remain division-level; they are not neighbourhood incidents or crime totals.
- A beach location can identify a relevant station, not establish that a sample describes all shoreline or today's swimming conditions. Any nearby-beach association must be explicit.
- A changing boundary is not an underlying neighbourhood event. Explain boundary/profile changes and rebase comparisons; do not manufacture a trend from different footprints.

### 3.4 Save settings without accounts or recurring administration

A profile retains coverage references/versions, core/nearby choices, topics, output preferences, copy limit, preferred layout and relevant publication specification. Initial self-service selections use validated shareable settings and browser-local persistence, with portable settings/edition receipts for backup or another device. Avoid collecting personal addresses, member lists or private contact information.

Named, source-verified organisation definitions may be small repository files reused by any profile. Do not create a public write endpoint or put a GitHub token in the browser. A public link is neither authenticated organisation ownership nor a trusted approval credential. Browser-local storage is not cross-device synchronisation; make that limitation visible. No required sign-in, central approval database or publisher account system in the first release.

## 4. Default print workflow: changes since the last edition

The primary journey is:

**Choose saved coverage → choose topics → choose previous edition or dates → set words/characters and output size → generate and preview → publisher approves the proof → download and retain the next-edition receipt.**

Start from “Download for a community newspaper” on a neighbourhood page, preselected to that area, or from a central Community Publishing entry. The main resident map may link to this function without crowding its primary controls. Organisations without print editions choose an embed from the same interface.

### 4.1 Reporting dates and reliable continuity

Keep the previous issue's print/publication date separate from its information cut-off. Default the next reporting interval to **after the previous finalised information cut-off through the requested end**, normally today in America/Toronto. Maintain precise cut-offs/watermarks internally so consecutive editions do not overlap or skip records. Explain the default in ordinary date language.

Offer explicit date selection, including a last-print date when no earlier receipt exists. Treat that as a user-selected starting point, not proof of what was included before. Show the start actually used; do not invent a prior edition. Future issue dates do not make future records available. Invalid/reversed dates or a period before retained history must produce a clear limitation or prevent a misleading comparison.

A request ending “today” does not certify current source information. Keep each source's successful check, upstream date, usable history interval and last qualified release separate. A stale/unavailable module must be disclosed or withheld; it must not silently advance its last-covered watermark. Do not manufacture a common fresh date across sources with different reporting schedules. A successful unchanged download is not a new City publication.

Primary change eligibility uses committed, meaningful changes first observed within the reporting interval, with original event/inspection dates beside them. Late-arriving older records may be described as newly reported/added information, never as an event that happened today. A newly collected establishment is not necessarily a new business. A comparison of only two current snapshots cannot claim every intermediate transition.

For each finalised package, retain the candidate event IDs, included event IDs, source-qualified release/history references, omissions and their reasons, geographic/profile versions, requested period, actual per-source coverage, original generation time, copy/layout version and output hashes. Distinguish omission for space, disabled topic, insufficient evidence and unavailable source. Merely generating, previewing or downloading a draft must not advance the previous-edition marker.

Previously included events are excluded unless a genuine later change, explicit follow-up or correction warrants inclusion. Omitted older events must not automatically reappear as new news. If topics or geography change, explain the changed selection and any catch-up context instead of claiming an equivalent comparison. The publisher may mark a proof finalised in their own saved state; this does not prove actual newspaper publication or organisational approval to Scarb.TO.

### 4.2 Snapshots and quiet periods

Keep a dated neighbourhood snapshot separate from changes over the reporting interval. Use compatible coverage/definitions before calculating comparisons or percentages. A latest snapshot at the end of a period is not a period total.

When there are no eligible changes, say that no new updates were found in the sources checked, with actual coverage/freshness. Offer an optional clearly dated snapshot or no feature. Do not invent a story, call missing sources zero activity, silently expand the period, or pad text to meet a target. Retain the existing weekly/RSS rule that a quiet period does not create artificial news.

## 5. Automatically composed editorial copy in Scarb's voice

Scarb prepares a coherent, source-grounded editorial update from the selected geography, qualified topics, reporting interval and space limit. “Editorial” here means explained information and evidence-grounded perspective, not invented reporting, quotes, visits, motives, public reaction or safety guarantees.

Use deterministic source-grounded composition first, sharing normalised facts and voice rules with other outputs. Choose clear priorities and stable tie-breaks so identical inputs reproduce the same selection and copy. Lead with useful, verified changes rather than sensationalism. Do not force equal topic coverage when the evidence does not support it. A topic switch affects eligibility, not permission to publish unsupported claims. A concise snapshot, changes-first article or balanced roundup can be presentations of the same evidence, not separate data products.

Every factual claim and number must have supporting record IDs, source references and dates in the edition receipt. Automated validation must check supported facts and constraints, not simply ask the text generator whether its own prose is correct. Deterministic templates do not remove the need to validate completeness and meaning. Preserve full qualified inspection findings where summarised, exact official outcomes and consequential limitations; incomplete inspection evidence cannot support a comprehensive-sounding summary.

### 5.1 Hard word and character limits

Allow a hard word limit or character limit, with live counts and a clearly displayed counting rule. If both are supplied, satisfy both. Count the final exported copy, not an earlier draft. The default editorial-copy count includes its heading, body and inline qualifications; show the separate source/footer allowance and the total placed-panel count so the publisher can constrain the whole panel when required. Count spaces/punctuation in character limits and document Unicode/newline handling; use the same counter in preview, export and tests.

Never truncate a sentence or strip an essential warning, official outcome or attribution to meet a limit. Prefer fewer verified items and complete sentences. If even a minimal accurate version cannot fit, explain that the limit is too small and offer a shorter selection/larger space. A limit is a maximum, not a padding target.

Routine copy uses readable dates, not fractional timestamps. Precise date/source information stays in the receipt and evidence view. For serious inspections, closures, crime or health limitations, use the calm, accurate register already required by the editorial guide.

A recurring paid language-model service is not required or authorised. Any later model-assisted route must preserve grounded claims, deterministic fallback, privacy, source terms, validation and separately applicable cost authority; it is not a prerequisite for this release.

## 6. Print layouts and download package

Editors choose topics and available space; the layout automatically adapts to the content. Use a small family of tested templates rather than unconstrained AI-designed pages. One topic may suit a focused article; two or three may suit a lead article and snapshot/sidebar; dense statistics may use a table or chart where the source supports it. Do not fill missing topics with placeholders that look like real findings.

There is no universal quarter-page size. Store exact width/height, units, orientation, margins, colour/grayscale needs, column constraints and relevant production requirements in a publication preset after they are verified. Advertising artwork dimensions are not proof of an editorial slot's dimensions. Unconfirmed presets must be labelled generic/provisional rather than publisher-approved. Quarter-page is a useful initial layout family, not a compulsory allocation.

Required initial outputs:

- A ready-to-place PDF with crisp text/vector elements where practical, embedded permitted fonts, correct page dimensions and appropriate raster resolution.
- Editable plain text with the same facts and explicit attribution; add DOCX only where useful, not as a blocker for the baseline.
- A high-resolution image alternative at the chosen physical dimensions/resolution, with an accessible text companion. Do not make raster text the only production route.
- A separate map when selected, with intact attribution and reuse rights; omit it when it reduces usefulness or readability.
- A machine-readable edition receipt/settings file and a human-readable source/coverage note.

Preview and export must use the complete qualified selection, not only the first screenful behind “Show more.” Distinguish intentional editorial selection from incomplete data. Choose fewer items or a larger layout instead of unreadably small type. Test actual rendered PDFs/images, grayscale, clipping, long names, Unicode, source-footers and QR readability at real size; browser print-media CSS alone is not proof of a press-ready file.

Include coverage name/definition, reporting period, information cut-off, source attribution and a readable web reference; a QR code supplements rather than replaces the text reference. Keep safety-critical limitations beside the relevant statement. Verify print/export rights for maps, tiles, fonts, logos and source content; web display permission is not automatically redistribution permission.

The feature belongs editorially to the publication, with a modest Scarb.TO information credit. Do not use an organisation's logo or imply a partnership/endorsement without applicable authority. Free editorial acceptance is a goal, not a commitment from any newspaper. No automated external sending or submission.

## 7. Frozen editions, corrections and portable state

A finalised print package is immutable evidence: retain its chosen facts, geography, settings, data/history references, precise cut-offs, generation time and final wording. Subsequent source updates do not silently replace it. Corrections create an explicit revision and explanation while preserving the original edition identity and factual history; explain boundary/template-only revisions too. A hash without retained supporting content is not sufficient recovery.

Provide a stable version-pinned evidence/edition web reference and a current corrections route. A QR pointing only to today's changing neighbourhood page is not an adequate record of the printed claims. Dot must prove the supported static/file-based route for retaining/reconstructing the cited evidence and issued editions; do not claim durable public archival of arbitrary client-generated text until it actually exists.

The initial no-account implementation may retain a publisher's finalised copy and receipt in browser storage plus a downloadable/importable package, anchored to immutable public source releases. Clearly distinguish local publisher state from an officially archived Scarb.TO edition. Do not expose private draft copy or invent a central authenticated publication registry. Named static editions and source releases should be generated/retained through the existing validated build, not a new monthly owner commit or curation duty. Implement the minimum automatic retention needed for accurate citations, corrections and reproduction; no separate database by default.

## 8. Website embeds

Provide a dedicated, list-first responsive iframe route rather than embedding the entire homepage. A compact update/snapshot widget is included in the first complete Community Publishing delivery. Map-heavy variants can follow demonstrated need; the main neighbourhood pages still require prominent maps.

An organisation chooses approved coverage, available topics, suitable length/layout and a rolling period, then previews and copies the embed code. Ordinary updates use the latest successfully validated public release; installing the live widget is not a request to approve every subsequent change. A frozen edition view, when offered, must be clearly distinct from the live widget.

Preserve source links, actual source-check/period labels, stale/unavailable/empty states and last-good retention. Changing the date alone must not keep old material looking new. Define whether an already-open widget refreshes or refreshes on load; do not claim continuous monitoring without the tested behaviour.

Use a lightweight area-specific public projection where supported; avoid forcing each embed to fetch the full Scarborough snapshot, all archives or mapping assets. No unnecessary analytics, advertising, authentication, location prompts or tracking cookies. Ordinary hosting/network requests still occur; do not promise zero data processing. Keep configuration allowlisted, validate imports/query values and safely escape source and publisher text. No arbitrary script/HTML or remote configuration URL ingestion.

Test on a genuine cross-origin test host, at desktop/mobile widths, with keyboard/screen-reader semantics, long copy, blocked framing, missing scripts/network, stale data and fallback links. A widget preview on Scarb.TO alone does not prove third-party embedding. Honour existing security headers and platform restrictions; do not weaken them to make embedding work. If resize messaging is introduced, validate origins and message schema. Some host platforms may not permit iframes: provide the normal link alternative without assuming permission to alter the organisation's site. No third-party installation or outreach without authority.

## 9. Source availability and eligibility

At the inspected repository baseline, DineSafe and its qualified observed-change history provide the initial source family. Inspection outcomes are not customer restaurant ratings. Selected police calls cannot be recast as neighbourhood crime. Historical beach data is not current advice, and planning/permit/public crime exports cannot be enabled by this document. Recheck current main and actual contracts before implementation; do not preserve an outdated status claim if a feed has since been independently qualified.

Present unsupported, insufficiently fresh or geographically incompatible modules as unavailable with a clear reason. Where a source publishes whole quarters, do not transform it into a purported monthly count to fit a newspaper interval. A newly published quarterly report can be described using its real reporting period only after source/privacy qualification.

The export must preserve official IDs, meanings, URLs, licences, event dates, publication dates, collection/observation dates and limitations. A new output surface does not expand the public-field allowlist, source rights or existing geographic scope. Last-good retention is not permission to label old facts current.

## 10. Initial candidate inventory — research leads, not partnerships

This is a prioritised intake list carried forward from the owner's attached research handoff and this discussion. **This documentation save does not independently reverify current activity, exact boundaries, rights or editorial specifications.** The items below are candidates and source leads, not qualified public organisation profiles. Preserve that distinction when implementing a directory. Do not restart a broad survey or create every candidate polygon before the first useful release.

| Priority/candidate | Reported source lead or useful test | Verification needed before a named exact profile |
| --- | --- | --- |
| Pilot: Centennial News / CCRA | [CCRA](https://ccranews.com/) and [newspaper page](https://ccranews.com/news/local-news/documents-grid-2/) | Prior discussion reported differing western-boundary descriptions (Highland Creek versus Colonel Danforth Road); resolve source authority, association/editorial/distribution meanings and actual print requirements. Do not silently choose one. |
| Early: West Rouge Life / West Rouge Community Association | [Association](https://www.westrouge.org/) | Verify current publication activity and exact described edges against usable source geometry; City neighbourhood equivalence is not presumed. |
| Early: Guildwood News & Views / Guildwood Village Community Association | [Association](https://www.guildwood.ca/) and [constitution](https://www.guildwood.ca/constitution) | Inspect the actual irregular boundary map and its precedence over prose; qualify digitisation and reuse. Strong candidate for first unambiguous custom-boundary validation if CCRA remains unresolved. |
| Early: The Villager / Highland Creek Community Association | [Association](https://myhighlandcreek.org/) | Distinguish association territory, editorial coverage and nearby distribution; use a clearly labelled City-area preset while exact coverage is unverified. |
| Broader-format test: Bluffs Monitor | [Publication](https://www.bluffsmonitor.com/) | Reverify active publishing, editorial communities, distribution and production specifications. A collection of neighbourhoods may be sufficient. |
| Later: Beach Metro Community News | [Publication](https://beachmetro.com/) | Separate the Scarborough portion from the publication's broader geography; no automatic expansion of Scarb.TO acquisition scope. |
| Additional boundary/widget leads | Glen Andrew, Curran Hall, Cliffcrest–Scarborough Village SW ([association](https://cliffcrestscarboroughvillagesw.ca/)) | Obtain original descriptions/maps, current status and rights. Do not convert approximate road/creek descriptions to claimed exact territories. |
| Discovery pool | West Hill, Morningside Heights, Midland Park, Dorset Park, Maryvale, Agincourt Village, Scarborough Rosewood and other groups identified in the City's 2024 Good Neighbour Guide handoff | Directory inclusion is not current activity or a formal boundary. Prioritise demonstrated need and existing source evidence. |
| Historical/digital research leads | The Voice / Bluffs Voice, Scarborough Mirror, The Discourse Scarborough | Verify current identity/activity and print-versus-digital role before listing as active print outlets. No current status asserted here. |

The system is reusable for additional Scarborough organisations; that does not create an obligation to validate every possible group before shipping. An unresolved publisher footprint/specification holds that exact preset, not generic print, qualified City-area combinations or web embeds. Contacting a publisher remains a separate protected action; use available original public sources first and report a specific unresolved choice only when necessary.

## 11. Integration sequence and acceptance evidence

Use the existing queue and `CURRENT_STATE.md`, not another project tracker or competing release. Dot may deliver working increments, but must retain the complete approved result through stabilization.

| Increment | Minimum useful result |
| --- | --- |
| Shared coverage | Reusable qualified City combinations and versioned custom polygons; source-compatible selection and deduplication; portable profiles. |
| Edition-aware publishing | Previous-cut-off/date selection, topic selection, changes plus optional snapshot, hard-length Scarb copy, proof approval and receipt continuity. |
| Production outputs | Actual PDF, editable text, raster alternative and optional attributed map; generic sizes plus verified publisher presets; immutable evidence/correction route. |
| Web reuse | Working lightweight cross-origin embed, clear live/frozen distinction, copyable configuration and usable fallbacks. |
| Stabilization | Consecutive edition continuity, a validated refresh reflected in an embed, recovery/rollback, corrections, practical maintenance/cost checks and verified public journeys. |

Acceptance tests must cover:

1. One City area, several areas, overlap, a genuine verified custom polygon, multipart/edge cases, outside-source coverage, invalid geometry and a boundary-version change. Map, list, copy and counts agree; overlapping areas do not duplicate identities.
2. Consecutive editions, exact cut-off edges/time zones, late-arriving historic records, genuine recurring changes, same-day later observations, unchanged re-downloads, first-ever exports, older-than-retained history, unavailable sources and changed topics/coverage. Drafts do not move the prior-edition state; omitted older events are not relabelled new.
3. Exact final word/character caps, Unicode/long names, count scope, impossible limits, no-change output, incomplete findings and stale data. Source traceability and essential warnings survive shortening. No fabricated significance, outcomes or freshness.
4. Complete underlying selections rather than visible pagination; exact PDF/image sizes, readable grayscale, no clipping, consistent text/graphic outputs, source/footer space, useful map attribution and working readable/QR references.
5. Reproduction from saved inputs and retained evidence, finalised-versus-draft state, changed boundary/source versions, clear corrections and browser receipt export/import without credentials or private-data leakage.
6. Actual third-party embedding, responsive/keyboard/accessibility behaviour, disabled framing/script/network fallbacks, lightweight data use and honest live refresh/staleness behaviour.
7. Required independent review and exact-head tests through authorised execution, normal merge/Pages release, separate verified-live checks and the existing stabilization discipline. No routine hosted-runner fallback; never execute untrusted PR code on a persistent personal runner.

These are focused acceptance cases for this feature, not new approval ceremonies. Do not claim print correctness from HTML alone, live embedding from a same-origin preview, source qualification from a successful download, or deployment from a green test.

## 12. Current repository basis and coordinator handoff

Documentation baseline inspected: main `e952b0f3142450512739513a1d024d61794c1c18` (PR #55 merge), following the [UX decision PR #54](https://github.com/justinpfisher/ScarbTO/pull/54). [Run 43310533601](https://github.com/justinpfisher/ScarbTO/actions/runs/43310533601) reported success when checked; this documentation work did not independently verify that release live. Always recheck current main, active/unpublished work and Actions before implementation.

Existing reusable components include the neighbourhood page generator, qualified geographic data, geocoded DineSafe collector, committed change history, weekly briefs/RSS and share/print views. Read [the UX investigation](research/ux/2026-11-12-resident-ux.md) for previously recorded complete-print, geographic-wording and data-loading concerns, then check which have since been repaired. Do not reopen closed work from an old checkpoint.

Coordination is recorded on [PR #54](https://github.com/justinpfisher/ScarbTO/pull/54#issuecomment-6836479747). This authoring chat adds only this new root specification to a documentation branch. It does not change shared architecture/state/agent files, application code, source data, generators, dependencies, workflows, runner configuration or production. No independent implementation review, project tests, deployment or live feature verification is claimed.

### Dot's first integration actions

- Reconcile this owner-approved record with current work. Complete the ordinary documentation review and integrate it; do not ask the owner to choose these product decisions again.
- In the existing `ARCHITECTURE.md` community-newspaper section, link this specification and replace the now-outdated “coverage/profile behaviour still to be decided” framing with the approved print/embed/edition-aware scope. Preserve the separate-follow-on boundary and all original release commitments.
- Add a concise approved/pending entry to `CURRENT_STATE.md`, accurately separating documented, implemented, tested, merged, deployed and verified-live states. Do not overwrite newer release receipts with this checkpoint.
- Add only a narrow pointer in `AGENTS.md` so future generators/edits preserve this specification; do not duplicate its full policy text or create another tracking register.
- Implement the smallest complete path through the existing release process. Use an available, well-sourced custom-boundary case while CCRA-specific ambiguity is resolved. Complete unaffected work independently; escalate only a genuine protected action, missing access or material product decision with exact owner steps.

The owner approval is established. Documentation integration is not implementation completion; implementation completion is not verified live operation. Retain these distinctions in every handoff and milestone.
