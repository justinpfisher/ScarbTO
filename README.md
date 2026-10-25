# Scarb.TO — living Scarborough map (PoC implementation starter)

A static, interactive map with a **real City of Toronto DineSafe inspection feed**, synchronised records list, local filters and official-source attribution. No server/database/accounts/paid API keys are required.

## Status and truthfulness

The importer has now been run against the live Toronto CKAN DineSafe CSV (resource refreshed **2026-10-25 08:16 UTC**). The validated snapshot contains **3,289 Scarborough establishments**, selected from 123,627 inspection rows, assigned to one of six Scarborough wards and a neighbourhood (zero unassigned). The City CSV is row-per-inspection and currently uses `estId`, `estName`, `inspectionStatus`, `inspectionDate`, and `typeDesc`; the importer accepts this schema and retains compatibility with the earlier field names. The initial snapshot is a baseline: it reports **zero observed change events**, not zero inspections.

Local offline tests and the live import/independent snapshot validation pass. The public staging site is live at <https://justinpfisher.github.io/ScarbTO/>. Its live page, 3,289-record snapshot and OpenFreeMap style returned HTTPS 200; a desktop browser check showed real map tiles, clustered pins, the synchronized record list, recent-inspection labelling, neighbourhood choices and working name search. No browser console errors were observed. The change-event list is correctly empty for the first baseline. Individual comparisons against the City lookup, iPhone Safari verification and custom-domain cutover remain outstanding.

The public `justinpfisher/ScarbTO` repository is on `main`; GitHub Actions tests and a live refresh/deploy succeeded (run history: <https://github.com/justinpfisher/ScarbTO/actions>). One daily scheduled refresh is configured for 10:17 UTC. A failed validation stops before publication; reverting the data commit restores the previous snapshot and Pages can redeploy it. Hosting and public-repository Actions are configured without paid services (C$0 incremental target). Existing mail records for `scarb.to` were preserved; DNS is on `ns69/ns70.domaincontrol.com` with three Zoho MX records. No domain DNS was changed. A DNS administrator must finish after staging review; retain all existing mail records and add only the GitHub Pages records GitHub specifies for this repository.

The CKAN metadata currently reports “License not specified”; the public dataset page and [City Open Government Licence](https://open.toronto.ca/open-data-licence/) remain linked for attribution and terms review.

## Architecture

- **Collector**: Python 3.12 standard-library script (`scripts/update_dinesafe.py`). On each run, discover the current DineSafe CSV through Toronto Open Data's CKAN metadata API (not historical ZIP); read official City ward and 158-neighbourhood GeoJSON, select six Scarborough wards using spatial containment; select newest recorded inspection per establishment; report exact quality statistics, observe changes across runs, and atomically publish JSON and CSV.
- **Static site**: HTML, CSS and ES modules in `docs/`. MapLibre GL JS 5.24.0 (pinned CDN), OpenFreeMap vector map, responsive map/list, data-source timestamps, staleness warning, accessible controls, browser-only filter preferences. No tracking or accounts.
- **Release**: GitHub Actions (`.github/workflows/refresh-and-publish.yml`) runs offline tests then official importer then independent snapshot check, commits only valid outputs, and deploys to Pages. Failure prevents deployment, and last good snapshot remains live. Git history is rollback; source and inspection timestamps are preserved.
- **Data products**: `docs/data/snapshot.json` current establishment records plus observed changes (up to 365 days); `docs/data/establishments.csv` machine-readable current export; `scarborough-neighbourhoods.geojson` for area narrowing. This is a start of reporting readiness, *not* a complete historical warehouse.

## Local setup

Python 3.11+ and Node 20+ for tests (site only requires a modern browser). No dependencies to install.

```sh
python -m unittest discover -s tests -v
node --check docs/app.mjs && node --test tests/logic.test.mjs
# With Internet access, pull and validate *current* official data:
python scripts/update_dinesafe.py --dry-run
# Publish a validated local copy to docs/data:
python scripts/update_dinesafe.py
python scripts/verify_snapshot.py
# View locally (never file:// for fetch):
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000`. Before first real import the map shows an explicit uninitialised state.

## Publish staging then cut over

1. Create a **public** GitHub repository, ideally `justinpfisher/ScarbTO` (first check it isn't already elsewhere), and copy these files to its `main` branch. Do not place secrets in the repository.
2. GitHub Settings → Pages → Build and deployment → Source: **GitHub Actions**. Allow the workflow to run on main. Confirm its real importer completes before publishing.
3. Inspect the GitHub Pages preview URL on iPhone and desktop: map tiles, clustering, map/list synchronisation, date/outcome/neighbourhood filtering, stale warning, source link, CSV download and accessibility.
4. Only then connect `scarb.to` with its existing DNS provider. Do not disrupt MX or other existing records. Take a record of the previous DNS settings for rollback. Verify HTTPS, canonical domain and production data again.
5. Verify daily refresh and a deliberate failure scenario retaining the previous successful snapshot. For rollback, revert the data commit or re-deploy a known-good GitHub Pages workflow/artifact.

Note: GitHub Actions runs triggered by `GITHUB_TOKEN` pushes do not automatically retrigger other workflows. The combined refresh/deploy workflow deploys in the **same execution** for this reason.

## Accuracy boundaries

- `ESTABLISHMENT_STATUS` is treated as the City data's latest recorded outcome, not a guarantee of current sanitary conditions or permanent business closure.
- An existing baseline is **not** described as recent activity. `status_changed`, `new_inspection` and `first_seen` events begin only after the second successful validated import.
- Detection time is the collector's observation; inspection time is the underlying City's date. These must never be conflated.
- A scheduled daily source refresh is **not** a live sensor or emergency feed.
- Data that fails validation stays unpublished. A stale warning appears when the last successful publication is over 48 hours old. An Actions status link exposes failed runs once the repository is live.
- The City Open Government Licence requires attribution and does not imply City endorsement; OpenStreetMap/OpenFreeMap attribution is rendered by the map.

## Known pre-release verifications for Codex/Work

- Confirm **live** CKAN `package_show?id=dinesafe` metadata structure, current CSV schema and resource choice. Current environment cannot fetch live external URLs.
- Confirm City ward layer returns exactly six Scarborough ward polygons and `outSR=4326` GeoJSON. Run dry-run and compare a handful of source entries against the City's public DineSafe lookup.
- Verify OpenFreeMap style, MapLibre CDN, mobile layout and controls in an actual browser. Add source/schema adaptation and any fixes with tests.
- Confirm Pages deployment, public GitHub Actions schedule, billing hard-stop and domain DNS before any cutover. Minimise provider/service proliferation.

## Sources

- [Toronto DineSafe dataset](https://open.toronto.ca/dataset/dinesafe/)
- [City of Toronto Open Government Licence](https://open.toronto.ca/open-data-licence/)
- [City ward polygons](https://gis.toronto.ca/arcgis/rest/services/cot_geospatial22/FeatureServer/0)
- [Neighbourhood polygons](https://gis.toronto.ca/arcgis/rest/services/cot_geospatial26/FeatureServer/9)
- [OpenFreeMap](https://openfreemap.org/)
- [GitHub Actions public-repository pricing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
