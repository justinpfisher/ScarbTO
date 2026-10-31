#!/usr/bin/env python3
"""Read-only HTTP verification of Scarb.TO production after Pages deploy.

Checks actual delivered HTML and public data rather than a workflow's success flag.
Never alters the live site or source data; fails if the area explorer is absent or
the official 6-ward/30-neighbourhood output is missing or malformed.
"""
from __future__ import annotations

import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = 'https://scarb.to/'
CHECKS = (
    ('', 300_000),
    ('app.mjs', 250_000),
    ('area-explorer.mjs', 250_000),
    ('data/scarborough-wards.geojson', 3_500_000),
    ('data/scarborough-overlay-neighbourhoods.geojson', 4_000_000),
    ('data/snapshot.json', 12_000_000),
)
EXPECTED_WARDS = {'20', '21', '22', '23', '24', '25'}


def download(path: str, marker: str) -> bytes:
    suffix = ('?' if not path or '?' not in path else '&') + 'release=' + quote(marker, safe='')
    url = BASE + path + suffix
    request = Request(url, headers={
        'User-Agent': 'ScarbTO-public-release-verifier/1.0',
        'Cache-Control': 'no-cache',
        'Accept': 'application/json,text/html,text/javascript,*/*',
    })
    with urlopen(request, timeout=12) as response:
        if response.status != 200:
            raise ValueError(f'{path or "index"}: HTTP {response.status}')
        bound = dict(CHECKS)[path]
        body = response.read(bound + 1)
        if not body or len(body) > bound:
            raise ValueError(f'{path or "index"}: unexpected response size')
        return body


def validate_feature_collection(blob: bytes, count: int, label: str) -> set[str]:
    payload = json.loads(blob)
    if payload.get('type') != 'FeatureCollection' or not isinstance(payload.get('features'), list):
        raise ValueError(label + ': not a GeoJSON FeatureCollection')
    features = payload['features']
    if len(features) != count:
        raise ValueError(f'{label}: expected {count} official areas; got {len(features)}')
    codes = [f.get('properties', {}).get('AREA_SHORT_CODE') for f in features]
    if not all(isinstance(code, str) and code for code in codes) or len(set(codes)) != count:
        raise ValueError(label + ': missing or duplicated area codes')
    if not all(f.get('geometry', {}).get('type') in ('Polygon', 'MultiPolygon') for f in features):
        raise ValueError(label + ': invalid geometry type')
    return set(codes)


def verify_once(marker: str) -> None:
    received = {path: download(path, marker) for path, _ in CHECKS}
    html = received[''].decode('utf-8')
    app = received['app.mjs'].decode('utf-8')
    explorer = received['area-explorer.mjs'].decode('utf-8')
    if 'data-area-overlay="neighbourhood"' not in html or 'data-area-overlay="ward"' not in html:
        raise ValueError('Production HTML does not contain the approved area controls')
    if 'createAreaExplorer' not in app or 'area-region-fill' not in explorer:
        raise ValueError('Production UI bundle does not contain the area overlay implementation')
    wards = validate_feature_collection(received['data/scarborough-wards.geojson'], 6, 'wards')
    if wards != EXPECTED_WARDS:
        raise ValueError('Production ward codes differ from six official Scarborough wards')
    neighbourhoods = validate_feature_collection(received['data/scarborough-overlay-neighbourhoods.geojson'], 30, 'neighbourhoods')
    if '125' not in neighbourhoods or '139' not in neighbourhoods or '046' in neighbourhoods:
        raise ValueError('Production neighbourhood selection differs from qualified police crosswalk')
    snapshot = json.loads(received['data/snapshot.json'])
    if snapshot.get('schema_version') != 1 or not snapshot.get('ready') or len(snapshot.get('establishments', [])) < 300:
        raise ValueError('Public DineSafe snapshot is not a validated, populated dataset')
    print('LIVE VERIFIED: https://scarb.to/ · official areas: 6 wards/30 neighbourhoods; '
          f'DineSafe establishments: {len(snapshot["establishments"])}; '
          f'published: {snapshot.get("published_at", "unspecified")}')


def main() -> int:
    marker = sys.argv[1] if len(sys.argv) > 1 else 'manual-check'
    last_error = None
    for attempt in range(1, 7):
        try:
            verify_once(marker)
            return 0
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
            last_error = exc
            print(f'Production check {attempt}/6 not verified: {type(exc).__name__}: {exc}', file=sys.stderr)
            if attempt < 6:
                time.sleep(10)
    print('LIVE NOT VERIFIED: leave the new release marked unconfirmed and investigate CDN or assets: '
          + str(last_error), file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
