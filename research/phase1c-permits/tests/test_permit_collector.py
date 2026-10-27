import json
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import permit_collector as collector


def source_row(row_id, **extra):
    return {
        "_id": row_id,
        "PERMIT_NUM": f"synthetic-{row_id}",
        "REVISION_NUM": "00",
        "PERMIT_TYPE": "BLD",
        "GEO_ID": None,
        "APPLICATION_DATE": None,
        "ISSUED_DATE": None,
        "COMPLETED_DATE": None,
        "STATUS": "Issued",
        "STREET_NUM": "1",
        "STREET_NAME": "Synthetic",
        "STREET_TYPE": "Rd",
        "STREET_DIRECTION": None,
        **extra,
    }


def page(total, rows):
    return {"success": True, "result": {"total": total, "records": rows}}


class PermitCollectorTests(unittest.TestCase):
    class Response:
        def __init__(self, body, url="https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/datastore_search"):
            self.body = body
            self.url = url
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def geturl(self):
            return self.url

        def read(self, size=-1):
            return self.body[:size]

    def test_client_uses_fixed_https_host_and_json_field_allowlist(self):
        response_body = json.dumps(page(0, [])).encode()
        with patch.object(collector, "urlopen", return_value=self.Response(response_body)) as open_url:
            client = collector.TorontoCKAN(retries=0)
            response = client._get_json("datastore_search", {
                "resource_id": "synthetic-resource",
                "limit": 0,
                "fields": ["_id", "STATUS"],
            })
        request = open_url.call_args.args[0]
        parsed = urlparse(request.full_url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.hostname, collector.API_HOST)
        self.assertEqual(json.loads(query["fields"][0]), ["_id", "STATUS"])
        self.assertEqual(response["result"]["records"], [])

    def test_client_rejects_redirect_outside_fixed_host(self):
        response_body = json.dumps(page(0, [])).encode()
        response = self.Response(response_body, "https://example.invalid/data")
        with patch.object(collector, "urlopen", return_value=response):
            with self.assertRaisesRegex(collector.CollectionError, "redirected outside"):
                collector.TorontoCKAN(retries=0)._get_json("datastore_search", {"limit": 0})

    def test_client_rejects_response_over_byte_limit(self):
        body = json.dumps(page(0, [])).encode() + (b" " * 1100)
        with patch.object(collector, "urlopen", return_value=self.Response(body)):
            with self.assertRaisesRegex(collector.CollectionError, "byte limit"):
                collector.TorontoCKAN(max_page_bytes=1024, retries=0)._get_json("datastore_search", {"limit": 0})

    def test_streams_allowlisted_pages_then_atomically_advances_manifest(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            metadata_values = iter([(3, "g1"), (3, "g1")])
            pages = {
                0: page(3, [source_row(17), source_row(18)]),
                2: page(3, [source_row(19)]),
            }
            result = collector.collect_snapshot(
                "active_permits", root,
                metadata=lambda: next(metadata_values),
                fetch_page=lambda offset, limit: pages[offset],
                page_size=2,
            )
            self.assertEqual(result["row_count"], 3)
            self.assertEqual(result["first_id"], 17)
            self.assertEqual(result["last_id"], 19)
            self.assertEqual(result["generation"], "g1")
            self.assertEqual(result["publication_status"], "disabled_pending_source_geography_and_privacy_review")
            snapshot = Path(root) / result["snapshot_file"]
            self.assertTrue(snapshot.is_file())
            rows = [json.loads(line) for line in snapshot.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["_id"] for row in rows], [17, 18, 19])
            self.assertFalse(list(Path(root).glob("*.tmp")))

    def test_actual_client_page_shape_composes_with_snapshot_collector(self):
        source = collector.SOURCE_RESOURCES["active_permits"]
        package = {"success": True, "result": {
            "metadata_modified": "2026-10-27T00:00:00",
            "resources": [{"id": source["resource_id"], "last_modified": "2026-10-26T00:00:00"}],
        }}
        count = page(1, [])
        records = page(1, [source_row(12)])
        client = collector.TorontoCKAN(retries=0)
        with patch.object(client, "_get_json", side_effect=[package, count, records, package, count]):
            with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                manifest = collector.collect_snapshot(
                    "active_permits", root,
                    metadata=lambda: client.metadata("active_permits"),
                    fetch_page=lambda offset, limit: client.page("active_permits", offset=offset, limit=limit),
                )
        self.assertEqual(manifest["row_count"], 1)
        self.assertEqual(manifest["first_id"], 12)

    def test_required_source_schema_rejects_id_only_page(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with self.assertRaisesRegex(collector.CollectionError, "required source fields"):
                collector.collect_snapshot(
                    "active_permits", root,
                    metadata=lambda: (1, "generation-1"),
                    fetch_page=lambda offset, limit: page(1, [{"_id": 1}]),
                )
            self.assertFalse((Path(root) / "active_permits-manifest.json").exists())

    def test_empty_generation_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with self.assertRaisesRegex(collector.CollectionError, "generation marker is empty"):
                collector.collect_snapshot(
                    "active_permits", root, metadata=lambda: (1, " "),
                    fetch_page=lambda offset, limit: page(1, [source_row(1)]),
                )

    def test_empty_result_cannot_replace_nonempty_last_good_snapshot(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            previous = collector.collect_snapshot(
                "active_permits", root,
                metadata=lambda: (1, "g1"),
                fetch_page=lambda offset, limit: page(1, [source_row(9)]),
            )
            manifest_path = Path(root) / "active_permits-manifest.json"
            previous_bytes = manifest_path.read_bytes()
            with self.assertRaisesRegex(collector.CollectionError, "not accepted without a qualified"):
                collector.collect_snapshot(
                    "active_permits", root, metadata=lambda: (0, "g2"),
                    fetch_page=lambda offset, limit: page(0, []),
                )
            self.assertEqual(manifest_path.read_bytes(), previous_bytes)
            self.assertTrue((Path(root) / previous["snapshot_file"]).is_file())

    def test_large_source_count_drop_preserves_last_good_snapshot(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            previous = collector.collect_snapshot(
                "active_permits", root,
                metadata=lambda: (4, "g1"),
                fetch_page=lambda offset, limit: page(4, [source_row(i) for i in range(1, 5)]),
                page_size=4,
            )
            manifest_path = Path(root) / "active_permits-manifest.json"
            previous_bytes = manifest_path.read_bytes()
            with self.assertRaisesRegex(collector.CollectionError, "retention floor"):
                collector.collect_snapshot(
                    "active_permits", root, metadata=lambda: (1, "g2"),
                    fetch_page=lambda offset, limit: page(1, [source_row(5)]),
                )
            self.assertEqual(manifest_path.read_bytes(), previous_bytes)
            self.assertTrue((Path(root) / previous["snapshot_file"]).is_file())

    def test_corrupt_content_addressed_file_is_not_reused_or_promoted(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            row = source_row(33)
            encoded = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            digest = sha256(encoded).hexdigest()
            corrupt = Path(root) / f"active_permits-{digest}.jsonl"
            corrupt.write_bytes(b"corrupt existing snapshot")
            with self.assertRaisesRegex(collector.CollectionError, "content-addressed snapshot is corrupt"):
                collector.collect_snapshot(
                    "active_permits", root, metadata=lambda: (1, "g1"),
                    fetch_page=lambda offset, limit: page(1, [row]),
                )
            self.assertEqual(corrupt.read_bytes(), b"corrupt existing snapshot")
            self.assertFalse((Path(root) / "active_permits-manifest.json").exists())
            self.assertFalse(list(Path(root).glob(".candidate-*.tmp")))

    def test_initial_empty_source_is_not_assumed_valid(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with self.assertRaisesRegex(collector.CollectionError, "Empty source result"):
                collector.collect_snapshot(
                    "active_permits", root, metadata=lambda: (0, "g1"),
                    fetch_page=lambda offset, limit: page(0, []),
                )

    def test_partial_page_preserves_previous_manifest_and_snapshot(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            first_metadata = iter([(2, "g1"), (2, "g1")])
            previous = collector.collect_snapshot(
                "active_permits", root,
                metadata=lambda: next(first_metadata),
                fetch_page=lambda offset, limit: page(2, [source_row(4), source_row(5)]),
                page_size=2,
            )
            manifest_path = Path(root) / "active_permits-manifest.json"
            old_manifest = manifest_path.read_bytes()
            old_snapshot = (Path(root) / previous["snapshot_file"]).read_bytes()

            with self.assertRaisesRegex(collector.CollectionError, "partial"):
                collector.collect_snapshot(
                    "active_permits", root,
                    metadata=lambda: (2, "g1"),
                    fetch_page=lambda offset, limit: page(2, [source_row(8)]),
                    page_size=2,
                )
            self.assertEqual(manifest_path.read_bytes(), old_manifest)
            self.assertEqual((Path(root) / previous["snapshot_file"]).read_bytes(), old_snapshot)
            self.assertFalse(list(Path(root).glob(".candidate-*.tmp")))

    def test_changed_generation_keeps_previous_good_manifest(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            metadata_values = iter([(1, "old"), (1, "old")])
            previous = collector.collect_snapshot(
                "active_permits", root,
                metadata=lambda: next(metadata_values),
                fetch_page=lambda offset, limit: page(1, [source_row(1)]),
            )
            manifest_path = Path(root) / "active_permits-manifest.json"
            old_manifest = manifest_path.read_bytes()
            metadata_values = iter([(1, "new"), (1, "newer")])
            with self.assertRaisesRegex(collector.CollectionError, "generation or count changed"):
                collector.collect_snapshot(
                    "active_permits", root,
                    metadata=lambda: next(metadata_values),
                    fetch_page=lambda offset, limit: page(1, [source_row(2)]),
                )
            self.assertEqual(manifest_path.read_bytes(), old_manifest)

    def test_row_outside_public_allowlist_is_rejected_before_snapshot_promotion(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with self.assertRaisesRegex(collector.CollectionError, "unapproved fields"):
                collector.collect_snapshot(
                    "active_permits", root,
                    metadata=lambda: (1, "g1"),
                    fetch_page=lambda offset, limit: page(1, [source_row(1, BUILDER_NAME="private")]),
                )
            self.assertFalse((Path(root) / "active_permits-manifest.json").exists())

    def test_resource_and_page_limits_fail_before_fetch(self):
        calls = []
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with self.assertRaisesRegex(collector.CollectionError, "snapshot limit"):
                collector.collect_snapshot(
                    "active_permits", root,
                    metadata=lambda: (100, "g1"),
                    fetch_page=lambda offset, limit: calls.append((offset, limit)),
                    max_rows=10,
                )
        self.assertEqual(calls, [])

    def test_snapshot_byte_limit_preserves_previous_good_manifest(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            previous = collector.collect_snapshot(
                "active_permits", root,
                metadata=lambda: (1, "g1"),
                fetch_page=lambda offset, limit: page(1, [source_row(1)]),
            )
            manifest_path = Path(root) / "active_permits-manifest.json"
            old_manifest = manifest_path.read_bytes()
            with self.assertRaisesRegex(collector.CollectionError, "byte limit"):
                collector.collect_snapshot(
                    "active_permits", root,
                    metadata=lambda: (1, "g2"),
                    fetch_page=lambda offset, limit: page(1, [source_row(2, STATUS="X" * 100)]),
                    max_snapshot_bytes=20,
                )
            self.assertEqual(manifest_path.read_bytes(), old_manifest)
            self.assertTrue((Path(root) / previous["snapshot_file"]).is_file())
            self.assertFalse(list(Path(root).glob(".candidate-*.tmp")))

    def test_unknown_source_is_rejected(self):
        with self.assertRaisesRegex(collector.CollectionError, "Unknown CKAN source"):
            collector.collect_snapshot("unreviewed_source", ".", metadata=lambda: (0, "g"), fetch_page=lambda o, l: page(0, []))

    def test_oar_source_is_a_separate_allowlisted_dataset(self):
        source = collector.SOURCE_RESOURCES["oar_address_points"]
        self.assertEqual(source["resource_id"], "0b3756af-9caf-4f0f-ac28-9c6617adede4")
        self.assertIn("geometry", source["fields"])
        self.assertNotIn("CONTACT_EMAIL", source["fields"])

    def test_permit_source_uses_live_street_components_not_nonexistent_address_fields(self):
        fields = collector.SOURCE_RESOURCES["active_permits"]["fields"]
        self.assertTrue({"STREET_NUM", "STREET_NAME", "STREET_TYPE", "STREET_DIRECTION"}.issubset(fields))
        self.assertNotIn("ADDRESS", fields)
        self.assertNotIn("APPLICATION_URL", fields)
        self.assertEqual(fields, collector.SOURCE_RESOURCES["cleared_permits_since_2017"]["fields"])


if __name__ == "__main__":
    unittest.main()

