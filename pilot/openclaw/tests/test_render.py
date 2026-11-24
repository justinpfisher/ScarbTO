import unittest
from src.render import summary_cards

class RenderTests(unittest.TestCase):
    def test_factual_synthetic_summary(self):
        records=[
          {"source_id":"A","area":"westrouge","inspection_date":"2026-11-11","collected_at":"2026-11-24T06:00:00Z","outcome":"Pass"},
          {"source_id":"A","area":"westrouge","inspection_date":"2026-11-11","collected_at":"2026-11-24T06:00:00Z","outcome":"Pass"},
          {"source_id":"B","area":"Highland Creek","collected_at":"2026-11-24T06:00:00Z","outcome":"Conditional Pass"},
          {"source_id":"C","area":"Unverified Area","inspection_date":"2026-11-10","outcome":"Closed"}
        ]
        self.assertEqual(summary_cards(records),[
          {"source_id":"A","area":"West Rouge","inspection_date":"2026-11-11","outcome":"Pass"},
          {"source_id":"B","area":"Highland Creek","inspection_date":"Inspection date unavailable","outcome":"Conditional Pass"}
        ])
    def test_empty(self):
        self.assertEqual(summary_cards([]),[])
