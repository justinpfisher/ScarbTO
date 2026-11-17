#!/usr/bin/env python3
"""Retain immutable qualified publishing inputs and lightweight City-area projections.

No source requests. Run after the existing validated snapshot/history generators.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.build_rss import load_events, SOURCE_URL, LICENCE_URL, parse_timestamp


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def retain(path, value):
    data = encoded(value)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f'Immutable publishing evidence changed: {path.name}')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)


def point_in_geometry(point, geometry):
    """Same edge-inclusive convention as the shared browser matcher."""
    def ring_location(ring):
        inside = False
        x, y = point
        for a, b in zip(ring, ring[1:]):
            cross = (x-a[0])*(b[1]-a[1])-(y-a[1])*(b[0]-a[0])
            if abs(cross) < 1e-12 and min(a[0], b[0])-1e-12 <= x <= max(a[0], b[0])+1e-12 and min(a[1], b[1])-1e-12 <= y <= max(a[1], b[1])+1e-12:
                return 0
            if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
                inside = not inside
        return 1 if inside else -1
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    for rings in polygons:
        outer = ring_location(rings[0])
        if outer == 0:
            return True
        if outer < 0:
            continue
        holes = [ring_location(hole) for hole in rings[1:]]
        if 0 in holes or 1 not in holes:
            return True
    return False

def build(root=ROOT):
    data = root / 'docs/data'
    output = root / 'docs/community-data'
    snapshot_bytes = (data / 'snapshot.json').read_bytes()
    snapshot = json.loads(snapshot_bytes)
    if snapshot.get('ready') is not True or snapshot.get('schema_version') != 1:
        raise ValueError('Publishing needs a qualified snapshot')
    source = snapshot['source']
    if source['dataset_url'] != SOURCE_URL or source['licence_url'] != LICENCE_URL:
        raise ValueError('Unapproved publishing source')
    checked = parse_timestamp(snapshot['published_at'], context='snapshot')
    validated = {e['id']: e for e in load_events(data / 'history')}
    raw = {}
    history_hashes = {}
    for path in sorted((data / 'history').glob('*.json')):
        content = path.read_bytes()
        history_hashes[path.name] = hashlib.sha256(content).hexdigest()
        for event in json.loads(content)['events']:
            if event['id'] not in validated:
                continue
            if event['id'] in raw:
                raise ValueError('Duplicate event identity')
            point = [event.get('longitude'), event.get('latitude')]
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in point):
                raise ValueError('Historic event location is missing; do not substitute current locations')
            if not (-80 < point[0] < -78 and 43 < point[1] < 45):
                raise ValueError('Historic event location is invalid')
            if event['status'] not in ('Pass', 'Conditional Pass', 'Closed'):
                raise ValueError('Invalid official outcome')
            if parse_timestamp(event['detected_at'], context='history') > checked:
                raise ValueError('History is newer than its qualified source release')
            # Public event allowlist: never carry arbitrary new upstream fields.
            keys = ('id', 'feed', 'kind', 'establishment_id', 'name', 'neighbourhood', 'inspection_date', 'detected_at', 'status', 'previous_status', 'latitude', 'longitude', 'source_url')
            raw[event['id']] = {key: event[key] for key in keys}
    if not raw:
        raise ValueError('Retained qualified history is missing')
    geometry_bytes = (data / 'scarborough-neighbourhoods.geojson').read_bytes()
    geometry_hash = hashlib.sha256(geometry_bytes).hexdigest()
    registry = {}
    for feature in json.loads(geometry_bytes)['features']:
        code = str(int(feature['properties']['AREA_SHORT_CODE']))
        key = f'city-{code}-{geometry_hash[:12]}'
        registry[key] = {
            'id': key, 'name': feature['properties']['AREA_NAME'], 'kind': 'city-neighbourhood',
            'city_code': code, 'purpose': 'editorial-coverage', 'verification': 'verified',
            'version': geometry_hash, 'source_url': 'https://open.toronto.ca/dataset/neighbourhoods/',
            'licence_url': LICENCE_URL, 'geometry': feature['geometry'],
            'coverage_note': 'Only records inside the qualified six Scarborough wards are included. City neighbourhoods can cross those wards; this is not necessarily a whole-neighbourhood total.',
        }
    # Reviewed custom definitions are repository files, never arbitrary remote URLs
    # or unauthenticated browser-written organisation boundaries.
    for path in sorted((root / 'community-boundaries').glob('*.json')):
        boundary = json.loads(path.read_text(encoding='utf-8'))
        if boundary.get('verification') != 'verified':
            continue
        required = ('id', 'name', 'purpose', 'source_urls', 'rights_basis', 'reviewed_at', 'source_date', 'interpretation', 'geometry', 'controls', 'coverage_note')
        if any(key not in boundary for key in required):
            raise ValueError('Custom boundary is missing source/rights/verification evidence')
        if boundary['purpose'] not in ('editorial-coverage', 'association-territory', 'print-distribution'):
            raise ValueError('Custom boundary meaning is invalid')
        if not boundary['source_urls'] or any(not url.startswith('https://') for url in boundary['source_urls']):
            raise ValueError('Custom boundary needs original source references')
        if not boundary['rights_basis'] or not boundary['interpretation']:
            raise ValueError('Custom boundary needs rights and interpretation disclosure')
        parse_timestamp(boundary['reviewed_at'], context='boundary review')
        geometry = boundary['geometry']
        if geometry.get('type') not in ('Polygon', 'MultiPolygon'):
            raise ValueError('Custom coverage requires polygon geometry')
        # Reuse the browser's topology/inclusion contract for custom definitions.
        subprocess.run(['node', '--input-type=module', '-e', "import {readFileSync} from 'node:fs'; import {validateGeometry} from './docs/community-publishing.mjs'; validateGeometry(JSON.parse(readFileSync(process.argv[1],'utf8')).geometry);", str(path)], cwd=root, check=True, capture_output=True, text=True)
        polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
        for rings in polygons:
            if not rings:
                raise ValueError('Custom boundary has no rings')
            for ring in rings:
                if len(ring) < 4 or ring[0] != ring[-1]:
                    raise ValueError('Custom boundary rings must close')
                for point in ring:
                    if len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point) or not (-79.6 <= point[0] <= -79 and 43.5 <= point[1] <= 44):
                        raise ValueError('Custom boundary needs finite Scarborough longitude/latitude')
        if len(boundary['controls']) < 2 or {c['inside'] for c in boundary['controls']} != {True, False}:
            raise ValueError('Custom boundary needs independent inside and outside controls')
        for control in boundary['controls']:
            if point_in_geometry(control['point'], geometry) != control['inside']:
                raise ValueError('Custom boundary fails its documented location controls')
        import re
        if not re.fullmatch(r'custom-[a-z0-9-]{1,70}', boundary['id']):
            raise ValueError('Invalid stable custom boundary identity')
        version = hashlib.sha256(encoded(boundary)).hexdigest()
        key = boundary['id'] + '-' + version[:12]
        registry[key] = {**boundary, 'id': key, 'stable_id': boundary['id'], 'version': version, 'kind': 'custom'}
    registry_hash = hashlib.sha256(encoded(registry)).hexdigest()
    events = sorted(raw.values(), key=lambda e: (parse_timestamp(e['detected_at'], context='event'), e['id']))
    release = {
        'schema_version': 1, 'source_url': SOURCE_URL, 'licence_url': LICENCE_URL,
        'checked_at': snapshot['published_at'], 'upstream_date_as_supplied': source['last_refreshed'],
        'history_start': events[0]['detected_at'], 'events': events,
        'records': [{k: r[k] for k in ('id','name','status','inspection_date','longitude','latitude','neighbourhood')} for r in snapshot['establishments']],
        'snapshot_sha256': hashlib.sha256(snapshot_bytes).hexdigest(), 'history_sha256': history_hashes,
        'geography_sha256': geometry_hash, 'registry_sha256': registry_hash,
    }
    release_id = hashlib.sha256(encoded(release)).hexdigest()
    release['id'] = release_id
    retain(output / 'releases' / f'{release_id}.json', release)
    retain(output / 'boundaries' / f'{registry_hash}.json', registry)
    # Each City projection contains complete historic events for its named area, not paginated UI results.
    # Exact polygon matching remains the common client's responsibility.
    for key, area in registry.items():
        projection = {**release, 'boundaries': {key: area}, 'records': [r for r in release['records'] if point_in_geometry([r['longitude'],r['latitude']],area['geometry'])], 'events': [e for e in events if point_in_geometry([e['longitude'], e['latitude']], area['geometry'])]}
        retain(output / 'releases' / release_id / f'{key}.json', projection)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'latest.json').write_bytes(encoded({'schema_version': 1, 'release_id': release_id, 'boundary_version': registry_hash, 'checked_at': release['checked_at'], 'areas': [{k: a[k] for k in ('id', 'name', 'city_code', 'kind', 'purpose', 'coverage_note') if k in a} for a in registry.values()]}))
    return release_id


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    print(build(parser.parse_args().root))
