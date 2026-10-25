#!/usr/bin/env python3
"""Check published snapshot before making it visible (no network)."""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / 'docs' / 'data'
s = json.loads((ROOT / 'snapshot.json').read_text(encoding='utf-8'))
if s.get('schema_version') != 1 or not s.get('ready'):
    raise SystemExit('Refusing uninitialised snapshot')
entries = s.get('establishments', [])
if len(entries) < 300 or len({e['id'] for e in entries}) != len(entries):
    raise SystemExit('Insufficient or duplicate establishment records')
for entry in entries:
    if entry['status'] not in ('Pass','Conditional Pass','Closed'):
        raise SystemExit('Invalid status value')
    if not (-80 < entry['longitude'] < -78 and 43 < entry['latitude'] < 45):
        raise SystemExit('Invalid coordinates')
when = datetime.fromisoformat(s['published_at'])
if when.tzinfo is None or datetime.now(timezone.utc)-when > timedelta(hours=3):
    raise SystemExit('Snapshot not freshly built; held')
if not (ROOT/'establishments.csv').is_file() or not (ROOT/'scarborough-neighbourhoods.geojson').is_file():
    raise SystemExit('Required export missing')
print(f"Verified {len(entries)} establishments and {len(s.get('activity',[]))} change events")
