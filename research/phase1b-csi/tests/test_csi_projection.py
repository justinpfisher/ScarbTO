from __future__ import annotations

import copy
import unittest
from datetime import datetime, time, timezone

import csi_adapter as csi
import csi_projection as projection
from test_csi_adapter import fixture_rows, pages_from, version


class CsiProjectionTests(unittest.TestCase):
    registry = {"109": "Synthetic Area A", "159": "Synthetic Area B", "174": "Synthetic Area C"}

    def grouped_response(self, groups, total=None, *, quarter_coverage=True, quarter="2025-Q4"):
        source_version = version(fixture_rows())
        year, q = map(int, quarter.split("-Q"))
        first_month = (q - 1) * 3 + 1
        start_date = datetime(year, first_month, 1).date()
        if q == 4:
            next_date = datetime(year + 1, 1, 1).date()
        else:
            next_date = datetime(year, first_month + 3, 1).date()
        start = datetime.combine(start_date, time.min, tzinfo=csi.TORONTO).astimezone(timezone.utc)
        end = datetime.combine(next_date, time.min, tzinfo=csi.TORONTO).astimezone(timezone.utc)
        start_sql = start.strftime("%Y-%m-%d %H:%M:%S")
        end_sql = end.strftime("%Y-%m-%d %H:%M:%S")
        where = f"REPORT_DATE >= TIMESTAMP '{start_sql}' AND REPORT_DATE < TIMESTAMP '{end_sql}'"
        metadata = {
            "service_item_id": source_version.service_item_id,
            "layer_id": source_version.layer_id,
            "layer_name": source_version.layer_name,
            "edit_date_utc": source_version.edit_date_utc,
            "schema_sha256": source_version.schema_sha256,
            "coverage_start_date": "2025-10-01" if quarter_coverage else "2025-10-02",
            "coverage_end_date": "2025-12-31",
            "coverage_basis": "published_extract_metadata",
            "queried_at_utc": "2026-10-27T12:00:00Z",
        }
        metadata_after = dict(metadata, queried_at_utc="2026-10-27T12:00:05Z")
        if total is None:
            total = sum(row["attributes"]["source_record_count"] for row in groups)
        fields = [
            {"name": "HOOD_158", "type": "esriFieldTypeString", "alias": "HOOD_158"},
            {"name": "CSI_CATEGORY", "type": "esriFieldTypeString", "alias": "CSI_CATEGORY"},
            {"name": "source_record_count", "type": "esriFieldTypeInteger", "alias": "source_record_count"},
        ]
        return {
            "metadata_before": metadata,
            "metadata_after": metadata_after,
            "count_before": total,
            "count_after": total,
            "query_bounds": {
                "report_quarter": quarter,
                "start_utc": start.isoformat().replace("+00:00", "Z"),
                "end_utc": end.isoformat().replace("+00:00", "Z"),
                "count_before_where": where,
                "statistics_where": where,
                "count_after_where": where,
            },
            "statistics_response": {
                "objectIdFieldName": "",
                "globalIdFieldName": "",
                "geometryType": None,
                "spatialReference": {"wkid": 4326, "latestWkid": 4326},
                "displayFieldName": "",
                "fieldAliases": {field["name"]: field["alias"] for field in fields},
                "fields": fields,
                "hasZ": False,
                "hasM": False,
                "features": copy.deepcopy(groups),
                "exceededTransferLimit": False,
            },
        }

    @staticmethod
    def group(code, category, count):
        return {"attributes": {
            "HOOD_158": code,
            "CSI_CATEGORY": category,
            "source_record_count": count,
        }}

    def build(self, groups, registry=None, **kwargs):
        return projection.build_projection_candidate(
            self.grouped_response(groups, **kwargs),
            neighbourhood_registry=registry or self.registry,
        )

    def test_grouped_statistics_emit_fixed_grid_with_separate_code_and_name(self):
        output = self.build([
            self.group("109", "Assault", 2),
            self.group("NSA", "Assault", 1),
        ])
        self.assertEqual(len(output["cells"]), 3 * len(csi.KNOWN_CSI_CATEGORIES))
        self.assertEqual({cell["neighbourhood_code"] for cell in output["cells"]}, set(self.registry))
        self.assertEqual({cell["neighbourhood"] for cell in output["cells"]}, set(self.registry.values()))
        self.assertIn("Contains information licensed under the Open Government Licence", output["attribution"])
        self.assertEqual(output["publication_status"], "disabled_pending_verified_neighbourhood_registry_and_privacy_review")
        self.assertEqual({cell["report_quarter"] for cell in output["cells"]}, {"2025-Q4"})

    def test_arcgis_statistics_headers_are_validated_without_allowing_geometry_or_ids(self):
        accepted = self.grouped_response([self.group("109", "Assault", 1)])
        self.assertEqual(
            projection.build_projection_candidate(accepted, neighbourhood_registry=self.registry)["cells"][0]["report_quarter"],
            "2025-Q4",
        )
        for field, value, message in (
            ("geometryType", "esriGeometryPoint", "geometry"),
            ("spatialReference", {"wkid": 3857}, "spatial reference"),
            ("objectIdFieldName", "OBJECTID", "identifies source records"),
            ("globalIdFieldName", "GlobalID", "identifies source records"),
        ):
            candidate = copy.deepcopy(accepted)
            candidate["statistics_response"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(csi.ContractError, message):
                projection.build_projection_candidate(candidate, neighbourhood_registry=self.registry)
        candidate = copy.deepcopy(accepted)
        candidate["statistics_response"]["features"][0]["geometry"] = {"x": -79, "y": 43}
        with self.assertRaisesRegex(csi.ContractError, "unexpected fields"):
            projection.build_projection_candidate(candidate, neighbourhood_registry=self.registry)

    def test_query_controls_and_statistics_share_derived_toronto_quarter(self):
        response = self.grouped_response([self.group("109", "Assault", 1)])
        self.assertEqual(response["query_bounds"]["start_utc"], "2025-10-01T04:00:00Z")
        self.assertEqual(response["query_bounds"]["end_utc"], "2026-01-01T05:00:00Z")
        candidate = projection.build_projection_candidate(response, neighbourhood_registry=self.registry)
        self.assertEqual({cell["report_quarter"] for cell in candidate["cells"]}, {"2025-Q4"})
        for key in ("count_before_where", "statistics_where", "count_after_where"):
            altered = copy.deepcopy(response)
            altered["query_bounds"][key] = "REPORT_DATE >= TIMESTAMP '2026-07-01 04:00:00' AND REPORT_DATE < TIMESTAMP '2026-10-01 04:00:00'"
            with self.subTest(key=key), self.assertRaisesRegex(csi.ContractError, "different quarter bounds"):
                projection.build_projection_candidate(altered, neighbourhood_registry=self.registry)

    def test_identical_groups_cannot_be_relabelled_to_another_covered_quarter(self):
        response = self.grouped_response([self.group("109", "Assault", 1)])
        response["query_bounds"]["report_quarter"] = "2026-Q3"
        with self.assertRaisesRegex(csi.ContractError, "does not match its Toronto report quarter"):
            projection.build_projection_candidate(response, neighbourhood_registry=self.registry)

    def test_four_is_banded_five_is_exact_and_empty_groups_are_zero(self):
        four = self.build([self.group("109", "Assault", 4)])
        five = self.build([self.group("109", "Assault", 5)])
        cell4 = next(c for c in four["cells"] if c["neighbourhood_code"] == "109" and c["category"] == "Assault")
        cell5 = next(c for c in five["cells"] if c["neighbourhood_code"] == "109" and c["category"] == "Assault")
        absent = next(c for c in five["cells"] if c["neighbourhood_code"] == "159" and c["category"] == "Robbery")
        self.assertEqual(cell4["count"], "0-4")
        self.assertEqual(cell5["count"], 5)
        self.assertEqual(absent["count"], "0-4")

    def test_codes_are_registry_membership_not_consecutive_numeric_range(self):
        output = self.build([self.group("174", "Assault", 1)])
        self.assertTrue(all(c["neighbourhood"] == "Synthetic Area C" for c in output["cells"] if c["neighbourhood_code"] == "174"))
        with self.assertRaisesRegex(csi.ContractError, "unregistered HOOD_158"):
            self.build([self.group("001", "Assault", 1)])

    def test_duplicate_unknown_and_malformed_group_statistics_reject(self):
        with self.assertRaisesRegex(csi.ContractError, "Duplicate neighbourhood"):
            self.build([
                self.group("109", "Assault", 1),
                self.group("109", "Assault", 1),
            ])
        with self.assertRaisesRegex(csi.ContractError, "unknown CSI category"):
            self.build([self.group("109", "Other", 1)])
        with self.assertRaisesRegex(csi.ContractError, "unexpected fields"):
            self.build([{"attributes": {"HOOD_158": "109", "CSI_CATEGORY": "Assault", "source_record_count": 1, "OBJECTID": 5}}])

    def test_duplicate_nsa_groups_are_rejected_before_unassigned_exclusion(self):
        response = self.grouped_response([
            self.group("NSA", "Assault", 1),
            self.group("NSA", "Assault", 1),
        ])
        with self.assertRaisesRegex(csi.ContractError, "Duplicate neighbourhood/category"):
            projection.build_projection_candidate(response, neighbourhood_registry=self.registry)

    def test_zero_count_groups_are_rejected_but_coherent_empty_response_is_valid(self):
        with self.assertRaisesRegex(csi.ContractError, "counts must be positive"):
            self.build([self.group("109", "Assault", 0)])
        empty = projection.build_projection_candidate(
            self.grouped_response([], total=0),
            neighbourhood_registry=self.registry,
        )
        self.assertEqual(len(empty["cells"]), len(self.registry) * len(csi.KNOWN_CSI_CATEGORIES))
        self.assertEqual({cell["count"] for cell in empty["cells"]}, {"0-4"})

    def test_group_totals_and_source_version_must_stay_stable(self):
        response = self.grouped_response([self.group("109", "Assault", 2)])
        response["count_after"] = 3
        with self.assertRaisesRegex(csi.ContractError, "count changed"):
            projection.build_projection_candidate(response, neighbourhood_registry=self.registry)
        response = self.grouped_response([self.group("109", "Assault", 2)])
        response["metadata_after"]["edit_date_utc"] = "changed"
        with self.assertRaisesRegex(csi.ContractError, "metadata changed"):
            projection.build_projection_candidate(response, neighbourhood_registry=self.registry)

    def test_transfer_limited_statistics_response_is_rejected(self):
        response = self.grouped_response([self.group("109", "Assault", 1)])
        response["statistics_response"]["exceededTransferLimit"] = True
        with self.assertRaisesRegex(csi.ContractError, "transfer-limited"):
            projection.build_projection_candidate(response, neighbourhood_registry=self.registry)

    def test_unavailable_quarter_and_partial_coverage_rejected(self):
        response = self.grouped_response([self.group("109", "Assault", 1)], quarter_coverage=False)
        with self.assertRaisesRegex(csi.ContractError, "incomplete"):
            projection.build_projection_candidate(response, neighbourhood_registry=self.registry)

    def test_recursive_allowlist_rejects_extra_root_source_or_cell_fields(self):
        output = self.build([self.group("109", "Assault", 1)])
        for path in ("root", "source", "cell"):
            candidate = copy.deepcopy(output)
            if path == "root":
                candidate["exact_nsa_total"] = 1
            elif path == "source":
                candidate["source"]["private"] = "forbidden"
            else:
                candidate["cells"][0]["raw_count"] = 1
            with self.subTest(path=path), self.assertRaisesRegex(csi.ContractError, "unexpected"):
                projection._validate_projection_keys(candidate)

    def test_raw_snapshot_rows_are_not_accepted_as_statistics(self):
        rows = fixture_rows()
        source_version = version(rows)
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        with self.assertRaisesRegex(csi.ContractError, "unexpected envelope"):
            projection.build_projection_candidate(validated, neighbourhood_registry=self.registry)

    def test_registry_requires_zero_padded_unique_codes_and_names(self):
        with self.assertRaisesRegex(csi.ContractError, "three-digit"):
            self.build([], {"1": "Synthetic"}, total=0)
        with self.assertRaisesRegex(csi.ContractError, "unique"):
            self.build([], {"109": "Same", "159": "same"}, total=0)


if __name__ == "__main__":
    unittest.main()


