from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import csi_adapter as csi


ROOT = Path(__file__).resolve().parents[1]


def fixture_rows() -> list[dict]:
    fixture = json.loads((ROOT / "fixtures" / "rows.synthetic.json").read_text(encoding="utf-8"))
    assert fixture["fixture_status"].startswith("synthetic")
    assert fixture["source"] == csi.SOURCE_NAME
    return fixture["rows"]


def layer_metadata() -> dict:
    return json.loads((ROOT / "fixtures" / "layer-metadata.checked.json").read_text(encoding="utf-8"))


def version(rows: list[dict] | None = None, **overrides) -> csi.SourceVersion:
    rows = rows if rows is not None else fixture_rows()
    metadata = layer_metadata()
    field_types = {
        name: field_type
        for name, field_type in metadata["query_field_types"].items()
        if name in rows[0]
    }
    values = {
        "service_item_id": metadata["service_item_id"],
        "layer_id": metadata["layer_id"],
        "layer_name": metadata["layer_name"],
        "edit_date_utc": metadata["last_edit_date_utc"],
        "schema_sha256": csi.schema_signature(rows[0].keys()),
        "field_types": field_types,
        "max_record_count": metadata["max_record_count"],
        "supports_pagination": metadata["supports_pagination"],
        "supports_order_by": metadata["supports_order_by"],
        "date_fields_time_zone_iana": metadata["date_fields_time_zone_iana"],
        "coverage_start_utc": "2014-01-01T00:00:00Z",
        "coverage_end_utc": "2026-09-30T23:59:59Z",
        "queried_at_utc": "2026-10-27T12:00:00Z",
        "expected_total": len(rows),
    }
    values.update(overrides)
    return csi.SourceVersion(**values)


def pages_from(rows: list[dict], page_size: int = 3) -> list[dict]:
    pages = []
    for offset in range(0, len(rows), page_size):
        items = rows[offset : offset + page_size]
        pages.append({
            "offset": offset,
            "requested_count": page_size,
            "order_by_fields": "OBJECTID ASC",
            "features": [{"attributes": row} for row in items],
            "exceeded_transfer_limit": offset + len(items) < len(rows),
        })
    return pages


