import unittest
import tempfile
import json
import os
import stat
from unittest.mock import patch
from pathlib import Path
from scripts import build_community_publishing as publishing
from scripts.build_community_publishing import point_in_geometry, retain

class CommunityProjectionTests(unittest.TestCase):
    def test_retained_evidence_is_idempotent_and_cannot_be_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'release.json'
            retain(path, {'id': 'a', 'copy': 'Original evidence'})
            original = path.read_bytes()
            retain(path, {'copy': 'Original evidence', 'id': 'a'})
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, 'Immutable'):
                retain(path, {'id': 'a', 'copy': 'Changed'})
            self.assertEqual(path.read_bytes(), original)


    def fixture(self, root):
        data = root / 'docs/data'
        (data / 'history').mkdir(parents=True)
        event = {
            'id': 'a' * 20, 'feed': 'dinesafe', 'kind': 'first_seen',
            'establishment_id': '1', 'name': 'Synthetic café',
            'neighbourhood': 'Synthetic area', 'status': 'Pass',
            'previous_status': None, 'inspection_date': '2026-11-01',
            'detected_at': '2026-11-02T12:00:00+00:00',
            'latitude': 43.75, 'longitude': -79.25,
            'source_url': publishing.SOURCE_URL,
        }
        snapshot = {
            'ready': True, 'schema_version': 1,
            'published_at': '2026-11-03T12:00:00+00:00',
            'source': {'dataset_url': publishing.SOURCE_URL,
                       'licence_url': publishing.LICENCE_URL,
                       'last_refreshed': '2026-11-03'},
            'establishments': [{**event, 'id': '1'}],
        }
        geometry = {'features': [{
            'properties': {'AREA_SHORT_CODE': '1', 'AREA_NAME': 'Synthetic café area'},
            'geometry': {'type': 'Polygon', 'coordinates': [[
                [-79.3, 43.7], [-79.2, 43.7], [-79.2, 43.8],
                [-79.3, 43.8], [-79.3, 43.7]]]},
        }]}
        for path, value in [(data / 'snapshot.json', snapshot),
                            (data / 'history/2026-11.json',
                             {'schema_version': 1, 'month': '2026-11', 'events': [event]}),
                            (data / 'scarborough-neighbourhoods.geojson', geometry)]:
            path.write_text(json.dumps(value), encoding='utf-8')
        return root / 'docs/community-data/latest.json'

    def test_latest_canonical_bytes_idempotence_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            latest = self.fixture(root)
            reference = root / 'default-mode'
            reference.write_bytes(b'')
            release_id = publishing.build(root)
            if os.name != 'nt':
                self.assertEqual(stat.S_IMODE(latest.stat().st_mode),
                                 stat.S_IMODE(reference.stat().st_mode))
                latest.chmod(0o640)
            mode = stat.S_IMODE(latest.stat().st_mode)
            selector = json.loads(latest.read_bytes())
            registry = json.loads((latest.parent / 'boundaries' /
                                   (selector['boundary_version'] + '.json')).read_bytes())
            expected = {'schema_version': 1, 'release_id': release_id,
                        'boundary_version': selector['boundary_version'],
                        'checked_at': '2026-11-03T12:00:00+00:00',
                        'areas': [{k: a[k] for k in ('id', 'name', 'city_code', 'kind',
                                  'purpose', 'coverage_note')} for a in registry.values()]}
            canonical = json.dumps(expected, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':')).encode('utf-8')
            self.assertEqual(latest.read_bytes(), canonical)
            before = {p.relative_to(root): p.read_bytes()
                      for p in latest.parent.rglob('*') if p.is_file()}
            self.assertEqual(publishing.build(root), release_id)
            self.assertEqual({p.relative_to(root): p.read_bytes()
                              for p in latest.parent.rglob('*') if p.is_file()}, before)
            self.assertEqual(stat.S_IMODE(latest.stat().st_mode), mode)
            self.assertFalse(list(latest.parent.glob('.latest.json.*.tmp')))

    def test_partial_selector_write_keeps_last_good(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            latest = self.fixture(root)
            publishing.build(root)
            original = latest.read_bytes()
            write_bytes = Path.write_bytes

            def fail_write(path, content):
                if path == latest:
                    write_bytes(path, content[:7])
                    raise OSError('simulated partial write')
                return write_bytes(path, content)

            # Before the fix this injects a partial direct selector write.
            # After the fix the same failure is injected into the staging stream.
            fdopen = os.fdopen

            def failing_stream(*args, **kwargs):
                stream = fdopen(*args, **kwargs)
                write = stream.write

                def partial(content):
                    write(content[:7])
                    raise OSError('simulated partial write')

                stream.write = partial
                return stream

            with patch.object(Path, 'write_bytes', fail_write), \
                    patch.object(publishing.os, 'fdopen', failing_stream):
                with self.assertRaisesRegex(OSError, 'simulated partial write'):
                    publishing.build(root)
            self.assertEqual(latest.read_bytes(), original)
            self.assertFalse(list(latest.parent.glob('.latest.json.*.tmp')))

    def test_failure_before_replace_preserves_selector_and_retained_evidence(self):
        for failure in ('fsync', 'replace'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                latest = self.fixture(root)
                publishing.build(root)
                before = {p: p.read_bytes() for p in latest.parent.rglob('*') if p.is_file()}
                snapshot = root / 'docs/data/snapshot.json'
                value = json.loads(snapshot.read_bytes())
                value['published_at'] = '2026-11-04T12:00:00+00:00'
                snapshot.write_text(json.dumps(value), encoding='utf-8')

                def fail(*args):
                    self.assertEqual(latest.read_bytes(), before[latest])
                    stages = list(latest.parent.glob('.latest.json.*.tmp'))
                    self.assertEqual(len(stages), 1)
                    candidate = json.loads(stages[0].read_bytes())
                    self.assertTrue((latest.parent / 'releases' /
                                     (candidate['release_id'] + '.json')).is_file())
                    self.assertTrue((latest.parent / 'boundaries' /
                                     (candidate['boundary_version'] + '.json')).is_file())
                    for area in candidate['areas']:
                        self.assertTrue((latest.parent / 'releases' / candidate['release_id'] /
                                         (area['id'] + '.json')).is_file())
                    raise OSError('simulated pre-replacement failure')

                with patch.object(publishing.os, failure, side_effect=fail):
                    with self.assertRaisesRegex(OSError, 'simulated pre-replacement failure'):
                        publishing.build(root)
                for path, content in before.items():
                    self.assertEqual(path.read_bytes(), content)
                self.assertFalse(list(latest.parent.glob('.latest.json.*.tmp')))
                publishing.build(root)
                self.assertNotEqual(latest.read_bytes(), before[latest])

    def test_edges_holes_and_multipart(self):
        outer = [[-79.3,43.7],[-79.2,43.7],[-79.2,43.8],[-79.3,43.8],[-79.3,43.7]]
        hole = [[-79.28,43.72],[-79.22,43.72],[-79.22,43.78],[-79.28,43.78],[-79.28,43.72]]
        geometry = {'type':'Polygon','coordinates':[outer,hole]}
        self.assertTrue(point_in_geometry([-79.3,43.75],geometry))
        self.assertFalse(point_in_geometry([-79.25,43.75],geometry))
        self.assertTrue(point_in_geometry([-79.28,43.75],geometry))
        self.assertTrue(point_in_geometry([-79.25,43.75],{'type':'MultiPolygon','coordinates':[[outer]]}))
        self.assertFalse(point_in_geometry([-79.1,43.75],geometry))

if __name__ == '__main__':
    unittest.main()
