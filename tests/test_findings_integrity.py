"""Collector findings and code-only integrity remain one strict public contract."""
import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.snapshot_integrity import SnapshotIntegrityError, validate_snapshot_integrity
from scripts.update_dinesafe import normalise

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = "All available source rows for this establishment, date and outcome; the source supplies no inspection identifier."
FIELDS = ['id', 'name', 'address', 'type', 'inspection_detail', 'inspection_findings', 'findings_coverage', 'status', 'inspection_date', 'latitude', 'longitude', 'ward', 'neighbourhood', 'source_url', 'licence_url', 'collected_at']
LEGACY_FIELDS = [field for field in FIELDS if field not in {'inspection_findings', 'findings_coverage'}]


class FindingsIntegrityTests(unittest.TestCase):
    def snapshot(self):
        snapshot = json.loads((ROOT / 'docs/data/snapshot.json').read_text(encoding='utf-8'))
        for row in snapshot['establishments']:
            row.update(inspection_findings=[], findings_coverage=COVERAGE)
        rows = json.loads((ROOT / 'tests/fixtures/namma-findings.json').read_text(encoding='utf-8'))['rows']
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        shape = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'AREA_NAME': 'Scarborough Ward 1'}, 'geometry': {'type': 'Polygon', 'coordinates': [[[-79.5, 43.6], [-79.0, 43.6], [-79.0, 44.0], [-79.5, 44.0], [-79.5, 43.6]]]}}]}
        wards = copy.deepcopy(shape)
        wards['features'] = [dict(copy.deepcopy(shape['features'][0]), properties={'AREA_NAME': f'Scarborough Ward {i}'}) for i in range(1, 7)]
        entries, _, _ = normalise(stream.getvalue().encode(), wards, shape, minimum=1)
        target = next(i for i, row in enumerate(snapshot['establishments']) if row['id'] == entries[0]['id'])
        snapshot['establishments'][target] = entries[0]
        return snapshot, target

    def write(self, root, snapshot):
        (root / 'snapshot.json').write_text(json.dumps(snapshot), encoding='utf-8')
        # Independent export construction matching the collector's public CSV.
        has_findings = bool(snapshot['establishments']) and 'inspection_findings' in snapshot['establishments'][0]
        fields = FIELDS if has_findings else LEGACY_FIELDS
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for entry in snapshot['establishments']:
            row = {key: entry.get(key) for key in fields}
            row.update(source_url='https://open.toronto.ca/dataset/dinesafe/', licence_url='https://open.toronto.ca/open-data-licence/', collected_at=snapshot['published_at'])
            if has_findings:
                row['inspection_findings'] = json.dumps(entry.get('inspection_findings'), ensure_ascii=False, sort_keys=True)
            for key in ('id', 'name', 'address', 'type', 'inspection_detail', 'ward', 'neighbourhood'):
                value = row.get(key)
                if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
                    row[key] = "'" + value
            writer.writerow(row)
        (root / 'establishments.csv').write_bytes(stream.getvalue().encode('utf-8-sig'))

    def test_legacy_snapshot_remains_valid(self):
        snapshot = json.loads((ROOT / 'docs/data/snapshot.json').read_text(encoding='utf-8'))
        for row in snapshot['establishments']:
            row.pop('inspection_findings', None)
            row.pop('findings_coverage', None)
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            self.write(root, snapshot)
            before = {name: (root / name).read_bytes() for name in ('snapshot.json', 'establishments.csv')}
            self.assertGreater(validate_snapshot_integrity(root)['establishments'], 300)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in before})

    def test_collector_five_findings_and_csv_preserved(self):
        snapshot, target = self.snapshot()
        self.assertEqual(len(snapshot['establishments'][target]['inspection_findings']), 5)
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            self.write(root, snapshot)
            before = {name: (root / name).read_bytes() for name in ('snapshot.json', 'establishments.csv')}
            self.assertEqual(validate_snapshot_integrity(root)['establishments'], len(snapshot['establishments']))
            self.assertEqual(before, {name: (root / name).read_bytes() for name in before})

    def test_mixed_partial_and_unknown_entry_schemas_rejected(self):
        original, _ = self.snapshot()
        for mutation in ('legacy', 'partial', 'unknown'):
            snapshot = copy.deepcopy(original)
            row = snapshot['establishments'][1]
            if mutation in ('legacy', 'partial'):
                del row['inspection_findings']
                if mutation == 'legacy':
                    del row['findings_coverage']
            else:
                row['private_extra'] = 'not an allowed public field'
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(dir=ROOT) as temp:
                self.write(Path(temp), snapshot)
                with self.assertRaises(SnapshotIntegrityError):
                    validate_snapshot_integrity(temp)

    def test_malformed_findings_and_coverage_rejected(self):
        original, target = self.snapshot()
        for mutation in ('not-array', 'unknown', 'missing', 'numeric', 'duplicate', 'conflicting-id', 'coverage'):
            snapshot = copy.deepcopy(original)
            row = snapshot['establishments'][target]
            finding = row['inspection_findings'][0]
            if mutation == 'not-array': row['inspection_findings'] = 'not findings'
            elif mutation == 'unknown': finding['private_extra'] = 'x'
            elif mutation == 'missing': del finding['fine']
            elif mutation == 'numeric': finding['fine'] = 25
            elif mutation == 'duplicate': row['inspection_findings'].append(copy.deepcopy(finding))
            elif mutation == 'conflicting-id': row['inspection_findings'][1]['row_id'] = finding['row_id']
            else: row['findings_coverage'] = 'A complete inspection'
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(dir=ROOT) as temp:
                self.write(Path(temp), snapshot)
                with self.assertRaises(SnapshotIntegrityError):
                    validate_snapshot_integrity(temp)

    def test_csv_finding_drift_is_rejected(self):
        snapshot, target = self.snapshot()
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            self.write(root, snapshot)
            snapshot['establishments'][target]['inspection_findings'][0]['wording'] += ' altered'
            (root / 'snapshot.json').write_text(json.dumps(snapshot), encoding='utf-8')
            with self.assertRaisesRegex(SnapshotIntegrityError, 'CSV does not exactly match'):
                validate_snapshot_integrity(root)


if __name__ == '__main__':
    unittest.main()
