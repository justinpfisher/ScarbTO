#!/usr/bin/env python3
"""Publish an independently validated, Scarborough-only Toronto DineSafe snapshot.

Python 3.11+ stdlib. No database, secrets, API keys, or pip dependencies.
Never overwrite the last published files if retrieval or validation fails.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode, urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CKAN = 'https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=dinesafe'
DATASET = 'https://open.toronto.ca/dataset/dinesafe/'
LICENCE = 'https://open.toronto.ca/open-data-licence/'
WARDS = 'https://gis.toronto.ca/arcgis/rest/services/cot_geospatial22/FeatureServer/0/query'
NEIGHBOURHOODS = 'https://gis.toronto.ca/arcgis/rest/services/cot_geospatial26/FeatureServer/9/query'
MAP_QUERY = {'where': '1=1', 'outFields': 'AREA_NAME,AREA_SHORT_CODE', 'returnGeometry': 'true', 'outSR': '4326', 'f': 'geojson'}

# Source-qualified official 2022 Social Planning Neighbourhoods v3.0 membership.
# Derived from hash-pinned 2026-10-27 contract; not a City-supplied membership flag.
AREA_NEIGHBOURHOODS = {
  "116": "Steeles",
  "118": "Tam O'Shanter-Sullivan",
  "119": "Wexford/Maryvale",
  "120": "Clairlea-Birchmount",
  "121": "Oakridge",
  "122": "Birchcliffe-Cliffside",
  "123": "Cliffcrest",
  "124": "Kennedy Park",
  "125": "Ionview",
  "126": "Dorset Park",
  "128": "Agincourt South-Malvern West",
  "129": "Agincourt North",
  "130": "Milliken",
  "133": "Centennial Scarborough",
  "134": "Highland Creek",
  "135": "Morningside",
  "136": "West Hill",
  "138": "Eglinton East",
  "139": "Scarborough Village",
  "140": "Guildwood",
  "141": "Golfdale-Cedarbrae-Woburn",
  "142": "Woburn North",
  "143": "West Rouge",
  "144": "Morningside Heights",
  "145": "Malvern West",
  "146": "Malvern East",
  "147": "L'Amoreaux West",
  "148": "East L'Amoreaux",
  "156": "Bendale-Glen Andrew",
  "157": "Bendale South"
}
AREA_WARDS = {
  "20": "Scarborough Southwest",
  "21": "Scarborough Centre",
  "22": "Scarborough-Agincourt",
  "23": "Scarborough North",
  "24": "Scarborough-Guildwood",
  "25": "Scarborough-Rouge Park"
}


def qualified_area_features(source: dict, expected: dict[str, str]) -> dict:
    """Publish complete official-area features; never derive them from establishment coverage."""
    if source.get('type') != 'FeatureCollection' or not isinstance(source.get('features'), list):
        raise DataError('Area boundary source is not a FeatureCollection')
    out = {}
    for feature in source['features']:
        props = feature.get('properties') or {}
        code = str(props.get('AREA_SHORT_CODE') or '').strip()
        if code not in expected:
            continue
        if code in out or props.get('AREA_NAME') != expected[code]:
            raise DataError('Duplicate or changed official area code/name: ' + code)
        geom = feature.get('geometry') or {}
        rings = boxes(geom)
        if not rings:
            raise DataError('Missing official area geometry: ' + code)
        for polygon in rings:
            if not isinstance(polygon, list) or not polygon:
                raise DataError('Invalid official polygon: ' + code)
            for ring in polygon:
                if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                    raise DataError('Unclosed official ring: ' + code)
                for point in ring:
                    if not isinstance(point, list) or len(point) < 2 or not all(
                        isinstance(n, (int, float)) and n == n for n in point[:2]
                    ) or not (-80 < point[0] < -78 and 43 < point[1] < 45):
                        raise DataError('Invalid Toronto boundary point: ' + code)
        out[code] = feature
    if set(out) != set(expected):
        raise DataError('Incomplete official area layer; missing: ' + ', '.join(sorted(set(expected) - set(out))))
    return {'type': 'FeatureCollection', 'features': [out[code] for code in sorted(out)]}


MAX_DOWNLOAD = 100 * 1024 * 1024
HEADERS = {'User-Agent': 'ScarbTO-PoC/0.1 (https://scarb.to; public open-data consumer)', 'Accept': '*/*'}
ALLOWED_STATUSES = {'pass': 'Pass', 'conditional pass': 'Conditional Pass', 'closed': 'Closed'}
SCHEMA = 1

class DataError(RuntimeError):
    pass


def download(url: str, stage: str) -> bytes:
    req = Request(url, headers=HEADERS)
    parsed = urlsplit(url)
    endpoint = f'{parsed.scheme}://{parsed.hostname}{parsed.path}'
    try:
        with urlopen(req, timeout=120) as response:
            if response.status != 200:
                raise DataError(f'HTTP {response.status} retrieving {stage} from {endpoint}')
            blob = response.read(MAX_DOWNLOAD + 1)
            if len(blob) > MAX_DOWNLOAD:
                raise DataError('Resource exceeds 100 MiB safety limit')
            return blob
    except HTTPError as exc:
        raise DataError(f'HTTP {exc.code} retrieving {stage} from {endpoint}') from None
    except (URLError, TimeoutError, OSError):
        raise DataError(f'Network failure retrieving {stage} from {endpoint}') from None


def json_bytes(raw: bytes, label: str) -> dict:
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise DataError(f'Invalid JSON: {label}') from exc
    if not isinstance(result, dict):
        raise DataError(f'Invalid JSON object: {label}')
    return result


def get_resources(metadata: dict) -> tuple[str, str | None]:
    if not metadata.get('success') or not isinstance(metadata.get('result'), dict):
        raise DataError('CKAN metadata did not report success')
    package = metadata['result']
    options = []
    for resource in package.get('resources', []):
        name = str(resource.get('name', '')).strip().casefold()
        url = str(resource.get('url', ''))
        fmt = str(resource.get('format', '')).strip().casefold()
        if fmt == 'csv' and url.startswith('https://') and 'historical' not in name:
            score = int('dinesafe.csv' in name) * 4 + int('dinesafe' in name) * 2 + int('dinesafe.csv' in url)
            options.append((score, url))
    if not options:
        raise DataError('No HTTPS current DineSafe CSV resource found; source schema needs review')
    options.sort(reverse=True)
    return options[0][1], package.get('last_refreshed')


def keyify(value: str) -> str:
    return ''.join(ch for ch in (value or '').upper() if ch.isalnum())


def as_string(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(keyify(key))
        if value is not None and str(value).strip():
            return str(value).strip()
    return ''


def date_string(value: str) -> str | None:
    value = (value or '').strip()
    if not value:
        return None
    try:
        if len(value) >= 10 and value[4:5] == '-' and value[7:8] == '-':
            return datetime.strptime(value[:10], '%Y-%m-%d').date().isoformat()
        for fmt in ('%Y%m%d', '%m/%d/%Y', '%d-%b-%Y', '%d-%b-%y'):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
    except ValueError:
        return None
    return None


def status_string(value: str) -> str:
    status = ' '.join(value.strip().casefold().split())
    if status not in ALLOWED_STATUSES:
        raise DataError(f'Unrecognised establishment status: {value[:80]!r}')
    return ALLOWED_STATUSES[status]


def coord(value: str) -> float | None:
    try:
        number = float(value)
        return number if number == number else None
    except (ValueError, TypeError):
        return None


def boxes(geom: dict) -> list[list[list[float]]]:
    """Yield Polygon ring arrays for GeoJSON Polygon/MultiPolygon."""
    typ = geom.get('type')
    if typ == 'Polygon':
        return [geom.get('coordinates', [])]
    if typ == 'MultiPolygon':
        return geom.get('coordinates', [])
    return []


def on_segment(x: float, y: float, x1: float, y1: float, x2: float, y2: float) -> bool:
    cross = (x-x1)*(y2-y1) - (y-y1)*(x2-x1)
    return abs(cross) < 1e-10 and min(x1,x2)-1e-12 <= x <= max(x1,x2)+1e-12 and min(y1,y2)-1e-12 <= y <= max(y1,y2)+1e-12


def inside_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        x1, y1 = a[:2]
        x2, y2 = b[:2]
        if on_segment(lon, lat, x1, y1, x2, y2):
            return True
        if (y1 > lat) != (y2 > lat):
            at_x = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
            if lon < at_x:
                inside = not inside
    return inside


def in_geometry(lon: float, lat: float, geom: dict) -> bool:
    for polygon in boxes(geom):
        if polygon and inside_ring(lon, lat, polygon[0]) and not any(inside_ring(lon, lat, hole) for hole in polygon[1:]):
            return True
    return False


def geometry_bbox(geom: dict) -> tuple[float, float, float, float]:
    points = [pt for poly in boxes(geom) for ring in poly for pt in ring]
    if not points:
        raise DataError('Empty geospatial boundary')
    return (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))


def prepare_shapes(feature_collection: dict, only_scarborough: bool = False) -> list[tuple[str, tuple, dict, dict]]:
    if feature_collection.get('type') != 'FeatureCollection':
        raise DataError('City boundary response is not GeoJSON FeatureCollection')
    shapes = []
    for feat in feature_collection.get('features', []):
        name = str(feat.get('properties', {}).get('AREA_NAME', '')).strip()
        geom = feat.get('geometry')
        if not name or not isinstance(geom, dict):
            continue
        if only_scarborough and 'scarborough' not in name.casefold():
            continue
        shapes.append((name, geometry_bbox(geom), geom, feat))
    if only_scarborough and len(shapes) != 6:
        raise DataError(f'Expected exactly 6 Scarborough municipal ward polygons, found {len(shapes)}')
    if not shapes:
        raise DataError('No valid city boundary polygons')
    return shapes


def matching_shape(lon: float, lat: float, shapes: list) -> str | None:
    for name, bbox, geom, _ in shapes:
        if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3] and in_geometry(lon, lat, geom):
            return name
    return None


def clean_address(value: str) -> str:
    """Omit the City's literal missing-component token; do not invent an address."""
    return ' '.join(part for part in value.split() if part != 'None')


