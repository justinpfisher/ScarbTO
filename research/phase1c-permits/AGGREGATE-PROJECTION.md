# P4 offline aggregate projection

`permit_aggregate.build_projection(receipt)` is a pure, standard-library builder.
It accepts only an already verified collision aggregate receipt, not source rows
or a normalized record export. It performs no I/O, ingestion, fetch, refresh,
publication or job dispatch. The existing `export_public` guard is unchanged.
Dot retains release and project coordination.

## Input and validation

The receipt must have status
`complete_stable_generation_identity_collision_accounting`, top-level `utcEnded`,
and an object `perSource` containing exactly `active` and `cleared_since_2017`.
Each source requires:

- `generation.marker`: one or two valid ISO calendar timestamps joined by `|`,
  matching the existing collector's CKAN generation representation. Each part
  requires seconds and may have up to six fractional digits. Preserve the exact
  supplied string; timezone-unspecified City metadata is never assigned UTC.
- `rows`: positive integer full-source row count, not a row array.
- `counts.inside_coverage`: nonnegative integer no greater than `rows`.
- `reconciledDisposition.insideNonCollidingRows`,
  `insideCollisionRowsQuarantine`, and `insideInvalidIdentityRowsQuarantine`:
  nonnegative integers whose sum equals `inside_coverage`. Booleans, floats,
  strings, missing values and inconsistent totals fail closed.

`utcEnded` must be a valid ISO timestamp with seconds, `T`, and explicit `Z` or
`+00:00`. Local offsets, naive times and unknown-offset `-00:00` are rejected,
not converted or relabelled. This validates UTC representation; authenticity
of the original check and upstream geographic/collision verification remain
prerequisites supplied by the caller, not facts this builder can independently
prove. It does not use the machine clock or invent check times.

## Output and evidence limits

The output contains only schema version, fixed six-ward footprint/provenance,
two ordered source summaries, fixed licence URL and exact Toronto attribution.
The footprint uses validated address points within wards 20–25 and qualifying
Scarborough neighbourhood polygons. Rows without a verified in-footprint address
match are excluded. Quarantine counts include collision and invalid-identity rows.
URLs, method and
coverage notes are constants, never copied from input prose. Extra receipt
fields are ignored; extra collections are rejected. No IDs, raw rows, names,
addresses, coordinates, projected locations or individual details are emitted.
Counts describe source rows, not unique permits, construction or longitudinal
identity. Cleared scope excludes the legacy 2000–2016 collection.

Focused tests reproduce the requester-supplied in-footprint evidence:

| Collection | Inside | Noncolliding | Collision quarantine | Invalid identity |
| --- | ---: | ---: | ---: | ---: |
| active | 22720 | 22279 | 441 | 0 |
| cleared_since_2017 | 47415 | 46233 | 1182 | 0 |

Fixture generation/check times and full-source totals are synthetic controls.
No original receipt file was supplied in this checkout; tests do not certify a
new live receipt, capture or source check. Counts are regression evidence, not
hardcoded acceptance totals for all future verified receipts.

Run the existing unittest entry point from `research/phase1c-permits`:

```sh
python -m unittest discover -s tests -p 'test_permit_aggregate.py' -v
```

The existing research test discovery also includes this test module without
workflow changes. No public data artifact is generated or staged.
