import json
import unittest

import permits_adapter as permits


POINTS = [
    {
        "ADDRESS_POINT_ID": 331669,
        "ADDRESS_ID": 357094,
        "address": "4003 Ellesmere Rd",
        "longitude": -79.1616549284861,
        "latitude": 43.7926372130702,
        "WARD_NUMBER": 25,
    },
    {
        "ADDRESS_POINT_ID": 357094,
        "ADDRESS_ID": 331669,
        "address": "347 Beechgrove Dr",
        "longitude": -79.12,
        "latitude": 43.8,
        "WARD_NUMBER": 25,
    },
]


def permit_row(**overrides):
    row = {
        "PERMIT_NUM": "22 236652 BLD",
        "REVISION_NUM": "00",
        "PERMIT_TYPE": "BLD",
        "GEO_ID": 331669,
        "APPLICATION_DATE": "2022-05-01",
        "ISSUED_DATE": "2022-06-01",
        "COMPLETED_DATE": None,
        "STATUS": "Issued",
        "APPLICATION_URL": "https://www.toronto.ca/example/permit",
        "BUILDER_NAME": "Synthetic Private Builder",
        "CONTACT_EMAIL": "private@example.invalid",
        "DESCRIPTION": "do not expose",
        "_id": 1,
    }
    row.update(overrides)
    return row


def dev_row(**overrides):
    row = {
        "APPLICATION_TYPE": "Site Plan",
        "APPLICATION#": "20 191603 ESC 20 SA",
        "FOLDERRSN": "4970049",
        "address": "1552 Kingston Rd",
        "DATE_SUBMITTED": "2021-01-14",
        "STATUS": "Under Review",
        "WARD_NUMBER": "20",
        "APPLICATION_URL": "https://www.toronto.ca/planning/app/123",
        "CONTACT_NAME": "Synthetic Name",
        "CONTACT_EMAIL": "secret@example.invalid",
        "DESCRIPTION": "unreviewed free text",
        "X": 123456,
        "Y": 789012,
        "_id": 22,
    }
    row.update(overrides)
    return row


