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

**Execution status (1 November 2026):** Trusted-main tests now select the Windows GMKtec runner using `[self-hosted, Windows, X64, scarbto-gmktec]`; ordinary pull-request execution has been removed from that persistent runner. The separate hosted job remains the existing essential public-refresh/Pages exception and depends on successful GMKtec tests. The static site remains served while GMKtec is offline, but new publication is blocked while its required tests cannot run. Registration and actual test execution do not prove service/reboot recovery or end-to-end migration success; use [CURRENT_STATE.md](CURRENT_STATE.md) for the latest verified result. The older Linux proposal in PR #1 is not the active migration.

Use targeted tests for small changes, broader browser tests for UI releases, and production checks after deployment. Close superseded PRs, keep the authoritative project status in `CURRENT_STATE.md`, and avoid extra manual gates for previously authorised ordinary work.

## Approved integrated resident release (1 November 2026)

The owner selected **the complete resident experience plus qualified development information, publishing useful working stages along the way**, and **shareable neighbourhood briefs on the website plus RSS, with email later**. After reviewing the integrated execution plan, the owner instructed: **"Okay. Lock this in. And get started."** These decisions authorise execution of that plan through the existing checks, normal release process and live verification. Do not ask again for ordinary implementation or milestone approvals. This section is the enduring scope record; the verified delivery ledger remains `CURRENT_STATE.md`.

### Audience, promise and identity

- **Primary audience:** Scarborough residents with practical local questions. **Secondary audience:** neighbourhood organisations, tenant/resident groups and community publishers sharing dependable local information. These are product-positioning choices, not measured visitor demographics or claims of resident testing.
- Core promise: help residents understand recorded changes near them, inspect the evidence and find the next useful step. Keep the service source-linked, mobile-first, approachable and independent of government.
- **Lake & Land is the selected working identity direction.** Complete the original land/water symbol, Scarb.TO wordmark, micro-icons, functional palette, typography, voice and actual product applications outside production. The original branding assignment reserved explicit adoption of the finished identity. Prepare the complete reviewable package before that one decision; liking the concept or approving this execution plan does not represent approval of unseen final assets. Once adoption is explicitly recorded, do not repeat routine cosmetic approval requests.
- The working palette is navy `#173F58`, limestone `#F1EDE4` and restrained clay `#D8A58F`, with Source Sans 3 for interface text and Source Serif 4 used selectively for the wordmark/editorial character. These are proposed design ingredients, not permission to skip contrast checks or reuse the earlier Common Ground tokens as Lake & Land.

### Required complete-release result

1. A coherent Explore experience: synchronised map/list, compact controls, search over qualified public records, meaningful recent changes, accessible details, predictable Back/Forward navigation and shareable public URLs. Essential information remains usable without map gestures or WebGL. Do not put private device coordinates or entered home addresses into shared links.
2. Stable neighbourhood pages using the same qualified geography, record meanings and filters, with source/coverage notices, useful official service links, a limited source-linked correction route and qualified municipal/provincial/federal representation context. Preserve split-area and term/vacancy distinctions; official address lookups remain available without collecting residents' addresses.
3. **Actual planning applications and the approved building-permit companion.** Independently qualify development applications, active permits, cleared-permit collection scope and their locations. A research sample, permit-only layer or links to City tools cannot substitute for the agreed planning coverage. Preserve complete acquisition, identity, geography, public-field, privacy and licence requirements.
4. Development appears consistently in map, list, details, neighbourhood context and observed history. Distinguish applications, permits, approvals and actual construction. Offer active-record browsing alongside recent changes so older active proposals remain discoverable.
5. Shareable website briefs and working RSS from the same validated committed change history, with source links, stable identities, correct dates and visible corrections. No email/subscriber system in this release.
6. Adopted identity integrated consistently after the reserved brand decision, source-safe public operation, tested last-good retention/rollback and verified live journeys.

