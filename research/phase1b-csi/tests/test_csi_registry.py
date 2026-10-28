from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from csi_registry import EXPECTED_SELECTED, RegistryError, load_verified_registry


CONTRACT = Path(__file__).parents[1] / "fixtures" / "official-source-contract" / "scarbto-neighbourhood158-source-contract-2026-10-27.json"


class VerifiedRegistryTests(unittest.TestCase):
    def test_hash_pinned_registry_and_crosswalk_load_exactly(self):
        registry = load_verified_registry(CONTRACT)
        self.assertEqual(len(registry.by_code), 158)
        self.assertEqual(registry.source_effective_date, "2022-04-12")
        self.assertEqual(registry.scarborough_codes, EXPECTED_SELECTED)
        self.assertEqual(len(registry.scarborough_codes), 30)
        self.assertEqual(registry.sha256, "0f16bf16cde47f382f21003050a978251f71c258581746d64c9a8c9f5ae8564e")

    def test_valid_three_digit_codes_are_exact_registry_members_not_a_numeric_range(self):
        registry = load_verified_registry(CONTRACT)
        for code in ("109", "159", "174"):
            self.assertIn(code, registry.by_code)
        self.assertNotIn("014", registry.by_code)
        self.assertEqual(registry.lookup_tps_code("014")["state"], "unknown_code")

    def test_join_uses_padded_code_and_preserves_display_name_difference(self):
        registry = load_verified_registry(CONTRACT)
        correct = registry.lookup_tps_code("001", "West Humber-Clairville")
        self.assertEqual(correct["state"], "matched")
        mismatch = registry.lookup_tps_code("001", "West Humber Clairville")
        self.assertEqual(mismatch["state"], "code_matched_name_differs_or_missing")
        self.assertEqual(mismatch["registry_name"], "West Humber-Clairville")
        self.assertEqual(mismatch["publisher_name"], "West Humber Clairville")
        self.assertEqual(registry.lookup_tps_code("1")["state"], "unassigned_or_invalid")
        self.assertEqual(registry.lookup_tps_code("NSA")["state"], "unassigned_or_invalid")

    def test_contract_bytes_are_pinned_before_json_or_registry_use(self):
        raw = CONTRACT.read_bytes()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[1]) as folder:
            candidate = Path(folder) / "tampered.json"
            candidate.write_bytes(raw + b" ")
            with self.assertRaisesRegex(RegistryError, "size or SHA-256"):
                load_verified_registry(candidate)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), "0f16bf16cde47f382f21003050a978251f71c258581746d64c9a8c9f5ae8564e")


if __name__ == "__main__":
    unittest.main()