def optional_text(value: str) -> str:
    """A source placeholder is missing information, not an establishment type."""
    return '' if value.casefold() in ('none', 'null') else value


def normalise(csv_data: bytes, wards: dict, neighbourhoods: dict, *, minimum: int = 300) -> tuple[list[dict], dict, dict]:
    ward_shapes = prepare_shapes(wards, only_scarborough=True)
    neigh_shapes = prepare_shapes(neighbourhoods)
    try:
        text = csv_data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise DataError('CSV was not UTF-8; source encoding changed') from exc
    reader = csv.DictReader(io.StringIO(text))
    found_columns = {keyify(x) for x in (reader.fieldnames or [])}
    # Current CKAN resource is a row-per-inspection export. `estId` is the
    # stable location identifier; unique_id identifies an individual row.
    # Retain compatibility with the older documented field names as well.
    required = {'INSPECTIONDATE','LATITUDE','LONGITUDE'}
    missing = required - found_columns
    alternatives = ({'ESTID','ESTNAME','ADDRESS','INSPECTIONSTATUS'},
                    {'ESTABLISHMENTID','ESTABLISHMENTNAME','ESTABLISHMENTADDRESS','ESTABLISHMENTSTATUS'})
    if not any(fields <= found_columns for fields in alternatives):
        missing |= {'ESTID/ESTABLISHMENTID','ESTNAME/ESTABLISHMENTNAME',
                    'ADDRESS/ESTABLISHMENTADDRESS','INSPECTIONSTATUS/ESTABLISHMENTSTATUS'}
    if missing:
        raise DataError(f'DineSafe CSV schema changed; required columns missing: {sorted(missing)}')
    newest: dict[str, dict] = {}
    city_rows = 0
    geocoded_rows = 0
    scarborough_rows = 0
    for original in reader:
        city_rows += 1
        row = {keyify(k): v for k, v in original.items() if k is not None}
        ident = as_string(row, 'estId', 'ESTABLISHMENT_ID')
        lat = coord(as_string(row, 'LATITUDE'))
        lon = coord(as_string(row, 'LONGITUDE'))
        day = date_string(as_string(row, 'INSPECTION_DATE'))
        if not ident or not day or lat is None or lon is None or not (-80 < lon < -78 and 43 < lat < 45):
            continue
        geocoded_rows += 1
        ward = matching_shape(lon, lat, ward_shapes)
        if not ward:
            continue
        scarborough_rows += 1
        name = as_string(row, 'estName', 'ESTABLISHMENT_NAME')
        if not name:
            continue
        status = status_string(as_string(row, 'inspectionStatus', 'ESTABLISHMENT_STATUS'))
        item = {
            'id': ident, 'name': name,
            'address': clean_address(as_string(row, 'address', 'ESTABLISHMENT_ADDRESS')),
            # The current City's typeDesc carries inspection findings, not
            # establishment categories. Do not publish it as "type".
            'type': optional_text(as_string(row, 'ESTABLISHMENTTYPE', 'ESTABLISHMENT_TYPE')),
            'inspection_detail': optional_text(as_string(row, 'typeDesc')),
            'status': status, 'inspection_date': day, 'latitude': lat, 'longitude': lon,
            'ward': ward, 'neighbourhood': matching_shape(lon, lat, neigh_shapes),
        }
        old = newest.get(ident)
        if old is None or day > old['inspection_date']:
            newest[ident] = item
        elif day == old['inspection_date'] and status != old['status']:
            raise DataError(f'Conflicting outcomes on latest inspection date for establishment {ident}')
    if city_rows < minimum:
        raise DataError(f'CSV contained only {city_rows} rows; expected >= {minimum}')
    establishments = sorted(newest.values(), key=lambda r: (r['name'].casefold(), r['id']))
    if len(establishments) < minimum:
        raise DataError(f'Only {len(establishments)} Scarborough establishments; expected >= {minimum}')
    if geocoded_rows < len(establishments) or scarborough_rows < len(establishments):
        raise DataError('Invalid geospatial counts')
    # Keep only neighbourhood boundaries used by a geolocated Scarborough establishment.
    matched_names = {r['neighbourhood'] for r in establishments if r['neighbourhood']}
    local_neighbourhoods = {'type': 'FeatureCollection', 'features': [feat for name, _, _, feat in neigh_shapes if name in matched_names]}
    quality = {'source_rows': city_rows, 'geocoded_rows': geocoded_rows, 'scarborough_rows': scarborough_rows,
               'scarborough_establishments': len(establishments), 'unassigned_neighbourhoods': sum(not r['neighbourhood'] for r in establishments)}
    return establishments, quality, local_neighbourhoods


