import unittest
from src.dates import inspection_date_label

class DateTests(unittest.TestCase):
    def test_inspection_date_not_collection_date(self):
        r={"inspection_date":"2026-11-11","collected_at":"2026-11-24T09:03:00Z","published_at":"2026-11-23T09:00:00Z"}
        self.assertEqual(inspection_date_label(r), "2026-11-11")
    def test_no_invented_date(self):
        r={"collected_at":"2026-11-24T09:03:00Z","published_at":"2026-11-23T09:00:00Z"}
        self.assertEqual(inspection_date_label(r), "Inspection date unavailable")
    def test_empty_inspection_date(self):
        self.assertEqual(inspection_date_label({"inspection_date":"","last_refreshed":"2026-11-24"}),"Inspection date unavailable")
