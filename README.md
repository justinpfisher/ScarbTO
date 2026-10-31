# Scarb.TO — Scarborough's living neighbourhood map

Scarb.TO collects changing information from authoritative public sources and presents it on an accessible, map-first neighbourhood interface. The first complete source is Toronto DineSafe. Residents should be able to answer **"What's changing near me?"** without consulting multiple City datasets.

**Project links:** [intended public domain](https://scarb.to/) · [GitHub Pages preview](https://justinpfisher.github.io/ScarbTO/) · [Actions and publication runs](https://github.com/justinpfisher/ScarbTO/actions) · [Current verified state and blockers](CURRENT_STATE.md) · [Architecture and roadmap](ARCHITECTURE.md).

## What is implemented

- A real City of Toronto DineSafe CKAN importer with official geographic filtering, count/schema checks, current-record JSON/CSV output, observed change detection and last-good release protection.
- A responsive MapLibre/OpenFreeMap map, synchronised accessible results list, neighbourhood and status filters, inspection-time filtering, official record links, source attribution and local browser preferences.
- Scarborough Community Council display boundary (separate from the six wards used for record inclusion) and a usable list fallback when the map cannot initialise.
- **Optional neighbourhood/City ward overlays** (off by default), with mutually exclusive outlines, a single synchronised DineSafe area filter, accessible selection, Clear area chip, and desktop/mobile region panels. The 30-neighbourhood overlay is a source-verified majority-area selection, not proof that every neighbourhood fits wholly within one ward; the underlying DineSafe six-ward inclusion is unchanged. Official municipal officeholder links are included. Provincial/federal matching awaits separate electoral-boundary qualification.
- An on-demand view of **selected** Toronto Police call counts by Divisions 41, 42 and 43. Counts are not individual call locations, all police activity or a neighbourhood crime map.
- A clearly labelled **historical beach sample preview**, not current swimming advice.
- Research-only permit/development and neighbourhood-statistics adapters. **Their public exports remain disabled** pending real-source, geographic and licensing qualification.

**Verified data checkpoint:** the 31 October 2026 production refresh validated 125,007 source rows and published 3,324 Scarborough establishments; the importer reported 115 retained activity records (not 115 new source events). The [actual public site](https://scarb.to/) and six-ward/30-neighbourhood assets passed the post-deployment live HTTP verification in [Actions run 41240217550](https://github.com/justinpfisher/ScarbTO/actions/runs/41240217550). These counts are not fixed expectations. Inspect [the current snapshot](docs/data/snapshot.json) for subsequent updates and [CURRENT_STATE.md](CURRENT_STATE.md) for release limits.

The public domain is [scarb.to](https://scarb.to/). Its October 31, 2026 production page, area assets and DineSafe snapshot were independently checked over HTTPS after the Pages deployment, while physical-device use has not yet been verified. The [Pages preview](https://justinpfisher.github.io/ScarbTO/) remains a separate verification target. Do not equate future GitHub Actions success with verified live data unless the production smoke step passes.

## Technology and data contracts

- **Collector:** Python standard library, `scripts/update_dinesafe.py`. Discovers the current non-historical DineSafe CSV using Toronto CKAN metadata, applies official six-ward geographic inclusion and 158-neighbourhood assignment, and selects the newest recorded inspection per establishment.
- **Validation:** `scripts/verify_snapshot.py` plus focused Python/JavaScript regression tests. Invalid source/schema, serious data loss and geography errors must fail closed without replacing the previous validated public snapshot.
- **Web:** static HTML/CSS/ES modules in `docs/`; MapLibre GL JS and OpenFreeMap vector tiles, with optional official static geographic assets in `docs/data/` generated from the existing City boundary source and checked at public deployment. No database, account, paid map key, analytics service or production application server.
- **Published data:** `docs/data/snapshot.json` and `docs/data/establishments.csv`. Current snapshots retain observed activity for up to 365 days; longer-term source-linked archives remain planned.
- **Dates:** an inspection's date, an official upstream refresh timestamp, a Scarb.TO collection/publication timestamp and a detected change are different facts. A successful source check is **not** evidence that the City updated its data.
- **Inspection details:** current `typeDesc` values can be infraction/detail text and must not be presented as establishment categories. Placeholder/missing address segments must not be treated as real address components.

**Official sources:** [Toronto DineSafe](https://open.toronto.ca/dataset/dinesafe/), [Toronto Open Government Licence](https://open.toronto.ca/open-data-licence/), [City ward polygons](https://gis.toronto.ca/arcgis/rest/services/cot_geospatial22/FeatureServer/0), and [Toronto neighbourhood polygons](https://gis.toronto.ca/arcgis/rest/services/cot_geospatial26/FeatureServer/9).

## Local development and validation

Requirements: Python 3.11+ and Node 22 for current test tooling. Map viewing requires a browser. GMKtec is the default authorised local execution computer.

```bash
python -m unittest discover -s tests -v
node --check docs/app.mjs
node --test tests/logic.test.mjs tests/list-focus.test.mjs tests/app-render.test.mjs tests/boundary.test.mjs tests/area-selection.test.mjs
python .github/scripts/test_research_prototypes.py
node tests/beach-history.test.mjs

# Official data validation requires outbound access.
python scripts/update_dinesafe.py --dry-run
python scripts/update_dinesafe.py
python scripts/verify_snapshot.py

# Preview the static web application locally.
python -m http.server 8000 --directory docs
```

Rendered Chromium regression checks use the repository's pinned Node dependencies and Playwright browser executable (see the active Actions workflow); run those checks for relevant UI modifications. Use the official source and real map tiles for release verification, not only synthetic fixtures.

## Publication, runner policy and rollback

The current `.github/workflows/refresh-and-publish.yml` runs tests, validates official data, writes only validated output and deploys GitHub Pages. Its configured daily trigger is 10:17 UTC; actual GitHub scheduled execution may be delayed. The last-good published site remains available on failed refresh. GitHub history permits data-file/release rollback.

**Infrastructure transition is incomplete:** as audited on 28 October 2026, both workflow jobs still select `ubuntu-latest`. This conflicts with Scarb.TO's GMKtec-first requirement. [PR #1](https://github.com/justinpfisher/ScarbTO/pull/1) proposes a repository-scoped runner but must **not** be merged until the actual GMKtec runner, labels, security boundary and publication recovery are verified. Essential public data refresh may use a documented limited hosted exception when independent availability justifies it; there must be no fallback for ordinary trusted build/test jobs.

Do not run untrusted fork PR code on a persistent GMKtec runner. Keep minimal GitHub token scopes and protect production history. Do not change DNS, mail records or repository visibility as part of an unrelated code change. Test, merge, deploy and independently verify live; if this cannot be done, report the actual stopping point.

## Priorities and contributor instructions

Read [AGENTS.md](AGENTS.md) for mandatory execution policy and [CURRENT_STATE.md](CURRENT_STATE.md) for the concise current backlog. Preserve the simple architecture, C$25/month incremental spending ceiling and 2–4-hour weekly maintenance objective. Prioritise verified DineSafe correctness and usability before speculative feed expansion; prove additional public feeds one at a time.

