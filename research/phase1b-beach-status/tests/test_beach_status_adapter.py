from datetime import datetime, timedelta, timezone
import unittest

import beach_status_adapter as beach


NOW = datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)
BEACH_ID = 10


def envelope(day="2026-07-15", **overrides):
    row = {
        "beachId": BEACH_ID,
        "beachName": "Bluffer's Beach Park",
        "eColi": 17,
        "statusFlag": "SAFE",
        "statusFlagPre": None,
        "advisory": None,
    }
    row.update(overrides)
    return {"CollectionDate": day, "data": [row]}


def card(**overrides):
    values = {
        "beach_id": BEACH_ID,
        "beach_name": "Bluffer's Beach Park",
        "in_season": "Yes",
        "last_update_raw": "2026-07-15 10:19:11",
        "result_envelopes": [envelope()],
        "now": NOW,
        "sample_freshness_limit": timedelta(days=2),
        "maintenance_enabled": "N",
    }
    values.update(overrides)
    values.setdefault("control_retrieved_at", {
        name: values["now"] for name in ("season", "last_update", "maintenance", "results")
    })
    return beach.build_status_card(**values)


class BeachStatusTests(unittest.TestCase):
    def test_evaluation_does_not_advance_cached_retrieval_time(self):
        fetched = datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)
        source_controls = {
            "season": fetched, "last_update": fetched,
            "maintenance": fetched, "results": fetched,
        }
        original = card(retrieved_at=fetched, control_retrieved_at=source_controls)
        later = card(
            now=fetched + timedelta(days=4), retrieved_at=fetched,
            control_retrieved_at=source_controls,
        )
        self.assertEqual(original["fetched_at_utc"], later["fetched_at_utc"])
        self.assertEqual(later["display_state"], "season_state_stale")
        self.assertEqual(later["results_fetched_at_utc"], "2026-07-15T16:00:00Z")

    def test_missing_maintenance_control_is_unknown_by_default(self):
        values = {
            "beach_id": BEACH_ID, "beach_name": "Synthetic Beach",
            "in_season": "Yes", "last_update_raw": None,
            "result_envelopes": None, "now": NOW,
            "sample_freshness_limit": timedelta(days=2),
            "control_retrieved_at": {
                name: NOW for name in ("season", "last_update", "maintenance", "results")
            },
        }
        result = beach.build_status_card(**values)
        self.assertEqual(result["display_state"], "maintenance_state_unknown")

    def test_missing_or_old_season_timestamp_never_qualifies_a_current_status(self):
        self.assertEqual(
            card(control_retrieved_at={
                "season": None, "last_update": NOW, "maintenance": NOW, "results": NOW,
            })["display_state"],
            "season_state_stale",
        )
        old = NOW - timedelta(days=100)
        self.assertEqual(
            card(control_retrieved_at={
                "season": old, "last_update": NOW, "maintenance": NOW, "results": NOW,
            })["display_state"],
            "season_state_stale",
        )

    def test_missing_or_old_maintenance_timestamp_never_qualifies_a_current_status(self):
        old = NOW - timedelta(days=100)
        for timestamp in (None, old):
            with self.subTest(timestamp=timestamp):
                self.assertEqual(
                    card(control_retrieved_at={
                        "season": NOW, "last_update": NOW,
                        "maintenance": timestamp, "results": NOW,
                    })["display_state"],
                    "maintenance_state_stale",
                )

    def test_old_result_or_update_control_is_not_presented_as_current(self):
        old = NOW - timedelta(days=100)
        for key in ("last_update", "results"):
            with self.subTest(key=key):
                times = {name: NOW for name in ("season", "last_update", "maintenance", "results")}
                times[key] = old
                self.assertEqual(card(control_retrieved_at=times)["display_state"], "source_controls_stale")

    def test_future_control_retrieval_time_is_rejected(self):
        times = {name: NOW for name in ("season", "last_update", "maintenance", "results")}
        times["season"] = NOW + timedelta(seconds=1)
        with self.assertRaisesRegex(beach.BeachContractError, "cannot be in the future"):
            card(control_retrieved_at=times)

    def test_raw_city_flags_are_preserved(self):
        value = card(result_envelopes=[envelope(statusFlag="SAFE", statusFlagPre="UNSAFE")])
        self.assertEqual(value["raw_status_flag"], "SAFE")
        self.assertEqual(value["raw_status_flag_pre"], "UNSAFE")

    def test_out_of_season_hides_last_seasons_safe_sample(self):
        value = card(in_season="No", result_envelopes=[envelope("2025-09-07")])
        self.assertEqual(value["display_state"], "out_of_season")
        self.assertIsNone(value["water_quality_status"])

    def test_null_results_are_unknown_not_safe(self):
        value = card(result_envelopes=None)
        self.assertEqual(value["display_state"], "no_current_result")
        self.assertIsNone(value["water_quality_status"])

    def test_null_result_data_is_unknown(self):
        value = card(result_envelopes=[{"CollectionDate": "2026-07-15", "data": None}])
        self.assertEqual(value["display_state"], "no_current_result")

    def test_no_matching_beach_id_is_unknown_even_if_name_matches(self):
        value = card(result_envelopes=[envelope(beachId=11)])
        self.assertEqual(value["display_state"], "no_current_result")

    def test_low_ecoli_never_overrides_official_unsafe_flag(self):
        value = card(result_envelopes=[envelope(eColi=1, statusFlag="UNSAFE")])
        self.assertEqual(value["display_state"], "current")
        self.assertEqual(value["water_quality_status"], "caution")

    def test_preliminary_flag_overrides_official_status(self):
        value = card(result_envelopes=[envelope(
            statusFlag="SAFE", statusFlagPre="UNSAFE"
        )])
        self.assertEqual(value["water_quality_status"], "caution")

    def test_unknown_status_fails_closed(self):
        value = card(result_envelopes=[envelope(statusFlag="Looks fine")])
        self.assertEqual(value["display_state"], "status_unrecognized")
        self.assertIsNone(value["water_quality_status"])

    def test_city_data_unavailable_status_is_not_safe(self):
        value = card(result_envelopes=[envelope(statusFlag="NO_DATA")])
        self.assertEqual(value["water_quality_status"], "unavailable")

    def test_maintenance_overrides_status(self):
        value = card(maintenance_enabled="Y")
        self.assertEqual(value["display_state"], "maintenance")
        self.assertIsNone(value["water_quality_status"])

    def test_unknown_maintenance_state_fails_closed(self):
        value = card(maintenance_enabled=None)
        self.assertEqual(value["display_state"], "maintenance_state_unknown")

    def test_numeric_control_values_are_not_coerced_to_booleans(self):
        self.assertEqual(card(in_season=1)["display_state"], "season_state_unknown")
        self.assertEqual(card(maintenance_enabled=0)["display_state"], "maintenance_state_unknown")

    def test_malformed_envelope_and_collection_date_are_rejected(self):
        with self.assertRaisesRegex(beach.BeachContractError, "envelope"):
            card(result_envelopes=[None])
        with self.assertRaisesRegex(beach.BeachContractError, "ISO date"):
            card(result_envelopes=[{"CollectionDate": "2026-07-15T00:00:00Z", "data": []}])

    def test_duplicate_latest_envelopes_are_rejected(self):
        with self.assertRaisesRegex(beach.BeachContractError, "Duplicate result envelopes"):
            card(result_envelopes=[envelope(), envelope(statusFlag="Caution is advised")])

    def test_sample_staleness_uses_toronto_calendar_date(self):
        value = card(result_envelopes=[envelope("2026-07-12")])
        self.assertEqual(value["display_state"], "stale")

    def test_date_only_sample_is_preserved_across_dst(self):
        just_after_dst_transition = datetime(2026, 3, 9, 3, 30, tzinfo=timezone.utc)
        value = card(
            now=just_after_dst_transition,
            result_envelopes=[envelope("2026-03-08")],
            control_retrieved_at={
                name: just_after_dst_transition
                for name in ("season", "last_update", "maintenance", "results")
            },
        )
        self.assertEqual(value["sample_date"], "2026-03-08")
        self.assertEqual(value["display_state"], "current")

    def test_timezone_less_source_update_is_preserved_without_fabricated_utc(self):
        value = card()
        self.assertEqual(value["source_update_raw"], "2026-07-15 10:19:11")
        self.assertIsNone(value["source_updated_at_utc"])

    def test_invalid_update_timestamp_and_nonstring_status_fail_safely(self):
        with self.assertRaisesRegex(beach.BeachContractError, "ISO timestamp"):
            card(last_update_raw="recently")
        value = card(result_envelopes=[envelope(statusFlag=["Safe to swim"])])
        self.assertEqual(value["display_state"], "status_unrecognized")

    def test_latest_collection_date_selected_and_name_does_not_drive_join(self):
        values = [
            envelope("2026-07-14", beachName="Old Name"),
            envelope("2026-07-15", beachName="Renamed by source"),
        ]
        value = card(result_envelopes=values)
        self.assertEqual(value["sample_date"], "2026-07-15")
        self.assertEqual(value["water_quality_status"], "safe")

    def test_duplicate_result_for_same_id_and_day_is_rejected(self):
        with self.assertRaisesRegex(beach.BeachContractError, "Duplicate result rows"):
            card(result_envelopes=[{
                "CollectionDate": "2026-07-15",
                "data": [
                    {"beachId": BEACH_ID, "statusFlag": "SAFE"},
                    {"beachId": BEACH_ID, "statusFlag": "UNSAFE"},
                ],
            }])

    def test_future_sample_date_is_rejected(self):
        with self.assertRaisesRegex(beach.BeachContractError, "future"):
            card(result_envelopes=[envelope("2026-07-16")])

    def test_access_closure_has_precedence_and_requires_verified_text(self):
        value = card(access_closure="Closed by Parks Canada.")
        self.assertEqual(value["display_state"], "access_closed")
        self.assertEqual(value["advisory"], "Closed by Parks Canada.")
        self.assertIsNone(value["water_quality_status"])

    def test_advisory_and_output_do_not_expose_measurement_or_geometry(self):
        value = card(result_envelopes=[envelope(
            eColi=17, advisory="<script>alert(1)</script>", geometry={"x": 1}
        )])
        self.assertEqual(value["advisory"], "<script>alert(1)</script>")
        encoded = str(value).casefold()
        self.assertNotIn("e_coli", encoded)
        self.assertNotIn("geometry", encoded)
        self.assertNotIn("17", str(value["advisory"]))
        self.assertEqual(value["publication_status"], "disabled_pending_source_rights_review")
        self.assertIn("ckan_unspecified", value["rights_status"])

    def test_public_export_remains_disabled(self):
        with self.assertRaises(beach.BeachExportDisabled):
            beach.export_public(card())


if __name__ == "__main__":
    unittest.main()