Existing approved UX is part of completion: contextual compact Key; an unobstructed phone map; dataset-specific controls; coherent area/filter/reset semantics; desktop area information with results and an accessible mobile sheet; precise record/location/count labels; distinct inspection/event/observation/publication times; stable freshness notices; recoverable empty states; non-colour status/selection cues; and a complete accessible list alternative. Preserve both overlays off by default, mutual exclusivity, visible area state and Clear area changing only geography. The approved 1 November UX follow-up clears an incompatible selected area when changing overlay type and explains that reset; closing the panel or hiding outlines preserves the selected area. An explicitly chosen empty period is not silently reset.

### Permanent neighbourhood destinations

The owner specifically proposed an address such as `scarb.to/westrouge`. Implement permanent, useful neighbourhood pages as P3, generated from one reusable template and the same qualified data as Explore. Use a readable canonical route such as `/west-rouge/` and retain the short `/westrouge/` entry as a forwarding alias; do not duplicate pages or change hosting/DNS to achieve this. A stable internal area ID survives spelling/slug changes. Preserve aliases for previously shared addresses.

Each page should prioritise recorded changes and active development, available inspection records, a map/list route with the same selected area, qualified representation, a small set of useful authoritative links, source/coverage information and that area's briefs/RSS. Show only live qualified information; do not populate empty sections with invented events or label unavailable development as zero. A separately maintained news blog, long neighbourhood essay, account system or live directory is not required.

