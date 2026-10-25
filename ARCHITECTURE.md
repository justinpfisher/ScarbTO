# Scarb.TO decision record — 24 October 2026

## Non-negotiables carried forward

Scarb.TO is a **Scarborough-first living local atlas**: a large interactive map on the first screen, a synchronised record list, a curated view of recently changed official information, date/outcome/neighbourhood controls, mobile-first operation and source/date disclosures. The UI should be distinctive but credible. Revenue is secondary; sponsors never control map ranking or safety-related results. Start with no outreach, no paid services and no unnecessary account systems. Bootstrap within **C$25/month** and **2–4 hours of maintenance per week**.

Build afresh while preserving `scarb.to`. The public website should only be cut over after a working, real-data staging deployment with a rollback path.

## Stage 0: PoC — one complete source-to-map path

- Official feed: Toronto Public Health's DineSafe **open-data** CSV; do not scrape the City's interactive lookup. Discover resources using CKAN `package_show`; verify resource and current schema live before launch.
- Scarborough boundary: union of the six official Scarborough city wards, not an arbitrary longitude cutoff or postal-code approximation. Toronto's 158-neighbourhood geometry enables neighbourhood selection.
- Data: for each establishment, stable identifier, name, address, type, coordinates, neighbourhood/ward, latest recorded inspection date, latest recorded outcome. Avoid mixing inspection dates with publication/detection dates.
- Pipeline: download and validate, normalise, compare with last successful snapshot, generate current snapshot + optional observations, commit validated files, publish a static website. Hold exceptions without replacing live good data. Show staleness and provide a public workflow history link.
- Website: GitHub Pages + MapLibre and OpenFreeMap, no runtime database. Scheduled **public-repository standard GitHub Action** may provide one small reliable hosted job daily; GMKtec remains the preferred normal development computer. This avoids the user's private-repository minute cap issue and does not require the home computer to remain online.
- Initial site: inspections map, recent-versus-all view, date/outcome/neighbourhood filtering, synchronised records, provenance, CSV export, responsible disclaimer and local-only saved filters. No contributions or accounts yet.
- Target incremental service cost: **C$0/month**, excluding already-owned domain. Provider availability/billing must be verified at launch.

## What "new" means

1. **Inspected at**: date of a visit, as reported by the City (can predate publication).
2. **Source refreshed at**: City's metadata when available, not independently verified by our collector.
3. **Detected at**: first Scarb.TO ingestion where a change was observed (may lag inspection by days).
4. **Published at**: successful validation/release timestamp.

Only show "recent change" labels for events observed across successive qualified snapshots. On first import, show **recently inspected**, not "just changed".

## Expansion path — one source at a time

| Stage | New feed/ability | Operational rule |
| --- | --- | --- |
| PoC | DineSafe | Real daily importer, geographically correct map, source-linked records, zero false live claims. |
| Phase 1B | Toronto Police historical/updated incidents | Confirm exact public dataset, its update cadence, spatial anonymisation and legal terms; avoid real-time police/dispatch labels and false address precision. |
| Phase 1C | Building and development permits | Confirm whether source covers new/active/cleared permits and which dates correspond to issuance, activity or permit status; avoid implying construction is occurring. |
| Phase 1D, seasonal | Beach water quality | Show sample timestamps, relevant seasonal status and gaps; keep absent/off-season sources explicitly unavailable, not "safe". |
| Phase 2 | Municipal, provincial, federal election candidate links | Per jurisdiction/election, record boundaries, candidacy verification and election date; official sources first, no editorial ranking. |
| After MVP | Corrections and missing-information submissions | Limited, source-linked, moderated-as-needed; no public write access to official records. |
| Later | Saved alerts, follows, contributions, sponsors | Add only after evidence of return use. Begin with browser-saved preferences; accounts only if cross-device persistence is truly needed. |

## Reusable data without early platform complexity

Each future adapter should produce a stable source ID and publication metadata, location geometry or neighbourhood reference, occurred/recorded date, detected date, status/type and citation. Keep source-specific uncertainty. A lightweight common event shape is more valuable than a universal taxonomy or data warehouse in the PoC.

The existing DineSafe JSON/CSV export is report-ready at the current-record level. For future recurring **neighbourhood briefs** or licensed aggregate reports, add a small append-only change history with `source_id`, `observed_at`, `valid_at`, `place_id`, change type and source link, then build on-demand filtered CSV/HTML/PDF exports. Newspaper-ready, attribution-rich summaries can be free distribution and marketing; report products should follow demonstrated demand, not dictate the public map.

**Do not** create PostgreSQL, object storage, paid LLM jobs, streaming infrastructure, worker queues, search clusters, data lake or per-user server state until observable limitations justify one of them. Potential triggers: generated data too large for acceptable mobile performance, historical reporting exceeding versioned-file practicality, unreliable host refreshes, or sustained multi-user submissions that cannot be handled safely with flat files.

## Verification/rollback essentials

Test official CSV format, six ward polygons, neighbourhood spatial assignments, regression on historical sample rows, count sanity, status recency, mobile map/list controls, source links and CDN loading. Publish only if all essential checks pass. A failed import must retain live last-good files and clearly expose staleness. Before DNS changes, document existing `scarb.to` records and preview on the GitHub Pages address; after cutover verify production HTTPS and real official data. Revert publication or DNS to the previous known-good state if needed.

## Open questions to resolve by live evidence — not another approval round

- Exact current DineSafe package resource and CSV schema (CKAN not reachable from the Chat runtime).
- Real source refresh cadence today, including time zone and weekends; scheduled daily polling is our choice, not proof of City frequency.
- Existing domain DNS/host configuration and whether a public repository or Pages setup already exists outside the connected installation.
- Whether the `Closed` label in the selected current resource represents an official closed notice versus an outdated historical record; match against the City lookup before launch.
- Production browser/map/CDN/iPhone verification, which requires a browser with network access.
