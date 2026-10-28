# Phase 1B CSI adapter prototype

This directory remains a synthetic-only research prototype. It is not wired
into ScarbTO's application, production data, scheduled workflow, site or DNS.
The publisher remains disabled for CSI. Fixtures contain fabricated records
and public metadata only.

The row adapter validates the version-bound paginated source contract. It
requires both the source identifier `HOOD_158` and the separate display label
`NEIGHBOURHOOD_158`; their association must match a supplied registry. The
source identifier is a padded string and must be validated by membership in a
versioned registry, not by assuming codes form a consecutive numeric range.
The synthetic fixture uses fictional mappings; it is not the official
registry.

The public-projection candidate does not consume row snapshots. It accepts an
ArcGIS grouped-statistics response envelope with `features[].attributes` keyed
by `HOOD_158` and `CSI_CATEGORY`,
checks stable source metadata and before/after count controls, and requires
the group sum to reconcile. NSA remains unassigned and contributes only to a
qualitative note. It produces a fixed category grid for a complete Toronto
report quarter, bands zero through four as `0-4`, preserves counts of five or
more, and rejects unknown groups or extra schema fields. The recursively
allowlisted candidate contains required Ontario Open Government Licence
attribution, but is still marked disabled. It exposes no marginal totals,
rankings, individual rows, event dates, offence text, coordinates, addresses,
or joins.

The grouped response validator permits only the known ArcGIS response headers
and validates the returned statistic field names/types, empty identifier
fields, null geometry type, and WGS84 spatial reference. It rejects geometry
on group features. The same half-open `REPORT_DATE` interval is recorded for
the before-count, statistics, and after-count queries; the displayed quarter
is derived from that interval using Toronto's timezone, including DST-aware
UTC boundaries. Duplicate groups are rejected before NSA is excluded, and
returned groups must have positive counts; a genuinely empty response is
valid only when both count controls agree at zero.

Quarter completeness uses inclusive Toronto calendar dates in published
extract metadata, not observed row-date minima/maxima. The report-quarter
adapter's row aggregation remains an internal synthetic validation path; it
is not used as the public-projection input.

## Source and privacy limits

TPS describes this as historical and preliminary offence/victim/vehicle-level
data. Repeated event IDs can be legitimate related rows, and a source-row
count is not a unique incident or person count. NSA represents unassigned
neighbourhood data. Source locations are deliberately offset. Do not join to
premises or addresses, reverse-geocode, publish individual locations, rank
neighbourhood safety, or imply live dispatch.

The candidate's `0-4` band is a conservative direct-republication choice for
this prototype, not a legal minimum or an anonymity guarantee. The complete
City HOOD_158 registry and a separately documented 30-neighbourhood
majority-area Scarborough overlay are now included in the hash-pinned
`fixtures/official-source-contract` artifact. Join by the exact three-digit
`AREA_SHORT_CODE`; preserve source code and publisher display name separately.
The overlay is not a publisher-supplied membership field and does not prorate
neighbourhood counts. Projection groups are reconciled across Toronto, then
only selected whole-neighbourhood cells are emitted. The registry does not
qualify a full recurring source refresh, public map integration, or public
release. No public CSI output has been enabled.

The candidate carries this attribution wording:

> Contains information licensed under the Open Government Licence - Ontario.

Official references remain in the source metadata and privacy proposal. The
contract records Toronto Social Planning Neighbourhoods v3.0 (effective
2022-04-12), source resource identity and hashes, the crosswalk method, and its
spatial validation. Keep the documented selection distinction visible in any
future output; do not treat the overlay as an official Scarborough
administrative boundary. Recheck applicable terms and item restrictions
before any future activation.

## Tests

Run the standard-library synthetic suite with:

```powershell
python -m unittest discover -s tests -v
```

Coverage includes code/name separation, the hash-pinned 158-area registry,
the selected 30-code overlay, nonconsecutive registry identifiers, mixed
assigned/NSA groups, count controls and source-version stability, quarter
coverage, the 4/5 band boundary, unknown/duplicate group rejection, and
recursive output-key allowlisting. No network access is used.

