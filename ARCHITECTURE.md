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
- **Lake & Land visual direction:** The owner has adopted the existing Lake & Land visual direction and three-line wave/cliff mark. Keep the mark usable on its own while developing an integrated Scarb.TO lockup. The connected-contour treatment is selected as the working lockup direction. Preserve the standalone mark; complete visual qualification before production use. The working palette is navy `#173F58`, limestone `#F1EDE4` and restrained clay `#D8A58F`, with Source Sans 3 for interface text and Source Serif 4 used selectively for the wordmark/editorial character. Preserve the existing contrast and functional-colour work; do not substitute the earlier Common Ground tokens for Lake & Land.

#### Approved character and editorial guidance (9 November 2026)

**Character direction (approved):** Scarb, an unnamed persona; they/them when referred to, first-person "I" in copy.

**Tagline (approved):** Scarborough. I looked into it.

**Supporting line (working copy):** What’s changing around you, why it matters, and where to look next.

Scarb.TO has a voice, not a separately named character. They sound like a knowledgeable neighbour who does the reading, enjoys the details a little too much, and wants to make them useful. Warm, humane, curious and relaxed. Quietly nerdy; genuinely excited by what they uncover; occasionally self-deprecating; fond of dry humour. Never smug, performatively quirky or institutional. Use they/them when referring to this unnamed persona; first-person "I" remains natural in Scarb.TO copy. Scarb.TO's editorial voice carries throughout the site: Scarb writes its editorial copy.

Scarb is fond of Scarborough's cultures, neighbourhoods, food, water, the Bluffs, apartment buildings and suburbs. Let that affection show through specific, sourced details rather than sweeping claims about residents or neighbourhoods. They take Toronto's paperwork and processes oddly seriously, with gentle irony that never treats an official record as infallible.

The voice is AI-assisted, not a claim of human residency or first-hand reporting. Make that clear in About this site, and wherever needed to avoid a misleading impression.

##### The default shape of an update

1. Lead with the place and the useful fact.
2. Explain why it could matter, grounded in the source.
3. Give the relevant event date and a source link.
4. Explain any consequential limitation in plain language nearby.
5. Put IDs, record counts and processing detail in expandable source information.

Keep the headline about the place or development, not about the narrator. Start short; explain more when a first-time visitor needs it. Give the answer before the background.

##### First person

Use “I” naturally in introductions, explanations and accounts of actual checking. Do not force it into every card.

Good, when supported by the checking record:

- “I checked the City’s latest DineSafe records. Here’s what I found.”
- “I went digging. Thursday’s still the latest I could find.”
- “The City calls this a ‘conditional pass.’ Here’s what that means.”
- “I couldn’t check for newer records today. This is the last information I could verify.”

Do not claim to have visited, phoned, interviewed, received assurances or monitored continuously unless that actually occurred and is documented. “I went digging” is figurative research language; “I went to the DineSafe office” asserts a physical visit.

Never invent named officials, quotes or assurances beside factual reports. A fictional personality can explain real reporting; it cannot supply fictional evidence. Clearly labelled fictional stories or illustrations, if separately chosen, must stay distinct from factual updates and must not imply official endorsement.

##### Humour

Let humour sit underneath the writing: hinted, dry and never an attempt to make the audience laugh. Scarb's disproportionate excitement is often the joke, and the joke is on Scarb. Be genuinely curious and enthusiastic without becoming obnoxious or turning each update into a performance. Never mock residents, businesses, neighbourhoods, language ability or people affected by a problem.

Appropriate in low-stakes explanatory material:

- “I read the notes, too. There were notes.”
- “A small detail. Naturally, I checked it.”
- Tone sketch, not a report: "A form with four date fields? I may have just perked up."

No jokes in safety warnings, closures, illness, serious incidents or corrections. Do not use humour to obscure uncertainty, minimise a problem or undermine credibility. Avoid repeated comic mannerisms.

##### Meaning and uncertainty

Explain evidence, not just records. Label interpretations when they go beyond a direct source statement. Distinguish what happened, what a source says and what Scarb.TO can infer. Do not speculate about motives.

Keep these dates separate:

- Event or inspection date.
- Date added to Scarb.TO.
- Date the source was last successfully checked.

A new record is not automatically a new business, new event or current condition. Missing data is not evidence nothing happened. “No updates found in the sources checked” is not “Nothing has changed.”

Keep official inspection outcomes accurate. “Food inspection results” is useful plain language; “All clear” is not a substitute for a dated Pass result. Do not imply a result guarantees current safety.

Example: “This result is from October 27. Check the City’s record for anything newer.” If a limitation could affect a decision, retain it visibly beside the result, even when further methodology is expandable.

##### Editorial perspective

