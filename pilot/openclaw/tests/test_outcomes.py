import unittest
from src.outcomes import outcome_label

class OutcomeTests(unittest.TestCase):
    def test_exact_source_value(self):
        for status in ("Pass","Conditional Pass","Closed","Pending verification"):
            with self.subTest(status=status):
                self.assertEqual(outcome_label({"outcome":status}),status)
    def test_missing_does_not_become_pass(self):
        self.assertEqual(outcome_label({"typeDesc":"a detail, not an outcome"}),"Outcome unavailable")
        self.assertEqual(outcome_label({"outcome":""}),"Outcome unavailable")