def make_activity(current: list[dict], previous: dict | None, now: datetime) -> list[dict]:
    history = [{**event, 'address': clean_address(event.get('address') or '')}
               for event in previous.get('activity', [])] if previous else []
    before = {r['id']: r for r in previous.get('establishments', [])} if previous else {}
    # Initial population is a historical baseline, never falsely claimed as new activity.
    if previous and previous.get('ready'):
        for new in current:
            old = before.get(new['id'])
            if old is None:
                kind = 'first_seen'
            elif old['status'] != new['status']:
                kind = 'status_changed'
            elif new['inspection_date'] > old['inspection_date']:
                kind = 'new_inspection'
            else:
                continue
            seed = f"{new['id']}|{kind}|{new['inspection_date']}|{new['status']}"
            event_id = hashlib.sha256(seed.encode()).hexdigest()[:20]
            history.append({
                'id': event_id, 'feed': 'dinesafe', 'kind': kind,
                'establishment_id': new['id'], 'name': new['name'], 'address': new['address'],
                'neighbourhood': new['neighbourhood'], 'inspection_date': new['inspection_date'],
                'detected_at': now.isoformat(timespec='seconds'), 'status': new['status'],
                'previous_status': old['status'] if old else None,
                'latitude': new['latitude'], 'longitude': new['longitude'],
                'source_url': DATASET,
            })
    cutoff = (now.date() - timedelta(days=365)).isoformat()
    deduped = {x['id']: x for x in history if x.get('detected_at','')[:10] >= cutoff}
    return sorted(deduped.values(), key=lambda v: (v['detected_at'], v['id']), reverse=True)[:5000]


