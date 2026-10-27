# CSI public-projection candidate

Status: synthetic implementation only. Public export remains disabled.

The candidate accepts only the ArcGIS grouped-statistics response envelope
(`features[].attributes`) keyed by the source `HOOD_158` code and one of the
five qualified CSI categories. It checks
that grouped counts reconcile to before/after count controls and that source
metadata remains stable. It does not accept or download raw incident rows.
The validator accepts only recognized ArcGIS response metadata, requires the
expected aggregate field schema and WGS84 reference, and rejects geometry or
record identifiers. Both count controls and the grouped query carry the same
Toronto-quarter half-open `REPORT_DATE` interval; the displayed quarter is
derived from those DST-aware UTC bounds. Duplicate groups (including NSA)
fail closed before unassigned rows are excluded, and returned group counts
must be positive. A zero total is valid only for an empty response with
matching zero controls.
The supplied synthetic registry maps padded source codes to separate display
names; codes are validated by registry membership rather than a numeric
range. Counts from zero through four are represented only by `0-4`; counts of
five or more remain exact. The projection contains no marginal totals,
rankings, overlapping time grains, event dates, row identifiers, offence text,
coordinates, addresses, or joins. It records source identity, published
coverage, source edit time, and retrieval time, with a qualitative note that
some records may be unassigned; it does not disclose an exact unassigned
total. The candidate includes the required Ontario Open Government Licence
attribution text.

This is a candidate direct-republication boundary, not a legal minimum or an
anonymity guarantee. The caller-supplied synthetic registry is not accepted as
proof that the complete official `HOOD_158` crosswalk has been qualified.
Every result is marked disabled, and the existing public exporter continues
to raise `PublicExportDisabled`. No real CSI feature rows or grouped result
payloads were downloaded for this work.

Before any future activation, verify the complete authoritative neighborhood
registry, apply it to the full source aggregate, inspect category/cell utility,
and review differencing across repeated releases. A missing aggregate cell is
shown as zero only after the complete validated grouped response and registry
are supplied; an unassigned source record is never converted to a named cell.


