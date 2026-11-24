import unittest
from src.areas import canonical_area

class AreaTests(unittest.TestCase):
    def test_exact_and_case_insensitive(self):
        self.assertEqual(canonical_area("West Rouge"), "West Rouge")
        self.assertEqual(canonical_area(" highland creek "), "Highland Creek")
    def test_documented_alias_only(self):
        self.assertEqual(canonical_area("westrouge"), "West Rouge")
        self.assertEqual(canonical_area("west-rouge"), "West Rouge")
        self.assertIsNone(canonical_area("Rouge"))
        self.assertIsNone(canonical_area("South Agincourt"))
    def test_missing(self):
        self.assertIsNone(canonical_area(None))
        self.assertIsNone(canonical_area("  "))