def build_snapshot(csv_data: bytes, wards: dict, neighbourhoods: dict, *, previous: dict | None,
                   source_url: str, last_refreshed: str | None, now: datetime, minimum: int = 300) -> tuple[dict, dict]:
    establishments, quality, local_neighbourhoods = normalise(csv_data, wards, neighbourhoods, minimum=minimum)
    if previous and previous.get('ready'):
        old_len = len(previous.get('establishments', []))
        if old_len and len(establishments) < old_len * .75:
            raise DataError(f'Suspected mass deletion: {old_len} -> {len(establishments)}; held for review')
    snap = {'schema_version': SCHEMA, 'ready': True,
            'published_at': now.isoformat(timespec='seconds'),
            'source': {'name': 'City of Toronto Open Data — DineSafe', 'dataset_url': DATASET,
                       'licence_url': LICENCE, 'resource_url': source_url, 'last_refreshed': last_refreshed},
            'quality': quality, 'establishments': establishments,
            'activity': make_activity(establishments, previous, now)}
    return snap, local_neighbourhoods


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode='wb', dir=path.parent, prefix='.stage-', delete=False) as f:
        stage = Path(f.name)
        try:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        except Exception:
            stage.unlink(missing_ok=True)
            raise
    os.replace(stage, path)


def archived_activity_by_id(output: Path) -> dict[str, dict]:
    """Read every validated month so an event ID cannot move on a retry."""
    history_dir = output / 'history'
    archived: dict[str, dict] = {}
    if not history_dir.exists():
        return archived
    for path in sorted(history_dir.glob('*.json')):
        month = path.stem
        try:
            if len(month) != 7 or datetime.strptime(month, '%Y-%m').strftime('%Y-%m') != month:
                raise ValueError('invalid month')
        except ValueError as exc:
            raise DataError(f'Invalid existing activity archive name: {path}') from exc
        try:
            existing = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            raise DataError(f'Invalid existing activity archive: {path}') from exc
        if not isinstance(existing, dict) or existing.get('schema_version') != 1 or existing.get('month') != month or not isinstance(existing.get('events'), list):
            raise DataError(f'Invalid existing activity archive: {path}')
        for event in existing['events']:
            event_id = event.get('id') if isinstance(event, dict) else None
            observed = event.get('detected_at') if isinstance(event, dict) else None
            if not isinstance(event_id, str) or not event_id or not isinstance(observed, str) or observed[:7] != month:
                raise DataError(f'Invalid archived event: {path}')
            if event_id in archived:
                raise DataError(f'Duplicate event ID across monthly archives: {event_id}')
            archived[event_id] = event
    return archived


