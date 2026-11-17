"""Dependency-free checks for checked-in, reviewed brand assets.

Does not replace metric geometry generation/review or rendered accessibility QA.
"""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / 'docs/assets/brand'
SVG = '{http://www.w3.org/2000/svg}'

def check():
    manifest = json.loads((BRAND/'regions.json').read_text(encoding='utf-8'))
    source = json.loads((ROOT/'docs/data/scarborough-neighbourhoods.geojson').read_text(encoding='utf-8'))
    members = [n for r in manifest['regions'] for n in r['members']]
    assert 6 <= len(manifest['regions']) <= 8
    assert len(members) == len(set(members)) == 31
    assert set(members) == {f['properties']['AREA_NAME'] for f in source['features']}
    report = json.loads((BRAND/'geometry-report.json').read_text())
    assert report['region_definition_sha256'] == hashlib.sha256(json.dumps(manifest['regions'],sort_keys=True).encode()).hexdigest(), 'Stale assets: region definitions changed'
    assert report['generator_sha256'] == hashlib.sha256((ROOT/'scripts/build_brand.py').read_bytes()).hexdigest(), 'Stale assets: generator changed since last successful build'
    assert report['region_components'] == [1]*len(manifest['regions'])
    assert report['final_gap_m2'] < .01
    assert abs(report['final_overlap_m2']) < .01
    assert report['outline_hausdorff_m'] <= report['simplification_tolerance_m'] + .01
    for filename, expected in report['source_git_blobs'].items():
        data = (ROOT/'docs/data'/filename).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == expected
    files=['scarbto-mark-dark.svg','scarbto-mark.svg','scarbto-mark-mono.svg','scarbto-mark-light.svg',
           'scarbto-icon.svg','scarbto-connected.svg','scarbto-connected-light.svg']
    for name in files:
        root = ET.parse(BRAND/name).getroot()
        assert root.tag == SVG+'svg'
        assert root.find(SVG+'title') is not None
        assert root.find(SVG+'desc') is not None
        assert list(root.iter(SVG+'path')), name
        assert not list(root.iter(SVG+'text')), f'{name}: wordmark must be font-independent'
        assert not list(root.iter(SVG+'image')), f'{name}: no raster master'
        assert not list(root.iter(SVG+'script'))
        for el in root.iter():
            assert all(not key.rsplit('}',1)[-1].lower().startswith('on') for key in el.attrib)
            for key,value in el.attrib.items():
                if key.rsplit('}',1)[-1] == 'href':
                    assert value.startswith('#'), f'{name}: external resource'
        _,_,w,h = map(float,root.attrib['viewBox'].split())
        assert w>0 and h>0
        if name == 'scarbto-icon.svg': assert abs(w-h)<.001
    print('Brand source membership, provenance, coverage report and seven vector variants passed.')

if __name__ == '__main__': check()
