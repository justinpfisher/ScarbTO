# CSI public-projection candidate

Status: synthetic implementation only. Public export remains disabled.

The candidate emits one completed Toronto report quarter as a fixed grid of
the five qualified CSI categories for each supplied, zero-padded `HOOD_158`
code. Counts from zero through four are represented only by `0-4`; counts of
five or more remain exact. The projection contains no marginal totals,
rankings, overlapping time grains, event dates, row identifiers, offence text,
coordinates, addresses, or joins. It records source identity, published
coverage, source edit time, and retrieval time, with a qualitative note that
some records may be unassigned; it does not disclose an exact unassigned
total.

This is a candidate direct-republication boundary, not a legal minimum or an
anonymity guarantee. The code requires a version-bound, paged validated
snapshot. Its caller-supplied synthetic registry is not accepted as proof that
the complete official `HOOD_158` crosswalk has been qualified. Every result is
marked disabled, and the existing public exporter continues to raise
`PublicExportDisabled`. No real CSI feature rows were fetched for this work.

Before any future activation, verify the complete authoritative neighborhood
registry, apply it to the full source aggregate, inspect category/cell utility,
and review differencing across repeated releases. A missing aggregate cell is
shown as zero only after the complete validated source snapshot and registry
are supplied; an unassigned source record is never converted to a named cell.