class PermitContractTests(unittest.TestCase):
    def test_datastore_snapshot_requires_stable_complete_pagination(self):
        pages = [
            {"offset": 0, "limit": 2, "records": [{"_id": 1}, {"_id": 2}]},
            {"offset": 2, "limit": 2, "records": [{"_id": 3}]},
        ]
        rows = permits.validate_snapshot_pages(
            pages, generation_before="g1", generation_after="g1",
            total_before=3, total_after=3,
        )
        self.assertEqual(len(rows), 3)
        with self.assertRaisesRegex(permits.PermitContractError, "generation changed"):
            permits.validate_snapshot_pages(
                pages, generation_before="g1", generation_after="g2",
                total_before=3, total_after=3,
            )
        with self.assertRaisesRegex(permits.PermitContractError, "Incomplete"):
            permits.validate_snapshot_pages(
                pages[:1], generation_before="g1", generation_after="g1",
                total_before=3, total_after=3,
            )
        with self.assertRaisesRegex(permits.PermitContractError, "offset zero"):
            permits.validate_snapshot_pages(
                [{"offset": False, "limit": 1, "records": [{"_id": 1}]}],
                generation_before="g1", generation_after="g1",
                total_before=1, total_after=1,
            )

    def test_permit_geography_joins_geo_id_to_address_point_id(self):
        result = permits.normalize_permits(
            [permit_row()], source_collection="active", address_points=POINTS
        )
        row = result["records"][0]
        self.assertEqual(row["address"], "4003 Ellesmere Rd")
        self.assertEqual(row["locations"][0]["address_point_id"], 331669)
        self.assertNotEqual(row["address"], "347 Beechgrove Dr")

    def test_revision_zeroes_and_full_permit_number_are_preserved(self):
        row = permits.normalize_permits(
            [permit_row()], source_collection="cleared", address_points=POINTS
        )["records"][0]
        self.assertEqual(row["permit_number"], "22 236652 BLD")
        self.assertEqual(row["revision"], "00")
        self.assertEqual(row["record_key"], "cleared:22 236652 BLD:00")

    def test_permit_types_at_same_address_remain_separate(self):
        values = permits.normalize_permits(
            [
                permit_row(PERMIT_NUM="22 236652 BLD", PERMIT_TYPE="BLD"),
                permit_row(PERMIT_NUM="22 236652 HVA", PERMIT_TYPE="HVA"),
            ],
            source_collection="active",
            address_points=POINTS,
        )["records"]
        self.assertEqual({row["permit_type"] for row in values}, {"BLD", "HVA"})

    def test_cancelled_completed_date_does_not_claim_construction(self):
        row = permits.normalize_permits(
            [permit_row(
                PERMIT_NUM="17 225341 ALT", PERMIT_TYPE="ALT",
                ISSUED_DATE=None, COMPLETED_DATE="2017-10-31", STATUS="Cancelled",
            )],
            source_collection="cleared", address_points=[],
        )["records"][0]
        self.assertEqual(row["status"], "Cancelled")
        self.assertEqual(row["completed_date"], "2017-10-31")
        self.assertEqual(row["construction_state"], "not_inferred")

    def test_active_closed_without_dates_is_not_inferred_completed(self):
        row = permits.normalize_permits(
            [permit_row(ISSUED_DATE=None, COMPLETED_DATE=None, STATUS="Closed")],
            source_collection="active", address_points=POINTS,
        )["records"][0]
        self.assertEqual(row["status"], "Closed")
        self.assertIsNone(row["issued_date"])
        self.assertIsNone(row["completed_date"])
        self.assertEqual(row["construction_state"], "not_inferred")

    def test_conflicting_duplicate_within_collection_is_quarantined(self):
        result = permits.normalize_permits(
            [permit_row(), permit_row(STATUS="Closed")],
            source_collection="active", address_points=POINTS,
        )
        self.assertEqual(result["records"], [])
        self.assertEqual(result["quarantined_record_keys"], ["active:22 236652 BLD:00"])

    def test_active_cleared_duplicate_is_quarantined(self):
        active = permits.normalize_permits(
            [permit_row()], source_collection="active", address_points=POINTS
        )
        cleared = permits.normalize_permits(
            [permit_row()], source_collection="cleared", address_points=POINTS
        )
        combined = permits.combine_permit_collections(active, cleared)
        self.assertEqual(combined["records"], [])
        self.assertEqual(len(combined["quarantined_record_keys"]), 2)

    def test_untrusted_url_uses_official_fallback(self):
        row = permits.normalize_permits(
            [permit_row(APPLICATION_URL="javascript:alert(1)")],
            source_collection="active", address_points=POINTS,
        )["records"][0]
        self.assertEqual(row["official_url"], permits.FALLBACK_PLANNING_URL)

    def test_development_rows_group_by_folder_and_keep_all_locations(self):
        rows = [
            dev_row(address="1552 Kingston Rd", _id=3),
            dev_row(address="1572 Kingston Rd", _id=4),
        ]
        record = permits.normalize_development_applications(rows)["records"][0]
        self.assertEqual(record["record_key"], "development:folder:4970049")
        self.assertEqual(record["application_number"], "20 191603 ESC 20 SA")
        self.assertEqual(
            [location["address"] for location in record["locations"]],
            ["1552 Kingston Rd", "1572 Kingston Rd"],
        )
        reverse = permits.normalize_development_applications(list(reversed(rows)))["records"][0]
        self.assertEqual(record["fingerprint"], reverse["fingerprint"])

    def test_folder_collision_with_different_application_is_quarantined(self):
        result = permits.normalize_development_applications([
            dev_row(),
            dev_row(**{"APPLICATION#": "21 000001 ESC 20 SA"}),
        ])
        self.assertEqual(result["records"], [])
        self.assertEqual(result["quarantined_record_keys"], ["development:folder:4970049"])

    def test_missing_folder_uses_explicit_application_fallback(self):
        record = permits.normalize_development_applications([
            dev_row(FOLDERRSN=None)
        ])["records"][0]
        self.assertEqual(record["record_key"], "development:application:20 191603 ESC 20 SA")
        self.assertTrue(record["folder_fallback_used"])

    def test_non_ward_grid_codes_are_not_treated_as_ward_numbers(self):
        result = permits.normalize_development_applications([dev_row(WARD_NUMBER="E2532")])
        self.assertEqual(result["records"], [])

    def test_conflicting_development_metadata_is_quarantined(self):
        result = permits.normalize_development_applications([
            dev_row(), dev_row(STATUS="Closed"),
        ])
        self.assertEqual(result["records"], [])
        self.assertEqual(result["quarantined_record_keys"], ["development:folder:4970049"])

    def test_sensitive_and_unreviewed_fields_are_excluded(self):
        permit = permits.normalize_permits(
            [permit_row()], source_collection="active", address_points=POINTS
        )
        development = permits.normalize_development_applications([dev_row()])
        serialized = json.dumps({"permit": permit, "development": development})
        for forbidden in (
            "Synthetic Private Builder", "private@example.invalid", "unreviewed free text",
            "Synthetic Name", "secret@example.invalid", "123456", "789012",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(permit["publication_status"], "disabled_pending_source_and_privacy_review")

    def test_address_point_id_is_required_and_wgs84_range_checked(self):
        with self.assertRaisesRegex(permits.PermitContractError, "ADDRESS_POINT_ID"):
            permits.normalize_permits(
                [permit_row()], source_collection="active",
                address_points=[dict(POINTS[0], ADDRESS_POINT_ID=0)],
            )
        with self.assertRaisesRegex(permits.PermitContractError, "WGS84"):
            permits.normalize_permits(
                [permit_row()], source_collection="active",
                address_points=[dict(POINTS[0], longitude=400)],
            )

    def test_public_export_is_disabled(self):
        with self.assertRaises(permits.PermitExportDisabled):
            permits.export_public([])


if __name__ == "__main__":
    unittest.main()

