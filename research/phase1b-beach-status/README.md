# Phase 1B source adapter prototypes

This directory is a research prototype. It is not wired into the ScarbTO
application, production site, workflow, or DNS. Its bounded beach-history
client can read one fixed public Toronto CKAN resource, but has no scheduler
or public publisher. All proposed public-output policy remains unapproved.

`fixtures/rows.synthetic.json` contains only fabricated records.
`fixtures/layer-metadata.checked.json` records public layer metadata only,
checked 2026-10-27; no Toronto Police feature rows were retrieved. No source
records or locations are included. `BEACH-SOURCE-CONTRACT.md` describes the
separate synthetic-only beach-status prototype and its source-rights gate.

## Implemented contract

- Accept only the researched layer identity `CSI_OPEN_DATA`, layer 0, and the
  current `CSI_CATEGORY` schema; compare every row's exact field set and its
  field-name signature with source metadata before accepting rows. Validate
  metadata types for the selected fields and validate their non-null row values.
  The official metadata confirms `REPORT_YEAR` is a string, so the copied
  synthetic records were corrected from integer years to strings.
- Require a stable service item, edit timestamp, layer/schema metadata, record
  limit, coverage interval, and count across the before/after pagination
  metadata. Query time is recorded but may naturally differ.
- Require contiguous pages from offset zero, honor the current source
  `maxRecordCount`, reject duplicate snapshot-local `OBJECTID`s, detect short,
  incomplete, extra, or transfer-limited pages, require `OBJECTID ASC` on every
  page, enforce strictly ascending IDs, and match the expected total.
  `OBJECTID` is used only for snapshot pagination integrity, never as a durable
  record or aggregate key.
- Parse `REPORT_DATE` and `OCC_DATE` only with explicit UTC information (or
  ArcGIS epoch milliseconds). Check report dates against source coverage and
  use `America/Toronto` when assigning occurrence months.
- Keep offence/source-row counts distinct from distinct occurrence IDs. A
  repeated `EVENT_UNIQUE_ID` may be a legitimate related row and an occurrence
  can contribute to multiple category cells.
- Produce only an internal candidate grouped by neighbourhood, category and
  Toronto occurrence month. It contains no event IDs, `OBJECTID`, offence text,
  coordinates, address, or premises join. It is marked
  `disabled_pending_privacy_review`.
- Public export always raises `PublicExportDisabled`. No sparse-cell threshold
  is invented. Public use remains blocked until a privacy policy and source
  terms are requalified.
- Atomic private candidate writes preserve a prior candidate if replacement
  fails. This is not a live-site snapshot or deployment mechanism.

The candidate retains a reference to TPS terms; the Ontario Open Government
Licence 1.1 and TPS item restrictions both need to be rechecked before any
future activation.

## Current official metadata and licence check

Checked 2026-10-27 using the layer metadata endpoint only. It reports service
item `0a239a5563a344a3bbf8452504ed8d68`, layer 0 `CSI_OPEN_DATA`,
`maxRecordCount: 2000`, pagination and order-by support, UTC date-field
reference (`Etc/UTC`), and layer last edit `2026-10-08T13:23:11.683Z`. For the
fields represented by the synthetic query fixture: `OBJECTID` is OID;
`EVENT_UNIQUE_ID`, `REPORT_YEAR`, `REPORT_MONTH`, `CSI_CATEGORY`, `OFFENCE`,
and `NEIGHBOURHOOD_158` are strings; `REPORT_DATE` and `OCC_DATE` are dates;
`LONG_WGS84` and `LAT_WGS84` are doubles. This metadata does not validate an
actual paged read or row count.

The TPS portal licence page identifies Open Government Licence - Ontario
version 1.1 and says source attribution is required. The layer description
also says occurrences are preliminary, locations are deliberately offset,
and the counts may not exactly reflect neighbourhoods. TPS's licence page
includes a restriction against linking the information with other databases
to attempt to identify an individual. The project-wide no-join/no-geocoding
boundary below is deliberately stricter and is a privacy safeguard, not a
claim that every part of it is quoted from that single licence clause.

Official references: [TPS layer metadata](https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services/Major_Crime_Indicators_Open_Data/FeatureServer/0?f=pjson), [TPS licence page](https://data.tps.ca/pages/licence), and [Ontario Open Government Licence](https://www.ontario.ca/page/open-government-licence-ontario). The Ontario page was blocked by the browser fetch during this check; TPS's own licence page is the source for the v1.1 and attribution findings. No feature/query endpoint was called.

The concise privacy-policy proposal, including suppression options and
limitations, is kept in [PRIVACY-POLICY-PROPOSAL.md](PRIVACY-POLICY-PROPOSAL.md).
It is not approved; public export remains disabled.

## Run tests

```powershell
python -m unittest discover -s tests -v
node .\tests\beach-status-view.test.mjs
```

The suite uses only Python standard-library modules and the synthetic fixture.
It does not download or publish anything.

## Activation gates

Before any real-data adapter or public output is considered: recheck the TPS
source metadata (including full field types/date encodings), license and item
restrictions; prove a real paged read is complete and version-stable;
independently review aggregation semantics and a
privacy suppression/generalisation policy; keep raw CSI rows and locations out
of the public map; and obtain a separate product/release review for adding the
feed. This prototype does not decide those gates or claim that the actual feed
was tested.

## Beach status prototype

`beach_status_adapter.py` accepts synthetic fixtures matching the Toronto
operational beach-status contract. It uses official status flags rather than
numeric E. coli values, joins only on beach ID, hides old results out of
season, preserves date-only collection dates and the timezone-unspecified
source update string, and keeps public export disabled. The DOM view uses
`textContent` and links to the official Toronto beach page. It does not fetch
data or claim live conditions. `beach_measurement_history.py` separately
validates complete, exact-total CKAN history pages and can write a
content-addressed candidate with atomic manifest promotion. Its companion
history view renders dated catalogue measurements with no safety inference.
The bounded live query only verified one page; no complete snapshot or app
integration exists yet. The client and tests are bounded and use synthetic
responses offline. See [BEACH-SOURCE-CONTRACT.md](BEACH-SOURCE-CONTRACT.md)
for source evidence, rights discrepancy, and remaining activation gates.

