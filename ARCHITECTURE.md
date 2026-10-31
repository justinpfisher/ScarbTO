# Scarb.TO — architecture and product decisions

This is the current *decision record*, not a claims-of-deployment ledger. For validated implementation status see [CURRENT_STATE.md](CURRENT_STATE.md); for agent requirements see [AGENTS.md](AGENTS.md).

## Mission and experience

Provide a current, source-linked answer to **"What is happening and changing in my neighbourhood?"**, initially for Scarborough, Toronto.

- Main screen: a large usable map, compact layer/time/neighbourhood controls, an accessible synchronised results list and clearly dated recent changes.
- Default: curated meaningful recent changes, with other information layers a tap away. Don't overwhelm the default view with every historical marker.
- Mobile-first, keyboard-accessible, approachable, credible and locally distinctive. No required account or intrusive advertising.
- Browser-saved filters first; followable places, optional alerts and limited source-linked community corrections at MVP or later when warranted.
- Editorial independence takes precedence over sponsorship. Free source-attributed briefs and possible paid licensed aggregate reports may be added only following evidence of useful demand.
- Minimise maintenance (2–4 hours/week) and incremental cost (C$25/month ceiling, C$0 preferred).

## Current delivery architecture

- **Static web app:** HTML/CSS/ES modules, MapLibre and OpenFreeMap delivered via public GitHub Pages/CDN. The public site must remain available when GMKtec is offline.
- **Small source adapters:** each fetches an authoritative source, validates metadata and schema, normalises identities, geographic references and timestamps, compares with the previous valid state, and publishes reusable records.
- **Geo accuracy:** DineSafe establishments are selected within the six City of Toronto Scarborough ward polygons. The Scarborough Community Council polygon is a distinct **display boundary**. Never use a visual boundary as an undocumented record filter.
- **File-backed data:** current JSON/CSV snapshots and a small append-only change history where necessary. No database, server-side user identity, streaming bus or separate analytics platform for the PoC.
- **Fail-closed delivery:** validate sources, duplicates, schema, count changes, valid geography, publication readiness and licensing. Hold anomalies; retain last-good data; show source and publication freshness; permit rollback.
- **Independent timestamp fields:** inspected/occurred, source updated, collector checked, first observed, public published. Don't infer one from another. Don't present a recently checked unchanged City dataset as an actual newly issued update.
- **No location invention or privacy shortcuts:** police calls may be division-level aggregates, not precise incident locations; historical water samples are not current beach advisories.

## Execution and deployment policy

GMKtec is the default for trusted development, tests, builds, ingestion and GitHub Actions. Applicable jobs select a verified Scarb.TO-authorised self-hosted runner. There is **no automatic GitHub-hosted compute fallback**. Never run untrusted public PR code on persistent GMKtec infrastructure.

A narrow, documented hosted exception is possible for **essential public feed refresh or public static delivery** where offline-home-computer dependence would materially impair availability. Restrict privileges and cost, and do not extend the exception to routine software builds/testing.

