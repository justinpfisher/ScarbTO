from __future__ import annotations

import copy
import json
import unittest

import csi_adapter as csi
import csi_projection as projection
from test_csi_adapter import fixture_rows, pages_from, version


class CsiProjectionTests(unittest.TestCase):
    def make_rows(self, count: int = 2):
        base = fixture_rows()[0]
        rows = []
        for index in range(count):
            row = copy.deepcopy(base)
            row["OBJECTID"] = 501 + index
            row["EVENT_UNIQUE_ID"] = f"SYNTH-PROJECTION-{index}"
            row["NEIGHBOURHOOD_158"] = "001"
            rows.append(row)
        return rows

    def build(self, rows, registry=None):
        source_version = version(rows)
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        return projection.build_projection_candidate(
            validated,
            source_version,
            report_quarter="2025-Q4",
            neighbourhood_registry=registry or {"001": "Synthetic Area 1", "002": "Synthetic Area 2"},
        )

    def test_fixed_complete_category_grid_bands_low_cells_and_emits_no_margins(self):
        output = self.build(self.make_rows(2))
        self.assertEqual(len(output["cells"]), 2 * len(csi.KNOWN_CSI_CATEGORIES))
        self.assertEqual(len({(x["neighbourhood_code"], x["category"]) for x in output["cells"]}), 10)
        assault = next(x for x in output["cells"] if x["neighbourhood_code"] == "001" and x["category"] == "Assault")
        zero = next(x for x in output["cells"] if x["neighbourhood_code"] == "002" and x["category"] == "Assault")
        self.assertEqual(assault["count"], "0-4")
        self.assertEqual(zero["count"], "0-4")
        self.assertNotIn("total", output)
        self.assertNotIn("source_record_total", output)
        self.assertNotIn("unaggregated_rows", output)
        self.assertEqual(output["publication_status"], "disabled_pending_verified_neighbourhood_registry_and_privacy_review")
        self.assertNotIn("SYNTH-PROJECTION", json.dumps(output))

    def test_exact_count_starts_at_five_and_grid_is_fixed(self):
        output = self.build(self.make_rows(5), {"001": "Synthetic Area 1"})
        assault = next(x for x in output["cells"] if x["category"] == "Assault")
        zero = next(x for x in output["cells"] if x["category"] == "Auto Theft")
        self.assertEqual(assault["count"], 5)
        self.assertEqual(zero["count"], "0-4")
        self.assertEqual(len(output["cells"]), len(csi.KNOWN_CSI_CATEGORIES))

    def test_nsa_unknown_codes_and_nonvalidated_rows_fail_closed(self):
        rows = self.make_rows(1)
        rows[0]["NEIGHBOURHOOD_158"] = "NSA"
        with self.assertRaisesRegex(csi.ContractError, "No completed-quarter CSI rows"):
            self.build(rows)
        rows = self.make_rows(1)
        rows[0]["NEIGHBOURHOOD_158"] = "159"
        with self.assertRaisesRegex(csi.ContractError, "outside the supplied verified registry"):
            self.build(rows)
        with self.assertRaisesRegex(csi.ContractError, "paged validated snapshot"):
            projection.build_projection_candidate(
                self.make_rows(1), version(self.make_rows(1)), report_quarter="2025-Q4",
                neighbourhood_registry={"001": "Synthetic"},
            )

    def test_registry_requires_zero_padded_unique_codes_and_names(self):
        with self.assertRaisesRegex(csi.ContractError, "zero-padded"):
            self.build(self.make_rows(1), {"1": "Synthetic"})
        with self.assertRaisesRegex(csi.ContractError, "unique"):
            self.build(self.make_rows(1), {"001": "Same", "002": "same"})


if __name__ == "__main__":
    unittest.main()

