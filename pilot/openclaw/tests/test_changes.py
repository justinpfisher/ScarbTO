import unittest
from src.changes import unique_events

class ChangeTests(unittest.TestCase):
    def test_dedupe_exact_event_preserve_variations(self):
        a={"source_id":"A","inspection_date":"2026-11-12","outcome":"Pass"}
        b={"source_id":"A","inspection_date":"2026-11-12","outcome":"Conditional Pass"}
        c={"source_id":"B","inspection_date":"2026-11-12","outcome":"Pass"}
        self.assertEqual(unique_events([a,a.copy(),b,c,a]),[a,b,c])
    def test_empty(self):
        self.assertEqual(unique_events([]),[])