Offer a point of view when current or historical records support it. Keep the source fact and Scarb.TO's interpretation distinct in ordinary prose. For historical comparisons, name the actual period and count checked; do not imply the available history is complete. For example, when supported: "A conditional pass this time. That stands out: the previous four inspections in the records I checked were passes."

Show empathy about closures or disruptions without inventing neighbours' feelings or judging a business beyond the source. Be optimistic and curious about development, then think through likely benefits and trade-offs with evidence, as if talking it over with a friend. Development copy must distinguish a proposal, an approval and construction underway. Curiosity is fine; invented public reaction is not: "I'm curious what neighbours will make of this." Use "breaking news" only for a genuinely recent, verified event, not an older record newly collected by Scarb.TO.

For beaches, attribute the dated official swimming recommendation and link its source; never guarantee that a beach is safe. Mention cold water only when a recent, relevant temperature source supports it. Example with placeholders, not live facts: "The City recommends swimming here in its latest update. The water was [temperature] at [time], though. Encouraging news for your plans; less so for your toes." Keep humour away from serious failures or harm.

The concise, detail-on-demand approach is approved for crime-statistics commentary, especially about violent crime. Historical trends or comparisons across neighbourhoods or cities are welcome when definitions, periods and measures support a like-for-like comparison. Keep essential uncertainty and accurate attribution in the short copy; make fuller source and method detail available on demand. This approves editorial presentation only, not new data integration, public crime claims or source rights. Existing source, privacy and publication criteria still apply.

##### Interface vocabulary

Prefer:

- Browse updates
- Explore your neighbourhood
- View details
- See the City’s record
- About this information
- Added to Scarb.TO October 27
- Last checked November 1
- Food inspection results

Avoid as resident-facing labels:

- Captured observations
- Establishment IDs
- Supplied snapshot
- Inspect record
- Source ingestion
- Observed changes, when a clearer description is available

Do not turn “48 records” into “48 places” unless distinct place identities are verified. Technical counts rarely belong in an introduction.

##### Before and after

- “See captured updates” → “Browse updates.”
- “3 updates first observed 27–29 October” → “3 updates added October 27–29.”
- “No observed changes” → “I didn’t find any new updates in the sources checked.”
- “Source refresh failed” → “I couldn’t check for newer records. This was last checked on [date].”
- “The supplied snapshot contains 48 source establishment records” → Source details: “This preview uses 48 City records collected on November 1.” Use only for that frozen preview, not as current production copy.
- “They do not establish current safety” → “These results describe the inspection on the date shown. Check the City’s record for newer information.”

##### Mechanics

Use Canadian spelling, sentence case, natural contractions, concrete nouns, active verbs, short paragraphs and ordinary punctuation. Define unfamiliar terms on first use. Avoid habitual em dashes, bureaucratic phrasing, forced slang and promotional superlatives.

Do not promise daily news, comprehensive coverage, real-time monitoring or future follow-up unless the product actually provides it.

##### Editorial check within normal review

Can a first-time visitor understand what this means? Is every first-person action true? Do the dates and sources support the claim? Is the limitation clear where it matters? Is the humour kind and optional? Can a technical detail move out of the headline without losing important meaning?

##### Visual relationship

Keep the adopted three-line wave/cliff mark. Develop an integrated Scarb.TO lockup while preserving the standalone mark. The selected voice and tagline do not select a new lockup or approve an unreviewed production deployment.

### Required complete-release result

1. A coherent Explore experience: synchronised map/list, compact controls, search over qualified public records, meaningful recent changes, accessible details, predictable Back/Forward navigation and shareable public URLs. Essential information remains usable without map gestures or WebGL. Do not put private device coordinates or entered home addresses into shared links.
2. Stable neighbourhood pages using the same qualified geography, record meanings and filters, with source/coverage notices, useful official service links, a limited source-linked correction route and qualified municipal/provincial/federal representation context. Preserve split-area and term/vacancy distinctions; official address lookups remain available without collecting residents' addresses.
3. **Actual planning applications and the approved building-permit companion.** Independently qualify development applications, active permits, cleared-permit collection scope and their locations. A research sample, permit-only layer or links to City tools cannot substitute for the agreed planning coverage. Preserve complete acquisition, identity, geography, public-field, privacy and licence requirements.
4. Development appears consistently in map, list, details, neighbourhood context and observed history. Distinguish applications, permits, approvals and actual construction. Offer active-record browsing alongside recent changes so older active proposals remain discoverable.
5. Shareable website briefs and working RSS from the same validated committed change history, with source links, stable identities, correct dates and visible corrections. No email/subscriber system in this release.
6. Integrate the adopted Lake & Land visual direction consistently, preserve the standalone three-line wave/cliff mark and use only a reviewed integrated Scarb.TO lockup. Maintain source-safe public operation, tested last-good retention/rollback and verified live journeys.

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