def reconcile_activity_history(output: Path, activity: list[dict]) -> list[dict]:
    """Keep the first archived observation when retries regenerate an event."""
    archived = archived_activity_by_id(output)
    reconciled: dict[str, dict] = {}
    for event in activity:
        event_id = event.get('id')
        if not isinstance(event_id, str) or not event_id:
            raise DataError('An observed change is missing its identifier')
        canonical = archived.get(event_id, event)
        current = reconciled.get(event_id)
        if current is None or canonical['detected_at'] < current['detected_at']:
            reconciled[event_id] = canonical
    return sorted(reconciled.values(), key=lambda value: (value['detected_at'], value['id']), reverse=True)


def prepare_activity_archives(output: Path, activity: list[dict]) -> list[tuple[Path, bytes]]:
    """Stage durable monthly observed events; do not backfill nonexistent observations.

    Archives contain only source-linked events already produced by successful
    snapshot comparisons. Existing event IDs are immutable; a repeated import
    cannot silently rewrite the original observation.
    """
    archived = archived_activity_by_id(output)
    months: dict[str, list[dict]] = {}
    pending_ids: set[str] = set()
    for event in activity:
        event_id = event.get('id')
        observed = event.get('detected_at', '')
        month = observed[:7] if isinstance(observed, str) else ''
        try:
            if len(month) != 7 or datetime.strptime(month, '%Y-%m').strftime('%Y-%m') != month:
                raise ValueError('invalid month')
        except ValueError as exc:
            raise DataError(f'Invalid archived observation month: {month!r}') from exc
        if not isinstance(event_id, str) or not event_id or not event.get('source_url'):
            raise DataError('An observed change is missing its identifier or official source')
        if event_id in archived or event_id in pending_ids:
            continue
        pending_ids.add(event_id)
        months.setdefault(month, []).append(event)

    pending: list[tuple[Path, bytes]] = []
    for month, new_events in sorted(months.items()):
        path = output / 'history' / (month + '.json')
        if path.exists():
            existing = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(existing, dict) or existing.get('schema_version') != 1 or existing.get('month') != month or not isinstance(existing.get('events'), list):
                raise DataError(f'Invalid existing activity archive: {path}')
            previous = existing['events']
        else:
            previous = []
        by_id: dict[str, dict] = {}
        for event in previous:
            if not isinstance(event, dict) or not isinstance(event.get('id'), str) or event['id'] in by_id:
                raise DataError(f'Invalid or duplicate archived event: {path}')
            by_id[event['id']] = event
        for event in new_events:
            by_id.setdefault(event['id'], event)
        records = sorted(by_id.values(), key=lambda value: (value['detected_at'], value['id']))
        serialised = json.dumps({'schema_version': 1, 'month': month, 'events': records},
                                separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        if not path.exists() or path.read_bytes() != serialised:
            pending.append((path, serialised))
    return pending

def load_local(path: str) -> bytes:
    return Path(path).read_bytes()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path(__file__).resolve().parent.parent / 'docs/data')
    p.add_argument('--csv', help='Offline input current DineSafe CSV (requires ward and neighbourhood fixtures)')
    p.add_argument('--wards', help='Offline ward GeoJSON')
    p.add_argument('--neighbourhoods', help='Offline neighbourhood GeoJSON')
    p.add_argument('--minimum', type=int, default=300, help='Establishment minimum (production 300)')
    p.add_argument('--dry-run', action='store_true', help='Fetch and validate without publishing')
    args = p.parse_args()
    sources = [args.csv, args.wards, args.neighbourhoods]
    if any(sources) and not all(sources):
        p.error('Provide --csv, --wards and --neighbourhoods together for offline mode')
    now = datetime.now(timezone.utc)
    if all(sources):
        raw_csv, raw_wards, raw_neigh = map(load_local, sources)
        source_url = 'offline-fixture'
        refreshed = None
    else:
        metadata = json_bytes(download(CKAN, 'CKAN package metadata'), 'CKAN package')
        source_url, refreshed = get_resources(metadata)
        raw_csv = download(source_url, 'DineSafe CSV')
        raw_wards = download(WARDS + '?' + urlencode(MAP_QUERY), 'official ward geography')
        raw_neigh = download(NEIGHBOURHOODS + '?' + urlencode(MAP_QUERY), 'official neighbourhood geography')
    wards = json_bytes(raw_wards, 'wards')
    neighbourhoods = json_bytes(raw_neigh, 'neighbourhoods')
    previous_path = args.output / 'snapshot.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else None
    snapshot, local_neigh = build_snapshot(raw_csv, wards, neighbourhoods, previous=previous,
        source_url=source_url, last_refreshed=refreshed, now=now, minimum=args.minimum)
    # These layers use the same downloaded, validated City geography as the DineSafe import.
    # Neighbourhood overlay membership is deliberately independent of establishment coverage.
    overlay_wards = qualified_area_features(wards, AREA_WARDS)
    overlay_neighbourhoods = qualified_area_features(neighbourhoods, AREA_NEIGHBOURHOODS)
    snapshot['activity'] = reconcile_activity_history(args.output, snapshot['activity'])
    fields = ['id', 'name', 'address', 'type', 'inspection_detail', 'status', 'inspection_date', 'latitude', 'longitude', 'ward', 'neighbourhood',
              'source_url', 'licence_url', 'collected_at']
    export = io.StringIO()
    writer = csv.DictWriter(export, fieldnames=fields)
    writer.writeheader()
    for entry in snapshot['establishments']:
        line = {**entry, 'source_url': DATASET, 'licence_url': LICENCE, 'collected_at': snapshot['published_at']}
        # A downloadable CSV may be opened as a spreadsheet. Treat source-controlled
        # names and addresses as text, not user-executable spreadsheet formulae.
        for field in ('id', 'name', 'address', 'type', 'inspection_detail', 'ward', 'neighbourhood'):
            value = line.get(field)
            if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
                line[field] = "'" + value
        writer.writerow(line)
    print(json.dumps({'quality': snapshot['quality'], 'new_activity': len(snapshot['activity']),
                     'dry_run': args.dry_run, 'source': source_url}, indent=2))
    if args.dry_run:
        return
    archive_writes = prepare_activity_archives(args.output, snapshot['activity'])
    atomic_write(args.output / 'scarborough-wards.geojson', json.dumps(overlay_wards, separators=(',', ':'), ensure_ascii=False).encode())
    atomic_write(args.output / 'scarborough-overlay-neighbourhoods.geojson', json.dumps(overlay_neighbourhoods, separators=(',', ':'), ensure_ascii=False).encode())
    # Retain the existing DineSafe-covered neighbourhood geometry for legacy zoom/filter behaviour.
    atomic_write(args.output / 'scarborough-neighbourhoods.geojson', json.dumps(local_neigh, separators=(',', ':'), ensure_ascii=False).encode())
    atomic_write(args.output / 'establishments.csv', export.getvalue().encode('utf-8-sig'))
    for archive_path, archive_data in archive_writes:
        atomic_write(archive_path, archive_data)
    atomic_write(previous_path, json.dumps(snapshot, separators=(',', ':'), ensure_ascii=False).encode())


if __name__ == '__main__':
    try:
        main()
    except (DataError, OSError, ValueError) as exc:
        raise SystemExit(f'NOT PUBLISHED: {exc}') from exc
