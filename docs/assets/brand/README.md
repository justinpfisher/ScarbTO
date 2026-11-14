# Scarb.TO: Scarborough's Shape — Neighbourhood Mosaic

Owner-selected November 12, 2026. This replaces the Lake & Land visual direction;
it does not change the approved Scarb editorial personality or product scope.
**The approved composition and original variants were independently reviewed. The November 14 white-divider correction has been regenerated and deterministically checked in this isolated candidate; integrated visual qualification, independent review of the corrected assets, and live adoption remain pending.**

## Identity

An accurately proportioned, north-up Scarborough Community Council silhouette,
filled with eight decorative groups of City neighbourhoods, separated by white lines. The wordmark is **Scarb.TO**. The tagline is **Scarborough. I looked
into it.** The owner-selected image is a creative reference, not geometry,
source evidence, a new layout requirement or permission to publish unqualified
development records.

The internal regions are illustrative, not official neighbourhoods, new
administrative districts, data categories or filters. The council outline is a
display boundary, distinct from the six-ward DineSafe inclusion boundary.

## Tokens and usage

| Role | Value | Use |
|---|---|---|
| `--brand-ink` | `#0A3D2A` | Body text, headings, dark surfaces |
| `--brand-forest` | `#0F5132` | Links, secondary text, buttons, focus outlines |
| `--brand-cream` | `#F8F5EA` | Page background, reversed text and dark-surface perimeter |
| `--brand-clay` | `#D2683C` | Decorative accents, never ordinary small text on cream |
| `--brand-sage` | `#7AAE7A` | Decorative areas and non-text surfaces |
| `--brand-meadow` | `#CFE6C2` | Soft surfaces with ink/forest text |

Ink on cream is approximately 11.23:1; forest on cream 8.58:1. Forest and ink
are the default text colours, including captions, helper labels, provenance,
placeholders and footer notes. Do not use low-contrast pale grey/green for
secondary information. Underline inline links. On dark forest/ink surfaces use
cream text and a visible cream focus outline; on light surfaces use forest
focus outlines. A two-colour offset focus ring can span both contexts. Do not
use brand clay as the sole indication of selected, error or warning states.

Brand region colours are not food-safety outcomes. Keep official Pass,
Conditional Pass and Closed labels, explicit text/icons and their tested
semantic colours. Verify actual rendered pairs, hover/focus/disabled states and
map overlays; this palette table is not whole-site WCAG certification.

## Artwork contract

- `scarbto-mark.svg`: primary transparent mosaic symbol.
- `scarbto-mark-dark.svg`: mosaic with a cream perimeter for dark surfaces.
- `scarbto-connected.svg`: horizontal symbol, outlined wordmark and tagline on light backgrounds.
- `scarbto-connected-light.svg`: cream outlined lettering for dark backgrounds.
- `scarbto-mark-mono.svg`: single forest-green silhouette.
- `scarbto-mark-light.svg`: single cream silhouette on dark backgrounds.
- `scarbto-icon.svg`: padded square reduced icon; the same geographic outline,
  without subdivisions that disappear at 16 px. Generate PNG/apple-touch
  derivatives from this asset, not an unrelated drawing.

Keep proportions intact, north up and unrotated. Host layouts must maintain
external clearspace of at least 1/12 of the symbol height around the image;
the SVG's built-in optical margins do not supply that layout spacing.
Never stretch axes independently, crop the
coastline, replace the outline with a traced third-party mark, or use the
decorative groups as application filters. Use the symbol or compact site name
when a full lockup makes the tagline illegible; keep the tagline as visible
HTML where it is not in the lockup. The favicon must remain legible at 16/32 px.

SVG lettering is outlined from **DM Sans**, SIL Open Font License 1.1. The
source font and licence are in `source/`; this avoids remote requests and missing
viewer fonts. Font source: google/fonts `ofl/dmsans/DMSans[opsz,wght].ttf`, Git
blob `c672f98060af9b2c85fca704ebd5ad9a8717c1df`; SHA-256
`8cd08d97e89c24d0aa92edd2f0f4c8ee6195eee9b7c9f154865a58b02f0c1c0d`.
Use existing readable system body fonts unless an independently tested local
font change is useful; the reference's typography suggestions do not require
external font loading or extra services.

Accessible linked-home name: **Scarb.TO home**. A decorative symbol next to
visible site text has `alt=""`; a stand-alone logo image has `alt="Scarb.TO"`.
Do not force screen readers to hear the full geography explanation on every
navigation. The source/artwork documentation supplies that explanation.

## Geography and reproducibility

Authoritative originals, never modified for branding:

- `docs/data/scarborough-council-boundary.geojson`, Git blob
  `06cb43ee1b137938f6feb8dd9b355dcf819b8838`.
- `docs/data/scarborough-neighbourhoods.geojson`, Git blob
  `14ba105712c753a8d1f47b9d00648381987dedf8` (31 features, not the 30-feature overlay).

`regions.json` records every named City feature exactly once. The specimen's
disconnected Southeast group is refined by assigning Centennial Scarborough
to the adjacent East group; other membership starts from the approved
illustrative manifest. No source records or underlying feature identifiers
change.

`scripts/build_brand.py` projects WGS84 coordinates into a local metric
azimuthal-equidistant CRS centred at 43.78° N, 79.20° W, with true north at
that central meridian (rather than UTM grid-north), dissolves each group,
snaps source coordinates to a 1-millimetre grid before double-precision
overlay to avoid floating-point seams, clips to the council shape and checks
partition coverage. Tiny independent-source gaps/overlaps are quantified and
reconciled for artwork only, with a fail-closed 0.1% ceiling. Shared-edge
topology-preserving simplification uses a 40-metre tolerance; the same outer
outline clips all regions. The output uses one uniform scale with screen-y
inverted, not a manual rotation or stretch. `geometry-report.json` records
actual errors, components, bounds, version and source hashes after generation.

Generation is a deliberate brand revision, not a daily data-refresh side
effect. A source hash mismatch stops generation for review. Preserve source
membership and metrics with each revision, and retain rollback in Git history.
Run with the separately pinned `scripts/requirements-brand.txt` toolchain;
this is an authoring tool, not a production runtime or new deployment service.

Contains information licensed under the **Open Government Licence – Toronto**:
https://open.toronto.ca/open-data-licence/. Source geometry: City of Toronto.
Scarb.TO is independent, not endorsed by the City or Scarborough Health Network.
Keep this attribution in the site's existing About/sources explanation.

## Existing release and review process

Apply the same assets/tokens to homepage, neighbourhood template and generated
pages, weekly generator, print/share surfaces, metadata and icons. Change the
authoritative generator rather than only its current output. Do not change
source dates, facts, RSS GUIDs, archived edition bytes or recorded hashes just
to restyle a page. Archive copy changes still require the existing explicit
editorial-revision path; prefer external CSS/asset updates where appropriate.

Use existing review/testing, not a parallel approval gate. Review source
geometry and all eight memberships, topology/coverage, final monochrome
similarity, small-size icon/wordmark, light/dark, print, desktop/mobile, actual
contrast and keyboard/non-happy-path UI. Integrate through the sole release
coordinator and existing GMKtec isolation/trusted-main/Pages route. Exact-head
tests, independent review and live verification must be recorded separately.
Brand completion does not mean the integrated resident release is complete.
