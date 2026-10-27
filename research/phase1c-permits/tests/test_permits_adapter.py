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

SQUARE = [{
    "type": "Feature",
    "properties": {"AREA_NAME": "Synthetic Neighbourhood"},
    "geometry": {"type": "Polygon", "coordinates": [[
        [-79.3, 43.7], [-79.1, 43.7], [-79.1, 43.9],
        [-79.3, 43.9], [-79.3, 43.7],
    ]]},
}]

SQUARE_WITH_HOLE = [{
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [
        [[-79.3, 43.7], [-79.1, 43.7], [-79.1, 43.9], [-79.3, 43.9], [-79.3, 43.7]],
        [[-79.25, 43.75], [-79.15, 43.75], [-79.15, 43.85], [-79.25, 43.85], [-79.25, 43.75]],
    ]},
}]


def oar_row(point_id, *, ward="25", address="4003 Ellesmere Rd", coordinates=None):
    return {
        "ADDRESS_POINT_ID": point_id,
        "ADDRESS_ID": 357094,
        "WARD": ward,
        "ADDRESS_FULL": address,
        "geometry": None if coordinates is None else {"type": "Point", "coordinates": coordinates},
    }


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
        "APPLICATION#": "21 191603 ESC 20 SA",
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

    def test_text_geo_id_from_live_ckan_schema_joins_verified_oar_point_id(self):
        # CKAN declares GEO_ID as text. The bounded live OAR lookup for point
        # 331669 returned ADDRESS_ID 357094 and 4003 Ellesmere Rd, ward 25.
        row = permits.normalize_permits(
            [permit_row(GEO_ID="331669")],
            source_collection="active",
            address_points=POINTS,
        )["records"][0]
        self.assertEqual(row["locations"][0]["address_point_id"], 331669)
        self.assertEqual(row["address"], "4003 Ellesmere Rd")
        self.assertNotEqual(row["address"], "347 Beechgrove Dr")

    def test_geo_id_rejects_non_numeric_and_non_positive_values(self):
        for value in ("331669x", " 331669 ", 0, -1, True):
            with self.subTest(value=value), self.assertRaises(permits.PermitContractError):
                permits.normalize_permits(
                    [permit_row(GEO_ID=value)],
                    source_collection="active",
                    address_points=POINTS,
                )

    def test_revision_zeroes_and_full_permit_number_are_preserved(self):
        row = permits.normalize_permits(
            [permit_row()], source_collection="cleared", address_points=POINTS
        )["records"][0]
        self.assertEqual(row["permit_number"], "22 236652 BLD")
        self.assertEqual(row["revision"], "00")
        self.assertEqual(row["record_key"], "permit:22 236652 BLD:00")

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
        self.assertEqual(result["quarantined_record_keys"], ["permit:22 236652 BLD:00"])

    def test_identical_active_cleared_duplicate_is_deduplicated_with_stable_key(self):
        active = permits.normalize_permits(
            [permit_row()], source_collection="active", address_points=POINTS
        )
        cleared = permits.normalize_permits(
            [permit_row()], source_collection="cleared", address_points=POINTS
        )
        combined = permits.combine_permit_collections(active, cleared)
        self.assertEqual(len(combined["records"]), 1)
        self.assertEqual(combined["records"][0]["record_key"], "permit:22 236652 BLD:00")
        self.assertEqual(combined["records"][0]["source_collection"], "active")
        self.assertEqual(combined["quarantined_record_keys"], [])
        reversed_combined = permits.combine_permit_collections(cleared, active)
        self.assertEqual(reversed_combined, combined)

    def test_conflicting_active_cleared_duplicate_is_quarantined(self):
        active = permits.normalize_permits(
            [permit_row()], source_collection="active", address_points=POINTS
        )
        cleared = permits.normalize_permits(
            [permit_row(STATUS="Cancelled")], source_collection="cleared", address_points=POINTS
        )
        combined = permits.combine_permit_collections(active, cleared)
        self.assertEqual(combined["records"], [])
        self.assertEqual(combined["quarantined_record_keys"], ["permit:22 236652 BLD:00"])

    def test_upstream_quarantine_is_preserved_when_combining(self):
        conflicted = permits.normalize_permits(
            [permit_row(), permit_row(STATUS="Closed")],
            source_collection="active", address_points=POINTS,
        )
        cleared = permits.normalize_permits(
            [permit_row(PERMIT_NUM="22 999999 BLD")],
            source_collection="cleared", address_points=POINTS,
        )
        combined = permits.combine_permit_collections(conflicted, cleared)
        self.assertIn("permit:22 236652 BLD:00", combined["quarantined_record_keys"])

    def test_untrusted_permit_url_is_omitted_not_replaced_with_planning_link(self):
        row = permits.normalize_permits(
            [permit_row(APPLICATION_URL="javascript:alert(1)")],
            source_collection="active", address_points=POINTS,
        )["records"][0]
        self.assertIsNone(row["official_url"])

    def test_permit_without_record_url_does_not_link_to_planning_applications(self):
        row = permits.normalize_permits(
            [permit_row(APPLICATION_URL=None)], source_collection="active", address_points=POINTS
        )["records"][0]
        self.assertIsNone(row["official_url"])

    def test_permit_source_address_must_match_joined_oar_address(self):
        with self.assertRaisesRegex(permits.PermitContractError, "disagrees with its OAR point"):
            permits.normalize_permits(
                [permit_row(ADDRESS="347 Beechgrove Dr")],
                source_collection="active", address_points=POINTS,
            )

    def test_oar_mapper_uses_live_schema_and_accounts_located_unlocated_rejected(self):
        result = permits.normalize_oar_address_points([
            oar_row("331669", coordinates=[-79.2, 43.8]),
            oar_row(2, coordinates=None),
            oar_row(3, coordinates=[-80.0, 43.8]),
            oar_row(4, ward="E2532", coordinates=[-79.2, 43.8]),
        ], neighbourhood_features=SQUARE, geometry_crs="EPSG:4326")
        self.assertEqual(result["total_count"], 4)
        self.assertEqual(result["located_count"], 1)
        self.assertEqual(result["unlocated_count"], 1)
        self.assertEqual(result["rejected_count"], 2)
        self.assertEqual(result["accounted_count"], result["total_count"])
        self.assertEqual(result["address_points"][0]["WARD_NUMBER"], 25)
        self.assertEqual(result["address_points"][0]["address"], "4003 Ellesmere Rd")

    def test_oar_mapper_does_not_classify_invalid_attributes_as_unlocated(self):
        result = permits.normalize_oar_address_points([
            oar_row(1, ward="E2532", coordinates=None),
        ], neighbourhood_features=SQUARE, geometry_crs="EPSG:4326")
        self.assertEqual(result["unlocated_count"], 0)
        self.assertEqual(result["rejected_count"], 1)

    def test_oar_mapper_validates_boundaries_even_when_no_points_are_locatable(self):
        with self.assertRaisesRegex(permits.PermitContractError, "required"):
            permits.normalize_oar_address_points(
                [oar_row(1)], neighbourhood_features=[], geometry_crs="EPSG:4326"
            )

    def test_oar_mapper_requires_explicit_coordinate_reference_system(self):
        with self.assertRaisesRegex(permits.PermitContractError, "explicitly qualified"):
            permits.normalize_oar_address_points(
                [oar_row(1, coordinates=[-79.2, 43.8])],
                neighbourhood_features=SQUARE, geometry_crs="",
            )

    def test_oar_mapper_quarantines_conflict_between_unlocated_and_located_rows(self):
        result = permits.normalize_oar_address_points([
            oar_row(9), oar_row(9, coordinates=[-79.2, 43.8]),
        ], neighbourhood_features=SQUARE, geometry_crs="EPSG:4326")
        self.assertEqual(result["unlocated_count"], 0)
        self.assertEqual(result["rejected_count"], 2)
        self.assertEqual(result["located_count"], 0)
        self.assertEqual(result["accounted_count"], 2)

    def test_oar_mapper_accepts_json_text_singleton_multipoint(self):
        result = permits.normalize_oar_address_points([
            oar_row(11, coordinates=None) | {
                "geometry": '{"type":"MultiPoint","coordinates":[[-79.2,43.8]]}'
            },
        ], neighbourhood_features=SQUARE, geometry_crs="EPSG:4326")
        self.assertEqual(result["located_count"], 1)
        self.assertEqual(result["address_points"][0]["longitude"], -79.2)

    def test_conflicting_duplicate_oar_id_is_quarantined_independent_of_order(self):
        rows = [
            oar_row(12, address="First Address", coordinates=[-79.2, 43.8]),
            oar_row(12, address="Different Address", coordinates=[-79.21, 43.81]),
        ]
        forward = permits.normalize_oar_address_points(rows, neighbourhood_features=SQUARE, geometry_crs="EPSG:4326")
        reverse = permits.normalize_oar_address_points(list(reversed(rows)), neighbourhood_features=SQUARE, geometry_crs="EPSG:4326")
        self.assertEqual(forward, reverse)
        self.assertEqual(forward["address_points"], [])
        self.assertEqual(forward["rejected_count"], 2)

    def test_polygon_union_supports_multipolygon_holes_and_rejects_malformed_rings(self):
        multipolygon = [{"geometry": {"type": "MultiPolygon", "coordinates": [
            SQUARE[0]["geometry"]["coordinates"],
            [[[-78.9, 43.7], [-78.8, 43.7], [-78.8, 43.8], [-78.9, 43.8], [-78.9, 43.7]]],
        ]}}]
        self.assertTrue(permits.point_in_scarborough_neighbourhoods(-79.2, 43.8, multipolygon))
        self.assertTrue(permits.point_in_scarborough_neighbourhoods(-78.85, 43.75, multipolygon))
        self.assertFalse(permits.point_in_scarborough_neighbourhoods(-79.2, 43.8, SQUARE_WITH_HOLE))
        self.assertTrue(permits.point_in_scarborough_neighbourhoods(-79.3, 43.8, SQUARE))
        with self.assertRaisesRegex(permits.PermitContractError, "closed"):
            permits.point_in_scarborough_neighbourhoods(-79.2, 43.8, [{
                "geometry": {"type": "Polygon", "coordinates": [[[-79.3, 43.7], [-79.1, 43.7], [-79.1, 43.9], [-79.3, 43.9]]]}
            }])
        with self.assertRaisesRegex(permits.PermitContractError, "no polygon"):
            permits.point_in_scarborough_neighbourhoods(-79.2, 43.8, [{
                "geometry": {"type": "MultiPolygon", "coordinates": []}
            }])
        with self.assertRaisesRegex(permits.PermitContractError, "closed"):
            permits.point_in_scarborough_neighbourhoods(-79.2, 43.8, SQUARE + [{
                "geometry": {"type": "Polygon", "coordinates": [[[-79.3, 43.7], [-79.1, 43.7], [-79.1, 43.9], [-79.3, 43.9]]]}
            }])

    def test_non_finite_oar_coordinates_are_rejected(self):
        result = permits.normalize_oar_address_points([
            oar_row(10, coordinates=[float("nan"), 43.8]),
        ], neighbourhood_features=SQUARE, geometry_crs="EPSG:4326")
        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(result["accounted_count"], 1)

    def test_polygon_validator_rejects_non_finite_input_coordinates(self):
        with self.assertRaisesRegex(permits.PermitContractError, "finite WGS84"):
            permits.point_in_scarborough_neighbourhoods(float("nan"), 43.8, SQUARE)

    def test_permit_status_is_trimmed_but_raw_text_and_unlocated_count_are_retained(self):
        result = permits.normalize_permits(
            [permit_row(STATUS=" Issued ", GEO_ID=None)],
            source_collection="active", address_points=[],
            oar_accounting={"total_count": 1, "located_count": 0, "unlocated_count": 1, "rejected_count": 0, "accounted_count": 1},
        )
        row = result["records"][0]
        self.assertEqual(row["status"], "Issued")
        self.assertEqual(row["raw_status"], " Issued ")
        self.assertEqual(result["location_accounting"]["address_points_total"], 1)
        self.assertEqual(result["location_accounting"]["permit_rows_unlocated"], 1)

    def test_permit_normalizer_rejects_inconsistent_oar_accounting(self):
        with self.assertRaisesRegex(permits.PermitContractError, "does not reconcile"):
            permits.normalize_permits(
                [], source_collection="active", address_points=[],
                oar_accounting={"total_count": 2, "located_count": 1, "unlocated_count": 1, "rejected_count": 0, "accounted_count": 2},
            )

    def test_permit_dates_require_iso_calendar_format(self):
        for value in ("2022-6-01", "2022-02-30", "2022-06-01T00:00:00Z"):
            with self.subTest(value=value), self.assertRaisesRegex(permits.PermitContractError, "ISO calendar date"):
                permits.normalize_permits(
                    [permit_row(APPLICATION_DATE=value)], source_collection="active", address_points=POINTS
                )

    def test_development_rows_group_by_folder_and_keep_all_locations(self):
        rows = [
            dev_row(address="1552 Kingston Rd", _id=3),
            dev_row(address="1572 Kingston Rd", _id=4),
        ]
        record = permits.normalize_development_applications(rows)["records"][0]
        self.assertEqual(record["record_key"], "development:folder:4970049")
        self.assertEqual(record["application_number"], "21 191603 ESC 20 SA")
        self.assertEqual(
            [location["address"] for location in record["locations"]],
            ["1552 Kingston Rd", "1572 Kingston Rd"],
        )
        reverse = permits.normalize_development_applications(list(reversed(rows)))["records"][0]
        self.assertEqual(record["fingerprint"], reverse["fingerprint"])

    def test_live_street_component_schema_builds_development_addresses(self):
        record = permits.normalize_development_applications([
            dev_row(
                address=None, STREET_NUM="1552", STREET_NAME="Kingston",
                STREET_TYPE="Rd", STREET_DIRECTION=None,
            ),
            dev_row(
                address=None, STREET_NUM="1572", STREET_NAME="Kingston",
                STREET_TYPE="Rd", STREET_DIRECTION=None,
            ),
        ])["records"][0]
        self.assertEqual(
            [loc["address"] for loc in record["locations"]],
            ["1552 Kingston Rd", "1572 Kingston Rd"],
        )

    def test_development_application_uses_planning_fallback_when_url_missing(self):
        record = permits.normalize_development_applications([
            dev_row(APPLICATION_URL=None)
        ])["records"][0]
        self.assertEqual(record["official_url"], permits.FALLBACK_PLANNING_URL)

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
        self.assertEqual(record["record_key"], "development:application:21 191603 ESC 20 SA")
        self.assertTrue(record["folder_fallback_used"])

    def test_missing_folder_resolves_only_from_unambiguous_matching_application(self):
        rows = [dev_row(), dev_row(FOLDERRSN=None, address="1572 Kingston Rd")]
        record = permits.normalize_development_applications(rows)["records"][0]
        self.assertEqual(record["record_key"], "development:folder:4970049")
        self.assertFalse(record["folder_fallback_used"])
        self.assertTrue(record["missing_folder_resolved_from_other_row"])
        self.assertEqual(len(record["locations"]), 2)

    def test_missing_folder_is_quarantined_if_application_maps_to_multiple_folders(self):
        result = permits.normalize_development_applications([
            dev_row(FOLDERRSN="4970049"),
            dev_row(FOLDERRSN="4970050"),
            dev_row(FOLDERRSN=None),
        ])
        self.assertEqual(result["records"], [])
        self.assertEqual(set(result["quarantined_record_keys"]), {
            "development:folder:4970049", "development:folder:4970050",
        })

    def test_development_source_text_is_trimmed_and_raw_fields_retained(self):
        row = permits.normalize_development_applications([
            dev_row(APPLICATION_TYPE=" Site Plan ", STATUS=" Under Review "),
        ])["records"][0]
        self.assertEqual(row["application_type"], "Site Plan")
        self.assertEqual(row["raw_application_type"], " Site Plan ")
        self.assertEqual(row["status"], "Under Review")
        self.assertEqual(row["raw_status"], " Under Review ")

    def test_development_status_and_type_must_remain_text(self):
        for field in ("APPLICATION_TYPE", "STATUS"):
            with self.subTest(field=field), self.assertRaisesRegex(permits.PermitContractError, "source text"):
                permits.normalize_development_applications([dev_row(**{field: 123})])

    def test_development_submission_date_requires_iso_calendar_format(self):
        with self.assertRaisesRegex(permits.PermitContractError, "ISO date or timestamp"):
            permits.normalize_development_applications([dev_row(DATE_SUBMITTED="2021-1-14")])

    def test_development_submission_timestamp_preserves_naive_source_form(self):
        record = permits.normalize_development_applications([
            dev_row(DATE_SUBMITTED="2021-07-29T00:00:00"),
        ])["records"][0]
        self.assertEqual(record["submission_date"], "2021-07-29")
        self.assertEqual(record["submission_timestamp"], "2021-07-29T00:00:00")
        self.assertNotIn("Z", record["submission_timestamp"])

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
        with self.assertRaisesRegex(permits.PermitContractError, "Toronto-area envelope"):
            permits.normalize_permits(
                [permit_row()], source_collection="active",
                address_points=[dict(POINTS[0], longitude=0, latitude=0)],
            )

    def test_public_export_is_disabled(self):
        with self.assertRaises(permits.PermitExportDisabled):
            permits.export_public([])


if __name__ == "__main__":
    unittest.main()