**Transition status:** The existing main workflow still uses hosted `ubuntu-latest`, while [PR #1](https://github.com/justinpfisher/ScarbTO/pull/1) proposes a GMKtec runner that is not independently verified operational. Safely migrate after runner registration and recovery verification; don't break the daily public feed to satisfy a policy on paper.

Use targeted tests for small changes, broader browser tests for UI releases, and production checks after deployment. Close superseded PRs, keep the authoritative project status in `CURRENT_STATE.md`, and avoid extra manual gates for previously authorised ordinary work.

## Source roadmap

| Stage | Public value | Qualification boundary |
| --- | --- | --- |
| PoC: DineSafe | Latest recorded outcomes and *observed* inspection changes on a Scarborough map | Official source, stable IDs, actual location, current inspection date, links, freshness and valid publication |
| MVP: permits/development | New/changed applications and permits by neighbourhood | Full collection, semantic identity, spatial accuracy, source date meaning, privacy and licensing; do not confuse a permit with construction underway |
| MVP: police/public safety | Carefully bounded, meaningful public incident summaries where available | Historical-vs-current and geographic uncertainty clearly labelled; no sensitive individual calls or invented precision |
| Seasonal: beach quality | Verified dated advisories and samples relevant to residents | Current-season official data and actual status rules; off-season gaps disclosed |
| Later: elections | Verified local candidate and election information | Electoral boundaries, jurisdiction, dates and official confirmation |
| After useful core | Corrections, alerts, community publication, reporting and revenue | Minimal moderation, privacy, licence rights, user demand and editorial independence |

An already-merged synthetic adapter or historical beach sample does **not** qualify as a new working public feed.

## Approved optional neighbourhood/ward area explorer (31 October 2026)

**Approved for implementation and public release:** Both boundary overlays off by default. The user can select **Neighbourhoods** or **City wards**, exclusively, and choose an individual polygon by tapping it or by an accessible area selector. Selecting an area filters the existing DineSafe map markers and list and opens a compact information panel (desktop side panel; mobile bottom sheet). Clear area removes only the geographic filter; closing the panel or hiding the outline does not silently clear it. Switching overlay types keeps a visible existing area chip until the user chooses a replacement or clears it. “Show all Scarborough” controls the camera, not the filters.

**Keep distinct source geography:** The production DineSafe establishment inclusion is based on the six official Scarborough municipal ward polygons, 20–25. The historical police source’s **30 whole neighbourhoods** are a verified majority-area selection from the 158 City neighbourhoods (2022 v3.0), not publisher-supplied administrative membership. The existing DineSafe map may include a thirty-first neighbouring geometry for establishments inside a qualifying ward. Do not relabel small boundary slivers as full Scarborough membership. Neighbourhood-to-ward intersections are measured (some truly split); largest-overlap is never complete containment.

**Representative integrity:** Source municipal officeholders from the City's official directory and certified election results using effective term dates (for example, October 2026 certified election versus November 15 term start). Current MPPs and MPs come from their own official directories, vacancies and **distinct provincial/federal riding boundaries**. Until electoral-boundary intersections and reuse terms are independently qualified, provide official address-lookup links without collecting addresses or telling everyone in a split neighbourhood that one representative serves them.

**Data release boundary:** DineSafe establishment counts and last reported inspections are eligible for the area panel, with source/publication timestamps and data limitations. Do not activate unqualified historical police neighbourhood reports or permit/development information. Historical police publication, when independently approved, uses **complete non-overlapping Toronto reporting quarters**, five approved categories, counts 0–4 shown only as “0–4” and exact 5+, no events/addresses/rankings/incidents, no disaggregated ward figures, no neighbourhood-area proration. Keep applications, issued permits and active construction distinct.

**Delivery sequence:** Release A = optional polygons, synchronized DineSafe selection, source links and City councillor details. Release B = verified provincial/federal electoral overlaps and separately source-qualified permit/development information. Release C = optional historical neighbourhood crime panel **only after** existing privacy/source/publication gates pass; never compete with or interrupt the existing CSI work. Reuse MapLibre, existing static sources, file-based history, browser preferences, GMKtec-first trust and Pages. No new paid service, credentials or permanent database.

## Small, reusable change archive

Preserve validated observed changes beyond the current 365-day activity display window through a simple versioned monthly archive if needed. A minimal event records source and record ID, place/area, original event date, observed date, change kind, provenance and source quality. Do not backfill invented observations from the baseline; don't add a database before file sizes or real demand justify it.

These files should support maps, lists, neighbourhood update pages, RSS and eventually attribution-rich community briefs. Generate static summaries from verified records first; no paid summariser is required.

## Safe operations and unresolved matters

- Preserve original data licences, attributions and credible source links.
- Distinguish last validated snapshot from real current source status.
- Keep repository history, data snapshots, public access and explicit rollback path.
- Verify the actual `scarb.to` production HTTPS response, data and mobile map after releases; a successful CI job alone is insufficient.
- Known immediate corrections include malformed DineSafe address placeholders, mislabeled inspection details and source-versus-publication freshness.
- Confirm runner availability and proper isolation on the physical GMKtec before activating proposed infrastructure workflows.

