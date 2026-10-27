# Toronto permits and development application prototype

This worktree is a synthetic-only, offline source-contract prototype. No CKAN
network client, large CSV download, geocoder, CRS converter, schedule, or public
export is included. ScarbTO public export remains disabled.

## Researched source packages

The future CKAN transport uses the Toronto CKAN API base
`https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/` and
`datastore_search` with explicit field allowlists, bounded pages, stable
`_id ASC`, and source-generation/count checks before and after pagination.
SQL search returned 404 in source qualification and is not used. Large CSVs
must be streamed with strict limits; the existing whole-file/read-all path is
not suitable. Observed row counts/resource sizes are not fixed expectations.

| Dataset | Datastore ID | Resource ID | Qualified scope |
| --- | --- | --- | --- |
| Active building permits | `6d0229af-bc54-46de-9c2b-26759b01dd05` | `dfce3b7b-4f17-4a9d-9155-5e390a5ffa97` | Active collection |
| Cleared permits since 2017 | `a96c0ba4-3026-402b-b09d-5b1268b8f810` | `b41c3e9e-4d2d-4b09-a789-9569d8da407c` | Legacy 2000-2016 omitted |
| Development applications | `8907d8ed-c515-4ce9-b674-9f8c6eefcf0d` | `77f8a66a-bd43-40e6-b6c9-12a2b03a5032` | Address rows, not unique applications |
| Toronto One Address Repository | `0b3756af-9caf-4f0f-ac28-9c6617adede4` | `64d4e54b-738f-4cd9-a9e7-8050fac8a52f` | Explicit EPSG:4326 CSV only |

The catalogue shows the Toronto Open Data Licence, while CKAN licence fields
were observed as unspecified. Preserve this discrepancy and attribution. The
City warns of intermittent CKAN outages. Refresh metadata does not state a
timezone. A failed or mixed-generation refresh must leave the prior validated
snapshot intact.

## Record and geography rules

Permit identity is the full `PERMIT_NUM` including its type suffix plus the
string `REVISION_NUM` (preserve `00`), independent of whether the same row
appears in active or cleared collections. An identical overlap is deduplicated;
conflicting values for the same identity are quarantined. Active and cleared
source collection and raw status are preserved. Application, issuance, and
completion dates remain separate.
No status, cleared-source membership, disappearance, or completion date alone
is converted to a claim that construction occurred. Conflicting active/cleared
or same-key records are quarantined.

For permit coordinates, `GEO_ID` joins to OAR `ADDRESS_POINT_ID`, never
`ADDRESS_ID`. Synthetic regression data covers permit 22 236652 BLD revision
00 at 4003 Ellesmere Rd: GEO_ID 331669 maps to ADDRESS_POINT_ID 331669 and
ADDRESS_ID 357094. Using ADDRESS_ID instead would map to a different address.
The bounded live CKAN metadata check declares permit `GEO_ID` as text, so the
adapter accepts only ASCII decimal text or an integer and normalizes it to an
integer point ID. A bounded live OAR lookup confirmed
`ADDRESS_POINT_ID=331669`, `ADDRESS_ID=357094`, `WARD=25`,
`ADDRESS_FULL=4003 Ellesmere Rd`. A filtered development query for folder
4970049 returned six rows over two pages (IDs 230-235), with stable metadata
and matching before/after totals. It identifies application `21 191603 ESC 20
SA` and six address rows at 1552, 1572, 1554, 1562, 1564, and 1570 Kingston
Road. This proves only this bounded filtered query, not a full import or
general refresh completeness. No transformation of planning X/Y values is
attempted. Those fields are NAD27
MTM10 and require independently validated coordinate conversion; this
prototype avoids them. OAR points must have already-qualified WGS84 fields
before they can be passed to the normalizer. Ward values are restricted to
current Scarborough wards 20-25; a ward-grid code such as E2532 is not a ward
number. Polygon boundary validation is still required before map activation.

The transport must map source fields explicitly before normalization: OAR
`WARD` to normalized `WARD_NUMBER`, `ADDRESS_FULL` to `address`, and coordinates
from the explicitly EPSG:4326 OAR resource to `longitude`/`latitude`. This
bounded check did not fetch those coordinates or qualify permit/development
live rows. The current CKAN OAR `geometry` field was not treated as WGS84.

Development address rows are grouped by source-prefixed FOLDERRSN with an
application-number consistency check; a missing folder uses an explicitly
marked application-number fallback. All qualified address locations are
retained and fingerprinted independent of input order. Example synthetic
contract coverage includes folder 4970049/application 21 191603 ESC 20 SA at
1552 and 1572 Kingston Rd. Those are two locations for one application. Other
development coordinates remain unused unless separately qualified by exact
address joining. Application status is an internal planning-review state:
Under Review, Appeal Received, NOAC Issued, and Closed do not mean construction
approval.

The normalizers intentionally exclude builder names, contact details, and
unreviewed free text. They validate official links against Toronto HTTPS hosts.
Development applications with no record URL use the City application-information
page as a general fallback; permits without a record URL expose no link rather
than implying that a planning page is a permit detail. The development adapter
accepts source `STREET_*` address components as well as already-normalized
addresses. Permit source addresses, when present, must agree with the joined OAR
address. OAR coordinates are checked against a broad Toronto-area sanity
envelope; this is not ward polygon validation. They do not expose raw
source rows, contact fields, X/Y, or guessed construction states. They mark
publication disabled. The first import must be labelled recent applications or
issuances, never newly observed changes: no delta/tombstone contract has been
verified. Absence from a replacement snapshot means only absent from that
snapshot.

Official catalogue terms: [Toronto Open Data Licence](https://open.toronto.ca/open-data-licence/).
Bounded live qualification confirmed OAR point 331669 and a filtered planning
query for folder 4970049. A six-row filtered completeness check returned IDs
230-235 across two pages with matching totals and unchanged metadata; the source
application number is `21 191603 ESC 20 SA`, with six address rows. This is a
small filtered check only, not a full import. No large CSV or bulk snapshot was
downloaded.

## Tests and activation gates

Run `python -m unittest discover -s tests -v`. Tests use invented fixture
records and no production/private data. Before live integration, recheck
package/resource metadata and complete pagination, validate source field
mapping, generation stability, CRS/geography against known points and current
ward/neighbourhood polygons, refresh-failure rollback, and the public allowlist
with a privacy/source-rights review. Qualify full-scale memory and runtime
before any large ingest; do not run concurrent heavy imports. Public export
remains disabled until those gates pass.

