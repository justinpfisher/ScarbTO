# Toronto beach status adapter prototype

This worktree is an offline, synthetic-only prototype. It is not connected to
the ScarbTO application, public site, scheduled workflow, or a live source
client. Public export remains disabled. The source contract is the Toronto
operational beach-status API used by the City's SwimSafe page; raw CKAN
sampling data is not used to assign a health status.

## Source contract

The future transport may query the City endpoints on `secure.toronto.ca`:

- `/opendata/adv/beach_list/v1?format=json`
- `/opendata/adv/in_season/v1?format=json`
- `/opendata/adv/last_update/v1?format=json`
- `/opendata/ss/maint_beach/v1?format=json`
- `/opendata/adv/beach_results/v1?format=json&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&beachId=10`

A result envelope has a date-only `CollectionDate` and `data` array or null.
Rows carry `beachId`, `beachName`, `eColi`, `advisory`, `statusFlag`,
and nullable `statusFlagPre`. The adapter joins only by integer `beachId`,
selects the latest collection date, and rejects duplicate rows/envelopes for
that date. Names are descriptive only. The preliminary status overrides the
ordinary status when non-null. Recognized labels map as follows:

| City status code | Official City label | Internal display value |
| --- | --- | --- |
| `SAFE` | Safe to swim | safe |
| `UNSAFE` | Caution is advised | caution |
| `NO_DATA` | Data unavailable | unavailable |
| Any other or missing code | unavailable; no quality label is inferred |

The numeric E. coli measurement is deliberately ignored. A low number does not
override an official caution, and a missing result never means safe.

## Bounded live schema check (2026-10-27)

Five unauthenticated requests were made to public City controls plus one
seven-day result query for beach ID 10; each response was capped at 1 MiB with
a 10-second timeout. The controls returned a 10-beach list, beach 10 as
Bluffer's Beach Park, `inSeason: No`, `lastUpdate: 2026-09-09 10:19:11`, and
`maintEnabled: N`. The seven-day result response was JSON null. A separate
four-day historical query returned two envelopes, dated 2026-09-07 and
2026-09-06, with the expected six row keys. The observed status code was
`SAFE`, not the human-readable label; the official City UI maps `SAFE` to
"Safe to swim", `UNSAFE` to "Caution is advised", and `NO_DATA` to "Data
unavailable". The adapter now maps those exact codes. No measurements,
coordinates, or source rows were saved or published. This confirms endpoint
shape and mapping only; it does not establish current conditions, refresh
reliability, complete source rights, or a safe-to-swim claim.

The [City's SwimSafe terms](https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/swimsafe-terms-of-use/)
say results are usually posted 24-36 hours after inspection, disclaim accuracy,
completeness, and currency guarantees, and say the webpages are not a guarantee
of facility conditions. The terms page contains no express data reuse grant.
Catalogue licensing for related data and these operational-page terms are
distinct; the rights check should resolve that specific reuse question before
public redistribution rather than treating the CKAN metadata discrepancy as
proof of a prohibition.

The display precedence is separately verified access closure, out-of-season,
unknown season, maintenance, unknown maintenance, missing result, freshness
qualification, then City status. A closure must come from a separately
verified authority; Toronto's beach list does not include Rouge, and the
prototype does not guess a Rouge identifier or merge Parks Canada records.
Out-of-season status hides last season's result. The date-only collection date
is preserved and its age is compared by Toronto calendar date. The raw
`lastUpdate` text is retained exactly; because the observed value has no
timezone, the adapter does not append UTC or use it to claim freshness.
Fetch time is separate from evaluation time and is a UTC timestamp captured
when the result and each control are retrieved. Re-evaluating a cached result
must not advance any retrieval timestamp. Preserve raw `statusFlag` and
`statusFlagPre`; the latter is the displayed source when non-null. Missing
maintenance state is unknown, never assumed to be `N`. The view shows sample,
source-update, and snapshot-retrieval dates separately. The endpoint paths
above include the required `/opendata/adv/` prefix.

A two-day sample-age limit is only a proposed application setting, not a City
service-level guarantee or a health threshold. Query-window, timeout, byte
limit, retry, schedule, source freshness, and last-good snapshot behavior must
be qualified in the future transport before activation. A valid current null
or out-of-season response must remove an old green status. A transport failure
must not erase history or the last-good validated snapshot.

## Rights and scope

Toronto's catalogue displays the Toronto Open Data Licence, while CKAN's
licence metadata for the related historical sampling dataset was observed as
unspecified. Preserve that discrepancy and attribution; it is not resolved by
this prototype. No CKAN sample rows are copied here. The operational status
is sourced from the public Toronto SwimSafe API/page. The specific SwimSafe
Terms of Use describe this as public information and disclaim accuracy,
completeness, and currency guarantees, but contain no express data reuse grant.
The catalogue's licence listing for related data does not automatically prove
that it applies to the operational API. Until a matching catalogue dataset or
explicit City permission establishes redistribution rights for this feed,
public export remains disabled. This is a specific rights question, not an
assumption that the disclaimer prohibits reuse.

The view component uses text nodes for status/advisory content and links to
the official Toronto beach-water-quality page. It does not render coordinates
or E. coli values. Public export is disabled in `beach_status_adapter.py`.

Official references:

- [Toronto beach-water-quality page](https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/beach-water-quality/)
- [Toronto SwimSafe terms](https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/swimsafe-terms-of-use/)
- [Toronto Open Data Licence](https://open.toronto.ca/open-data-licence/)
- [Toronto operational UI source](https://www.toronto.ca/resources/tph_beaches/scripts/main0.0.0.js)
- [Parks Canada Rouge beach status](https://parks.canada.ca/pn-np/on/rouge/visit/infrastructure/plage-beach)

## Run tests

```powershell
python -m unittest discover -s tests -v
node .\tests\beach-status-view.test.mjs
```

All inputs are synthetic. The tests do not call the City API, process personal
data, deploy, or publish.

## Activation gates

Before integrating a live feed, resolve the specific operational-feed
redistribution basis; implement a bounded transport with control-first
validation, one in-flight request, timeouts and byte limits; verify source
response schemas and Toronto date handling; and implement atomic validated
last-good retention. Agree the app freshness policy and any separate closure
source before showing current labels. Keep public export disabled until these
gates pass. This prototype does not claim current beach conditions or actual
source availability.

