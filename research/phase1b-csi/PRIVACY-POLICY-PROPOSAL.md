# Phase 1B CSI privacy policy proposal

**Status: proposed for review; not adopted. Public export remains disabled.**

## Proposed output boundary

- Only aggregate data by Toronto neighbourhood, CSI category, and a coarse
  occurrence/reporting period. The period definition and resolution need an
  explicit product/privacy decision; the prototype's Toronto-local month is
  internal test behavior, not an approved public resolution.
- Exclude event IDs, `OBJECTID`, offence text, exact dates, addresses, and
  coordinates. Do not create point maps or present the source's offset
  locations as a specific intersection or place.
- Do not link or join CSI records to DineSafe, premises, addresses, people,
  businesses, organisations, or other datasets; do not reverse-geocode.
- Label the source as historical/preliminary, distinguish occurrence date
  from report date, and do not imply live dispatch, verified completeness, or
  an exact count for a neighbourhood. Do not rank neighbourhood safety.
- Include TPS attribution and a link to the applicable licence. The TPS portal
  currently identifies the Open Government Licence - Ontario v1.1. Recheck
  the licence and item restrictions at activation.

The prototype's disabled internal candidate currently records a date range
for diagnostics. That is not part of the proposed public schema; remove or
generalise those exact bounds before implementing any public projection.

## Sparse-cell handling choices for review

No suppression threshold is selected. Options include suppressing cells below
a policy-set threshold, combining months into quarters or years, combining
categories, grouping neighbourhoods into a coarser geography, or withholding
the layer until the remaining cells are adequate. The owner/privacy reviewer
must choose a policy before public export is enabled.

Suppression must account for differencing between overlapping totals and
repeated releases, not just a per-cell minimum. Coarsening geography can be
misleading because TPS deliberately offsets locations and warns that
neighbourhood counts may not match the actual geography. Coarsening categories
can hide different source meanings. A threshold by itself is not a complete
privacy guarantee.

## Known source limitations

TPS describes rows as offence and/or victim level, so one occurrence may
produce multiple rows and appear in multiple categories. Keep source-row
counts separate from distinct occurrence identifiers. Dates are UTC in source
metadata; convert deliberately for Toronto display. The source is preliminary,
excludes occurrences deemed unfounded, and makes no accuracy, completeness, or
timeliness guarantee. Do not compare its values with other crime datasets as
though they were directly equivalent.

## Approval needed before activation

Review source terms, the exact public aggregation grain, suppression and
differencing behavior, attribution wording, caveats, and whether the product
should show the layer at all. Until that decision is recorded, only synthetic
fixtures and internal aggregate candidates may be used.