class CsiContractTests(unittest.TestCase):
    def test_fixture_is_synthetic_and_has_required_current_schema(self):
        rows = fixture_rows()
        metadata = layer_metadata()
        csi.validate_schema(rows[0].keys())
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["EVENT_UNIQUE_ID"], rows[1]["EVENT_UNIQUE_ID"])
        self.assertEqual(rows[0]["EVENT_UNIQUE_ID"], rows[2]["EVENT_UNIQUE_ID"])
        self.assertNotIn("coordinates", json.dumps(rows).casefold())
        self.assertEqual(metadata["metadata_status"], "official ArcGIS layer metadata only; no feature rows")
        self.assertEqual(metadata["max_record_count"], 2000)
        self.assertIs(metadata["supports_pagination"], True)
        self.assertIs(metadata["supports_order_by"], True)
        self.assertEqual(metadata["date_fields_time_zone_iana"], "Etc/UTC")
        self.assertEqual(metadata["query_field_types"]["CSI_CATEGORY"], "esriFieldTypeString")
        self.assertEqual(metadata["query_field_types"]["REPORT_DATE"], "esriFieldTypeDate")
        self.assertEqual(metadata["query_field_types"]["OCC_DATE"], "esriFieldTypeDate")
        self.assertEqual(metadata["query_field_types"]["REPORT_YEAR"], "esriFieldTypeString")
        self.assertEqual(metadata["query_field_types"]["REPORT_MONTH"], "esriFieldTypeString")

    def test_report_year_numeric_mismatch_is_rejected(self):
        rows = fixture_rows()
        rows[0]["REPORT_YEAR"] = 2026
        with self.assertRaisesRegex(csi.ContractError, "REPORT_YEAR value does not match esriFieldTypeString"):
            csi.validate_pages(pages_from(rows), version(rows), version(rows))

    def test_metadata_field_type_mismatch_and_non_utc_timezone_fail_closed(self):
        rows = fixture_rows()
        types = dict(layer_metadata()["query_field_types"])
        types["CSI_CATEGORY"] = "esriFieldTypeInteger"
        with self.assertRaisesRegex(csi.ContractError, "CSI field type mismatch"):
            version(rows, field_types=types).validate()
        with self.assertRaisesRegex(csi.ContractError, "not Etc/UTC"):
            version(rows, date_fields_time_zone_iana="America/New_York").validate()

    def test_missing_selected_field_type_fails_closed(self):
        types = dict(layer_metadata()["query_field_types"])
        del types["REPORT_YEAR"]
        with self.assertRaisesRegex(csi.ContractError, "missing required field types"):
            version(field_types=types).validate()

    def test_contiguous_pages_accept_repeated_event_ids_but_unique_objectids(self):
        rows = fixture_rows()
        validated = csi.validate_pages(pages_from(rows), version(rows), version(rows))
        self.assertEqual(len(validated), len(rows))
        self.assertEqual(len({r["EVENT_UNIQUE_ID"] for r in validated}), 3)

    def test_missing_current_csi_category_fails_closed(self):
        rows = fixture_rows()
        for row in rows:
            row.pop("CSI_CATEGORY")
        with self.assertRaisesRegex(csi.ContractError, "CSI_CATEGORY"):
            csi.validate_pages(pages_from(rows), version(rows), version(rows))

    def test_duplicate_snapshot_objectid_across_pages_fails(self):
        rows = fixture_rows()
        rows[3]["OBJECTID"] = rows[0]["OBJECTID"]
        with self.assertRaisesRegex(csi.ContractError, "Duplicate OBJECTID"):
            csi.validate_pages(pages_from(rows), version(rows), version(rows))

    def test_stable_objectid_order_is_required_and_checked(self):
        rows = fixture_rows()
        pages = pages_from(rows)
        pages[0]["order_by_fields"] = ""
        with self.assertRaisesRegex(csi.ContractError, "stable OBJECTID ASC"):
            csi.validate_pages(pages, version(rows), version(rows))

        rows = fixture_rows()
        rows[2]["OBJECTID"] = 99
        with self.assertRaisesRegex(csi.ContractError, "strictly ascending"):
            csi.validate_pages(pages_from(rows), version(rows), version(rows))

    def test_fractional_and_boolean_pagination_values_are_rejected(self):
        rows = fixture_rows()
        pages = pages_from(rows)
        pages[0]["offset"] = False
        with self.assertRaisesRegex(csi.ContractError, "contiguous"):
            csi.validate_pages(pages, version(rows), version(rows))

        pages = pages_from(rows)
        pages[0]["features"][0]["attributes"]["OBJECTID"] = 101.5
        with self.assertRaisesRegex(csi.ContractError, "integer snapshot OBJECTID"):
            csi.validate_pages(pages, version(rows), version(rows))

    def test_nonrequired_source_field_drift_between_rows_fails(self):
        rows = fixture_rows()
        rows[4].pop("OFFENCE")
        with self.assertRaisesRegex(csi.ContractError, "row schema changed"):
            csi.validate_pages(pages_from(rows), version(rows), version(rows))

    def test_missing_page_and_unexpected_short_or_more_pages_fail(self):
        rows = fixture_rows()
        missing_tail = pages_from(rows)[:1]
        missing_tail[0]["exceeded_transfer_limit"] = False
        with self.assertRaisesRegex(csi.ContractError, "Incomplete CSI pagination"):
            csi.validate_pages(missing_tail, version(rows), version(rows))

        pages = pages_from(rows)
        pages[0]["exceeded_transfer_limit"] = False
        with self.assertRaisesRegex(csi.ContractError, "continued after source"):
            csi.validate_pages(pages, version(rows), version(rows))

        pages = pages_from(rows)
        pages[0]["features"].pop()
        with self.assertRaisesRegex(csi.ContractError, "short"):
            csi.validate_pages(pages, version(rows), version(rows))

    def test_source_version_change_during_pagination_fails(self):
        rows = fixture_rows()
        before = version(rows)
        after = version(rows, edit_date_utc="2026-10-09T12:00:00Z")
        with self.assertRaisesRegex(csi.ContractError, "source version changed"):
            csi.validate_pages(pages_from(rows), before, after)

    def test_empty_source_count_fails_closed(self):
        with self.assertRaisesRegex(csi.ContractError, "Invalid source pagination metadata"):
            version(expected_total=0).validate()

    def test_naive_or_non_utc_dates_are_rejected(self):
        with self.assertRaisesRegex(csi.ContractError, "explicit UTC offset"):
            csi.parse_utc("2026-01-01T00:00:00", "REPORT_DATE")
        with self.assertRaisesRegex(csi.ContractError, "must be UTC"):
            csi.parse_utc("2026-01-01T00:00:00-05:00", "REPORT_DATE")

    def test_invalid_or_out_of_coverage_dates_fail_even_on_unaggregated_rows(self):
        rows = fixture_rows()
        rows[4]["REPORT_DATE"] = "not-a-timestamp"
        with self.assertRaisesRegex(csi.ContractError, "Invalid UTC REPORT_DATE"):
            csi.build_aggregate_candidate(rows, version(rows))

        rows = fixture_rows()
        rows[4]["REPORT_DATE"] = "2013-12-31T23:59:59Z"
        with self.assertRaisesRegex(csi.ContractError, "outside the reported source coverage"):
            csi.build_aggregate_candidate(rows, version(rows))

    def test_utc_to_toronto_month_boundary_is_explicit_and_aggregated(self):
        rows = fixture_rows()
        validated = csi.validate_pages(pages_from(rows), version(rows), version(rows))
        candidate = csi.build_aggregate_candidate(validated, version(rows))
        assault = next(cell for cell in candidate["cells"] if cell["category"] == "Assault")
        # 2025-12-31 23:40Z is still December in Toronto. Repeated rows remain
        # two source rows but count one distinct occurrence for this category.
        self.assertEqual(assault["occurrence_month_toronto"], "2025-12")
        self.assertEqual(assault["source_row_count"], 2)
        self.assertEqual(assault["distinct_occurrence_ids"], 1)
        self.assertEqual(candidate["report_date_min_utc"], "2026-01-01")
        self.assertEqual(candidate["occurrence_date_min_utc"], "2025-12-31")

    def test_same_occurrence_in_two_categories_counts_once_per_category(self):
        rows = fixture_rows()
        candidate = csi.build_aggregate_candidate(rows, version(rows))
        cells = [cell for cell in candidate["cells"] if cell["neighbourhood"] == "Synthetic Area 1"]
        event_counts = {cell["category"]: cell["distinct_occurrence_ids"] for cell in cells}
        self.assertEqual(event_counts["Assault"], 1)
        self.assertEqual(event_counts["Theft Over"], 1)

    def test_candidate_contains_aggregates_only_and_public_export_is_disabled(self):
        rows = fixture_rows()
        candidate = csi.build_aggregate_candidate(rows, version(rows))
        encoded = json.dumps(candidate)
        for forbidden in csi.FORBIDDEN_PUBLIC_FIELDS:
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(candidate["publication_status"], "disabled_pending_privacy_review")
        self.assertTrue(any("no sparse-cell threshold" in text for text in candidate["limitations"]))
        with self.assertRaises(csi.PublicExportDisabled):
            csi.export_public(candidate)

    def test_report_quarter_uses_toronto_calendar_and_counts_source_records(self):
        rows = fixture_rows()
        rows[3]["REPORT_DATE"] = "2025-12-31T23:59:59Z"
        rows[3]["REPORT_YEAR"] = "2025"
        rows[3]["REPORT_MONTH"] = "December"
        source_version = version(rows)
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        candidate = csi.build_report_quarter_candidate(validated, source_version)

        self.assertEqual(candidate["publication_status"], "disabled_pending_privacy_review")
        self.assertEqual(candidate["source_record_total"], 5)
        self.assertEqual(candidate["aggregated_source_record_total"], 4)
        self.assertEqual(candidate["unaggregated_rows"], 1)
        self.assertEqual(candidate["incomplete_quarter_rows"], 0)
        by_quarter: dict[str, int] = {}
        for cell in candidate["cells"]:
            by_quarter[cell["report_quarter"]] = (
                by_quarter.get(cell["report_quarter"], 0) + cell["source_record_count"]
            )
        # 00:15Z on January 1 is still December 31 in Toronto, so all
        # aggregatable rows belong to 2025-Q4 (not UTC 2026-Q1).
        self.assertEqual(by_quarter["2025-Q4"], 4)
        self.assertNotIn("2026-Q1", by_quarter)
        self.assertEqual(candidate["observed_report_date_min_utc"], "2025-12-31")
        self.assertEqual(candidate["observed_report_date_max_utc"], "2026-01-01")
        serialized = json.dumps(candidate)
        for forbidden in csi.FORBIDDEN_PUBLIC_FIELDS:
            self.assertNotIn(forbidden, serialized)
        self.assertNotIn("2025-12-31T23:59:59", serialized)
        with self.assertRaises(csi.PublicExportDisabled):
            csi.export_public(candidate)

    def test_partial_report_quarter_is_excluded_not_presented_as_complete(self):
        rows = fixture_rows()
        rows[0]["REPORT_DATE"] = "2026-10-10T10:00:00Z"
        rows[0]["REPORT_YEAR"] = "2026"
        rows[0]["REPORT_MONTH"] = "October"
        source_version = version(rows, coverage_end_utc="2026-10-10T23:59:59Z")
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        candidate = csi.build_report_quarter_candidate(validated, source_version)

        self.assertEqual(candidate["source_record_total"], 5)
        self.assertEqual(candidate["incomplete_quarter_rows"], 1)
        self.assertEqual(candidate["aggregated_source_record_total"], 3)
        self.assertNotIn("2026-Q4", {cell["report_quarter"] for cell in candidate["cells"]})

    def test_toronto_quarter_boundary_accounts_for_utc_offset(self):
        before = csi.parse_utc("2026-01-01T04:59:59Z", "test report date")
        at = csi.parse_utc("2026-01-01T05:00:00Z", "test report date")
        self.assertEqual(csi._quarter_for_toronto(before), (2025, 4))
        self.assertEqual(csi._quarter_for_toronto(at), (2026, 1))

    def test_partial_last_coverage_day_does_not_complete_quarter(self):
        rows = fixture_rows()
        rows[0]["REPORT_DATE"] = "2026-02-10T12:00:00Z"
        source_version = version(rows, coverage_end_utc="2026-03-31T00:00:00Z")
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        candidate = csi.build_report_quarter_candidate(validated, source_version)

        self.assertEqual(candidate["incomplete_quarter_rows"], 1)
        self.assertEqual(candidate["aggregated_source_record_total"], 3)
        self.assertNotIn("2026-Q1", {cell["report_quarter"] for cell in candidate["cells"]})

    def test_partial_first_coverage_instant_does_not_complete_quarter(self):
        rows = fixture_rows()
        rows[0]["REPORT_DATE"] = "2026-04-01T04:00:00Z"
        source_version = version(rows, coverage_start_utc="2025-10-01T04:00:01Z")
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        candidate = csi.build_report_quarter_candidate(validated, source_version)

        self.assertEqual(candidate["incomplete_quarter_rows"], 3)
        self.assertEqual(candidate["aggregated_source_record_total"], 1)
        self.assertEqual(
            {cell["report_quarter"] for cell in candidate["cells"]}, {"2026-Q2"}
        )

    def test_report_quarter_rejects_unvalidated_or_wrong_version_rows(self):
        rows = fixture_rows()
        source_version = version(rows)
        with self.assertRaisesRegex(csi.ContractError, "paged validated snapshot"):
            csi.build_report_quarter_candidate(rows, source_version)
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        other_version = version(rows, edit_date_utc="2026-10-09T12:00:00Z")
        with self.assertRaisesRegex(csi.ContractError, "different source version"):
            csi.build_report_quarter_candidate(validated, other_version)

    def test_report_quarter_rechecks_snapshot_objectids_after_validation(self):
        rows = fixture_rows()
        source_version = version(rows)
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        # A caller can mutate the list after validation; the aggregation
        # boundary must not count the same source record twice.
        validated[1]["OBJECTID"] = validated[0]["OBJECTID"]
        with self.assertRaisesRegex(csi.ContractError, "duplicate or invalid OBJECTID"):
            csi.build_report_quarter_candidate(validated, source_version)

    def test_nsa_is_unaggregated_in_both_internal_candidates(self):
        rows = fixture_rows()
        rows[0]["NEIGHBOURHOOD_158"] = "NSA"
        source_version = version(rows)
        month_candidate = csi.build_aggregate_candidate(rows, source_version)
        self.assertFalse(any(cell["neighbourhood"] == "NSA" for cell in month_candidate["cells"]))
        self.assertEqual(month_candidate["unaggregated_rows"], 2)

        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        quarter_candidate = csi.build_report_quarter_candidate(validated, source_version)
        self.assertFalse(any(cell["neighbourhood"] == "NSA" for cell in quarter_candidate["cells"]))
        self.assertEqual(quarter_candidate["unaggregated_rows"], 2)

    def test_unknown_csi_categories_fail_closed(self):
        rows = fixture_rows()
        rows[0]["CSI_CATEGORY"] = "Synthetic Unknown Category"
        source_version = version(rows)
        with self.assertRaisesRegex(csi.ContractError, "Unknown CSI category"):
            csi.build_aggregate_candidate(rows, source_version)
        validated = csi.validate_pages(pages_from(rows), source_version, source_version)
        with self.assertRaisesRegex(csi.ContractError, "Unknown CSI category"):
            csi.build_report_quarter_candidate(validated, source_version)

    def test_null_source_fields_are_counted_as_unaggregated_not_fabricated(self):
        rows = fixture_rows()
        candidate = csi.build_aggregate_candidate(rows, version(rows))
        self.assertEqual(candidate["source_rows"], 5)
        self.assertEqual(candidate["unaggregated_rows"], 1)
        self.assertEqual(sum(c["source_row_count"] for c in candidate["cells"]), 4)

    def test_all_unaggregatable_rows_refuse_an_empty_candidate(self):
        rows = fixture_rows()
        for row in rows:
            row["NEIGHBOURHOOD_158"] = None
        with self.assertRaisesRegex(csi.ContractError, "refuse an empty candidate"):
            csi.build_aggregate_candidate(rows, version(rows))

    def test_atomic_candidate_write_preserves_last_good_on_replace_failure(self):
        rows = fixture_rows()
        candidate = csi.build_aggregate_candidate(rows, version(rows))
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temp:
            target = Path(temp) / "candidate.json"
            target.write_text('{"last_good":true}\n', encoding="utf-8")
            before = target.read_bytes()
            with patch.object(csi.os, "replace", side_effect=OSError("synthetic replace failure")):
                with self.assertRaisesRegex(OSError, "synthetic replace failure"):
                    csi.write_candidate_atomically(target, candidate)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(list(Path(temp).glob("*.tmp")), [])
            self.assertEqual(list(Path(temp).glob(".*.tmp")), [])

    def test_atomic_candidate_write_replaces_only_after_candidate_is_ready(self):
        rows = fixture_rows()
        candidate = csi.build_aggregate_candidate(rows, version(rows))
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as temp:
            target = Path(temp) / "candidate.json"
            target.write_text('{"last_good":true}\n', encoding="utf-8")
            csi.write_candidate_atomically(target, candidate)
            written = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(written["publication_status"], "disabled_pending_privacy_review")
            self.assertFalse(list(Path(temp).glob(".*.tmp")))


if __name__ == "__main__":
    unittest.main()

