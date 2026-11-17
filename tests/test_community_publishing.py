import unittest
import tempfile
from pathlib import Path
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
