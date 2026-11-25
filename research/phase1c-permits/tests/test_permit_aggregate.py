"""Supplied aggregate counts; synthetic timestamps/totals, no source records."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from permit_aggregate import build_projection, ProjectionError, STATUS
import permits_adapter


def receipt():
    return {
        "status": STATUS, "utcEnded": "2026-11-25T12:00:00.123456Z",
        "perSource": {
            key: {
                "generation": {"marker": "2026-11-24 08:17:15.620381|2026-11-24T08:18:00"},
                "rows": inside + 100,  # Synthetic full-source total.
                "counts": {"inside_coverage": inside},
                "reconciledDisposition": {
                    "insideNonCollidingRows": noncolliding,
                    "insideCollisionRowsQuarantine": collision,
                    "insideInvalidIdentityRowsQuarantine": 0,
                },
            }
            for key, inside, noncolliding, collision in (
                ("active", 22720, 22279, 441),
                ("cleared_since_2017", 47415, 46233, 1182),
            )
        },
    }


class AggregateTests(unittest.TestCase):
    def test_supplied_actual_counts_and_exact_allowlist(self):
        result = build_projection(receipt())
        self.assertEqual(set(result), {"schema_version", "footprint", "sources", "licence_url", "attribution"})
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(set(result["footprint"]), {"ward_numbers", "ward_boundary_source_url", "neighbourhood_boundary_source_url", "method"})
        self.assertEqual(result["footprint"]["ward_numbers"], list(range(20, 26)))
        self.assertEqual(result["footprint"]["ward_boundary_source_url"], "https://open.toronto.ca/dataset/city-wards/")
        self.assertEqual(result["footprint"]["neighbourhood_boundary_source_url"], "https://open.toronto.ca/dataset/neighbourhoods/")
        self.assertEqual(result["licence_url"], "https://open.toronto.ca/open-data-licence/")
        self.assertEqual(result["attribution"], "Contains information licensed under the Open Government Licence – Toronto.")
        for source, key, noncolliding, quarantined, total, slug in zip(
            result["sources"], ("active", "cleared_since_2017"), (22279, 46233),
            (441, 1182), (22720, 47415), ("active", "cleared"),
        ):
            self.assertEqual(set(source), {"collection", "source_url", "source_generation_as_supplied", "checked_at_utc", "in_footprint_noncolliding_row_count", "in_footprint_quarantined_row_count", "coverage_note"})
            self.assertEqual(source["collection"], key)
            self.assertEqual(source["source_url"], f"https://open.toronto.ca/dataset/building-permits-{slug}-permits/")
            self.assertEqual(source["in_footprint_noncolliding_row_count"], noncolliding)
            self.assertEqual(source["in_footprint_quarantined_row_count"], quarantined)
            self.assertEqual(noncolliding + quarantined, total)
            for limitation in ("not unique permits", "do not establish construction", "identity across generations", "not a source update time"):
                self.assertIn(limitation, source["coverage_note"])
        self.assertIn("legacy 2000–2016 is excluded", result["sources"][1]["coverage_note"])

    def test_no_leakage_override_mutation_or_network(self):
        value = receipt()
        expected = build_projection(value)
        poison = {key: "PRIVATE_SENTINEL" for key in (
            "IDs", "address", "coordinates", "X", "Y", "name", "details", "raw_rows",
            "source_url", "coverage_note", "attribution", "method", "licence_url",
        )}
        def inject(obj):
            for child in list(obj.values()):
                if isinstance(child, dict):
                    inject(child)
            obj.update(poison)
        for source in value["perSource"].values():
            inject(source)
        value.update(poison)
        original = deepcopy(value)
        with patch("socket.socket", side_effect=AssertionError("No network")):
            result = build_projection(value)
        self.assertEqual(result, expected)
        self.assertEqual(value, original)
        self.assertNotIn("PRIVATE_SENTINEL", json.dumps(result))

    def test_invalid_identity_rows_remain_quarantined(self):
        value = receipt()
        d = value["perSource"]["active"]["reconciledDisposition"]
        d["insideCollisionRowsQuarantine"] -= 2
        d["insideInvalidIdentityRowsQuarantine"] = 2
        self.assertEqual(build_projection(value)["sources"][0]["in_footprint_quarantined_row_count"], 441)

    def test_count_types_missing_fields_and_reconciliation(self):
        paths = [("rows",), ("counts", "inside_coverage")] + [
            ("reconciledDisposition", key) for key in receipt()["perSource"]["active"]["reconciledDisposition"]
        ]
        for collection in ("active", "cleared_since_2017"):
            for path in paths:
                for bad in (None, True, False, -1, 1.5, "22720", [], {}, float("nan"), float("inf"), "MISSING"):
                    with self.subTest(collection=collection, path=path, bad=bad):
                        value = receipt()
                        parent = value["perSource"][collection]
                        for key in path[:-1]:
                            parent = parent[key]
                        if bad == "MISSING":
                            del parent[path[-1]]
                        else:
                            parent[path[-1]] = bad
                        with self.assertRaises(ProjectionError):
                            build_projection(value)
        for rows, inside in ((0, 22720), (22719, 22720), (30000, 22721)):
            value = receipt()
            value["perSource"]["active"]["rows"] = rows
            value["perSource"]["active"]["counts"]["inside_coverage"] = inside
            with self.assertRaises(ProjectionError):
                build_projection(value)

    def test_structure_and_status_fail_closed(self):
        for field in ("status", "utcEnded", "perSource"):
            for bad in (None, [], {}, "incomplete"):
                value = receipt()
                value[field] = bad
                with self.assertRaises(ProjectionError):
                    build_projection(value)
        for bad in (None, [], "receipt"):
            with self.assertRaises(ProjectionError):
                build_projection(bad)
        for field in ("generation", "counts", "reconciledDisposition"):
            value = receipt()
            value["perSource"]["active"][field] = []
            with self.assertRaises(ProjectionError):
                build_projection(value)
        for key in ("active", "cleared_since_2017"):
            value = receipt()
            del value["perSource"][key]
            with self.assertRaises(ProjectionError):
                build_projection(value)
        value = receipt()
        value["perSource"]["planning"] = {}
        with self.assertRaises(ProjectionError):
            build_projection(value)

    def test_generation_validated_and_never_relabelled_utc(self):
        for marker in ("2026-11-24 08:17:15.620381", "2026-11-24T08:17:15-05:00", "2026-11-24T08:17:15Z|2026-11-24 09:00:00"):
            value = receipt()
            value["perSource"]["active"]["generation"]["marker"] = marker
            self.assertEqual(build_projection(value)["sources"][0]["source_generation_as_supplied"], marker)
        for bad in (None, "", " ", 123, {}, "PRIVATE_SENTINEL", "2026-02-30T00:00:00", "2026-11-24", "2026-11-24T00:00:00|", "2026-11-24T00:00:00\nPRIVATE_SENTINEL"):
            value = receipt()
            value["perSource"]["active"]["generation"]["marker"] = bad
            with self.assertRaises(ProjectionError) as caught:
                build_projection(value)
            self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_check_time_requires_explicit_utc(self):
        for good in ("2026-11-25T12:00:00Z", "2026-11-25T12:00:00.123456+00:00"):
            value = receipt()
            value["utcEnded"] = good
            self.assertEqual(build_projection(value)["sources"][0]["checked_at_utc"], good)
        for bad in ("2026-11-25T07:00:00-05:00", "2026-11-25T12:00:00", "2026-11-25T12:00:00-00:00", "2026-11-25", "2026-02-30T12:00:00Z", "2026-11-25T24:00:00Z", "2026-11-25T12:00:00+00:01", "2026-11-25T12:00:00Z prose"):
            value = receipt()
            value["utcEnded"] = bad
            with self.assertRaises(ProjectionError):
                build_projection(value)

    def test_order_determinism_and_existing_export_guard(self):
        value = receipt()
        expected = build_projection(value)
        value["perSource"] = dict(reversed(list(value["perSource"].items())))
        self.assertEqual(build_projection(value), expected)
        with self.assertRaises(permits_adapter.PermitExportDisabled):
            permits_adapter.export_public(expected)


if __name__ == "__main__":
    unittest.main()