The City lists West Rouge as neighbourhood **143**, which is present in the existing qualified overlay. City social-planning areas can differ from historical/community definitions; name the actual boundary used for each dataset and do not convert a broad source statistic into smaller-area precision. Source: [City neighbourhood definitions and list](https://www.toronto.ca/city-government/data-research-maps/neighbourhoods-communities/neighbourhood-profiles/about-toronto-neighbourhoods/), checked 1 November 2026. A page is an entry point into the same service, with consistent filter meanings, canonical links, accessible HTML content and a shareable area identity.

### Execution packages and dependency order

| Package | Outcome | Dependency |
| --- | --- | --- |
| P0 | Reliable trusted validation, public publication and recovery | Current main, active repair and authorised runner access |
| P1 | Complete reviewable Lake & Land asset/specimen package | Existing chosen concept; production branding awaits adoption |
| P2 | Complete resident exploration and public record routes | Current baseline; P0 for publication; coordinate active UX writer |
| P3 | Useful neighbourhood pages and qualified representation | Shared P2 route/state conventions and qualified geography |
| P4 | Qualified planning/permit sources and locations | Start source feasibility early; preserve every source gate |
| P5 | Development integrated across resident views | P2 plus independently qualified P4 outputs |
| P6 | Web briefs, Updates index and RSS | Area pages and validated event history; DineSafe may stage first |
| P7 | Accurate metadata, sharing/print views and on-site reuse guidance | Real routes/content; adopted assets for production brand artwork |
| P8 | Integrated live verification and stabilization | All required packages, source evidence and brand adoption |

Begin release reliability, identity preparation and source feasibility in parallel, with one writer for each shared file set. Publish approved UX and qualified source-specific stages as ready; do not hold unrelated improvements for the whole programme. The integrated release remains incomplete until the promised development, briefs and RSS work is actually operating and verified. Conditional historical-police work continues separately with its existing owner and controls.

### Briefs and RSS publication semantics

- Generate weekly editions after the last complete Monday-Sunday period in `America/Toronto`, through the next successful scheduled publication. Do not promise an exact delivery hour.
- Weekly news eligibility comes from first observation of a **committed meaningful change** in that period. Show the original source-event date separately. Baseline/unchanged records may provide clearly labelled context but cannot manufacture new-event eligibility.
- Use one deterministic static generator for website editions and RSS. Provide an all-Scarborough feed and neighbourhood feeds where area briefs exist; no CMS, paid summariser or new database is required.
- Distinguish source entity ID, change-event ID and area-period edition identity. Stable edition URLs/GUIDs and original publication dates survive unchanged rebuilds and corrections; material corrections show a revision and explanation. A genuine recurring transition is a new event; retrying the same observation is not.
- A quiet week creates no artificial RSS item. Retain immutable allowlisted evidence supporting published statements with durable references and hashes. A hash alone cannot recover a changed source. Preserve published editions except documented corrections, load history progressively, retain the latest 26 genuine editions in each feed and keep older web editions.
- Bound raw candidate retention while preserving the active validated checkpoint and last-good evidence. Full source acquisition does not require downloading the complete historical source into a phone on initial load.

### Completion evidence and limits

Verify the six resident journeys on actual public routes: find nearby information; understand a change; understand development; check an inspection; return to an area; share information. Retain the reviewed candidate, merged revision, deployed code/data revision, source qualification evidence and production results. Target WCAG 2.2 AA with explicit keyboard/focus/semantic/contrast/reflow checks; automated tests are not resident interviews or an accessibility certification.

Require at least three consecutive scheduled validated refreshes, one real weekly brief-generation cycle, and a genuine public brief/RSS item opened in a fresh browser and a feed reader. A quiet-week cycle is valid when correctly logged but does not replace proof that publication works. An explicitly labelled introductory coverage edition can demonstrate publication if only a valid baseline exists; never invent news. Demonstrate last-good retention and rollback safely outside production failure injection. Time the routine operational review against the 2-4-hour weekly allowance.

Retain C$0 preferred incremental recurring cost, C$25/month ceiling, no extra AI API, no paid font/design/service dependency, GitHub as the authoritative project record, GMKtec-first trust and the narrow existing refresh/hosting exceptions. Email, accounts, push/personalised alerts, live routing, comprehensive business/events directories, ratings/safety scores and open forums are deferred. No external outreach, partner claims, sponsor sales or revenue target is needed to complete the technical release. Do not quietly reduce the agreed result when a source or access dependency is blocked; continue unaffected work and report the exact unresolved requirement.

## Source roadmap

| Stage | Public value | Qualification boundary |
| --- | --- | --- |
| PoC: DineSafe | Latest recorded outcomes and *observed* inspection changes on a Scarborough map | Official source, stable IDs, actual location, current inspection date, links, freshness and valid publication |
| MVP: permits/development | New/changed applications and permits by neighbourhood | Full collection, semantic identity, spatial accuracy, source date meaning, privacy and licensing; do not confuse a permit with construction underway |
| Conditional: historical police information | Carefully bounded historical neighbourhood counts, if independently qualified | Separate approved source/privacy lane; complete quarters, suppressed small counts, no individual incidents, rankings or invented precision |
| Seasonal: beach quality | Verified dated advisories and samples relevant to residents | Current-season official data and actual status rules; off-season gaps disclosed |
| Later: elections | Verified local candidate and election information | Electoral boundaries, jurisdiction, dates and official confirmation |
| After useful core | Corrections, alerts, community publication, reporting and revenue | Minimal moderation, privacy, licence rights, user demand and editorial independence |

An already-merged synthetic adapter or historical beach sample does **not** qualify as a new working public feed.

## Approved optional neighbourhood/ward area explorer (31 October 2026)

**Approved for implementation and public release:** Both boundary overlays off by default. The user can select **Neighbourhoods** or **City wards**, exclusively, and choose an individual polygon by tapping it or by an accessible area selector. Selecting an area filters the existing DineSafe map markers and list and opens a compact information panel (desktop side panel; mobile bottom sheet). Clear area removes only the geographic filter; closing the panel or hiding the outline does not silently clear it. The approved 1 November UX follow-up refines the earlier switching rule: switching to the other overlay type clears an incompatible selected area and explains the change, keeping map, list and labels synchronised. Closing the panel or hiding outlines still preserves the selection. “Show all Scarborough” controls the camera, not the filters.

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
- Maintain regression coverage for DineSafe missing-address placeholders, inspection-detail labels and source-versus-publication freshness; check `CURRENT_STATE.md` before treating older defects as unresolved.
- Confirm runner availability and proper isolation on the physical GMKtec before activating proposed infrastructure workflows.

