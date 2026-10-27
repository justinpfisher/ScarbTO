from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

import beach_measurement_history as history


def row(row_id, *, day="2026-09-16", e_coli=None, site="49E"):
    return {
        "_id": row_id,
        "beachId": 10,
        "beachName": "Bluffer's Beach Park",
        "siteName": site,
        "collectionDate": day,
        "eColi": e_coli,
    }


def page(total, rows):
    return {"success": True, "result": {
        "resource_id": history.RESOURCE_ID,
        "filters": {"beachId": 10},
        "total": total,
        "total_was_estimated": False,
        "records": rows,
    }}


class BeachMeasurementHistoryTests(unittest.TestCase):
    def test_query_is_fixed_resource_filtered_and_ckan_encoded(self):
        url = history.query_url(offset=20, limit=10)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.hostname, history.API_HOST)
        self.assertEqual(params["resource_id"], ["8102bd4c-83cd-4354-9788-eecc0c7a09b4"])
        self.assertEqual(params["fields"], ["_id,beachId,beachName,siteName,collectionDate,eColi"])
        self.assertEqual(json.loads(params["filters"][0]), {"beachId": 10})
        self.assertEqual(params["sort"], ["_id asc"])
        self.assertEqual(params["offset"], ["20"])
        self.assertEqual(params["limit"], ["10"])

    def test_live_client_refuses_unapproved_host_and_redirects(self):
        client = history.TorontoBeachHistoryClient()
        with self.assertRaisesRegex(history.BeachHistoryError, "outside the fixed HTTPS host"):
            client._get_json("https://example.invalid/api")
        handler = history._RejectRedirects()
        with self.assertRaisesRegex(history.BeachHistoryError, "redirect rejected"):
            handler.redirect_request(None, None, 302, "Found", {}, "https://example.invalid/")
        with self.assertRaisesRegex(ValueError, "Invalid bounded CKAN client limits"):
            history.TorontoBeachHistoryClient(max_response_bytes=history.MAX_PAGE_BYTES + 1)

    def test_live_client_requires_exact_package_resource_and_count(self):
        client = history.TorontoBeachHistoryClient()
        package = {
            "success": True,
            "result": {
                "id": history.PACKAGE_ID,
                "metadata_modified": "2026-09-24T21:07:41.327144",
                "resources": [{
                    "id": history.RESOURCE_ID,
                    "datastore_active": True,
                    "last_modified": None,
                    "metadata_modified": "2026-09-24T21:07:40.968373",
                }],
            },
        }
        count = page(10_300, [])
        with patch.object(client, "_get_json", side_effect=[package, count]) as get_json:
            total, generation = client.metadata()
        self.assertEqual(total, 10_300)
        self.assertIn("package:2026-09-24T21:07:41.327144", generation)
        self.assertIn("resource:2026-09-24T21:07:40.968373", generation)
        request = get_json.call_args.args[0]
        params = parse_qs(urlparse(request).query)
        self.assertEqual(params["limit"], ["0"])
        self.assertEqual(params["fields"], [",".join(history.FIELDS)])

    def test_live_client_rejects_inactive_or_mismatched_resource(self):
        client = history.TorontoBeachHistoryClient()
        package = {
            "success": True,
            "result": {
                "id": history.PACKAGE_ID,
                "metadata_modified": "2026-09-24T21:07:41.327144",
                "resources": [{"id": "wrong", "datastore_active": True}],
            },
        }
        with patch.object(client, "_get_json", return_value=package):
            with self.assertRaisesRegex(history.BeachHistoryError, "missing or inactive"):
                client.metadata()

    def test_complete_snapshot_requires_exact_stable_pagination(self):
        result = history.build_complete_snapshot(
            [page(3, [row(11, e_coli=17), row(12, site="50E")]), page(3, [row(15, day="2026-09-08")])],
            total_before=3, generation_before="g1", total_after=3, generation_after="g1",
            page_size=2, retrieved_at=datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["records"][0]["eColi"], 17)
        self.assertIn("not current swimming advice", result["interpretation"])
        self.assertNotIn("status", result["records"][0])

    def test_estimated_total_is_rejected(self):
        estimated = page(1, [row(1)])
        estimated["result"]["total_was_estimated"] = True
        with self.assertRaisesRegex(history.BeachHistoryError, "estimated"):
            history.validate_page(estimated, limit=1)

    def test_missing_exactness_flag_is_rejected(self):
        unknown = page(1, [row(1)])
        del unknown["result"]["total_was_estimated"]
        with self.assertRaisesRegex(history.BeachHistoryError, "estimated or lacks"):
            history.validate_page(unknown, limit=1)

    def test_incomplete_or_unstable_snapshot_fails_closed(self):
        cases = [
            ([page(3, [row(1), row(2)])], 3, "incomplete"),
            ([page(2, [row(1), row(2)]), page(2, [row(3)])], 3, "page total changed"),
        ]
        for pages, after_total, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(history.BeachHistoryError, message):
                    history.build_complete_snapshot(
                        pages, total_before=3, generation_before="g1",
                        total_after=after_total, generation_after="g1",
                        page_size=2, retrieved_at=datetime.now(timezone.utc),
                    )

    def test_generation_change_and_unordered_ids_are_rejected(self):
        with self.assertRaisesRegex(history.BeachHistoryError, "generation changed"):
            history.build_complete_snapshot(
                [page(1, [row(1)])], total_before=1, generation_before="g1",
                total_after=1, generation_after="g2", page_size=2,
                retrieved_at=datetime.now(timezone.utc),
            )

    def test_invalid_page_size_and_boolean_final_total_fail_closed(self):
        with self.assertRaisesRegex(history.BeachHistoryError, "page size"):
            history.collect_and_store_snapshot(
                metadata_before=(1, "g1"), fetch_page=lambda offset, limit: page(1, [row(1)]),
                metadata_after=lambda: (1, "g1"), destination=".", page_size=0,
                retrieved_at=datetime.now(timezone.utc),
            )
        with self.assertRaisesRegex(history.BeachHistoryError, "source total changed"):
            history.build_complete_snapshot(
                [page(1, [row(1)])], total_before=1, generation_before="g1",
                total_after=True, generation_after="g1", page_size=1,
                retrieved_at=datetime.now(timezone.utc),
            )
        with self.assertRaisesRegex(history.BeachHistoryError, "unordered"):
            history.build_complete_snapshot(
                [page(2, [row(2), row(1)])], total_before=2, generation_before="g1",
                total_after=2, generation_after="g1", page_size=2,
                retrieved_at=datetime.now(timezone.utc),
            )

    def test_health_status_is_never_inferred_from_measurement(self):
        with self.assertRaisesRegex(history.BeachHistoryError, "exact field allowlist"):
            history.validate_page(page(1, [dict(row(1, e_coli=17), statusFlag="SAFE")]), limit=1)
        with self.assertRaisesRegex(history.BeachHistoryError, "nonnegative integer or null"):
            history.validate_page(page(1, [row(1, e_coli="SAFE")]), limit=1)

    def test_candidate_snapshot_is_content_addressed_and_manifest_is_atomic_pointer(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            rows = [row(7, e_coli=17), row(9, day="2026-09-08", site="50E")]
            manifest = history.collect_and_store_snapshot(
                metadata_before=(2, "g1"),
                fetch_page=lambda offset, limit: page(2, rows[offset:offset + limit]),
                metadata_after=lambda: (2, "g1"), destination=directory, page_size=1,
                retrieved_at=datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc),
            )
            root = Path(directory)
            manifest_path = root / "beach-10-history-manifest.json"
            stored = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(stored, manifest)
            self.assertEqual(stored["row_count"], 2)
            snapshot_path = root / stored["snapshot_file"]
            self.assertTrue(snapshot_path.is_file())
            self.assertEqual(history._file_sha256(snapshot_path), stored["sha256"])
            self.assertEqual(stored["publication_status"], "candidate_requires_application_integration_review")

    def test_failed_refresh_preserves_last_good_manifest_and_snapshot(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            rows = [row(7), row(9, day="2026-09-08")]
            first = history.collect_and_store_snapshot(
                metadata_before=(2, "g1"),
                fetch_page=lambda offset, limit: page(2, rows[offset:offset + limit]),
                metadata_after=lambda: (2, "g1"), destination=directory, page_size=1,
                retrieved_at=datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc),
            )
            manifest_path = Path(directory) / "beach-10-history-manifest.json"
            before = manifest_path.read_bytes()
            calls = []

            def broken_page(offset, limit):
                calls.append(offset)
                if offset == 0:
                    return page(2, [row(11)])
                return page(1, [row(12)])

            with self.assertRaisesRegex(history.BeachHistoryError, "page total changed"):
                history.collect_and_store_snapshot(
                    metadata_before=(2, "g2"), fetch_page=broken_page,
                    metadata_after=lambda: (2, "g2"), destination=directory, page_size=1,
                    retrieved_at=datetime(2026, 10, 27, 13, 0, tzinfo=timezone.utc),
                )
            self.assertEqual(calls, [0, 1])
            self.assertEqual(manifest_path.read_bytes(), before)
            self.assertTrue((Path(directory) / first["snapshot_file"]).is_file())


if __name__ == "__main__":
    unittest.main()

