import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

import permit_collector as collector
import permit_resumable as resumable


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
        "EST_CONST_COST": None,
        "DWELLING_UNITS_CREATED": None,
        "DWELLING_UNITS_LOST": None,
        "STREET_NUM": "1",
        "STREET_NAME": "Synthetic",
        "STREET_TYPE": "Rd",
        "STREET_DIRECTION": None,
        **extra,
    }


def response(total, records):
    return {"success": True, "result": {"total": total, "total_was_estimated": False, "records": records}}


def transient_http(code):
    return HTTPError("https://ckan0.cf.opendata.inter.prod-toronto.ca/", code, "transient", {}, None)


class InjectedCKAN:
    def __init__(self, metadata, fetch_page):
        self._metadata = metadata
        self._fetch_page = fetch_page

    def metadata(self, source_key):
        collector._safe_source(source_key)
        return self._metadata()

    def page(self, source_key, *, offset, limit):
        collector._safe_source(source_key)
        return self._fetch_page(offset, limit)


def collect_resumable_snapshot(source_key, destination, *, metadata, fetch_page, **kwargs):
    return resumable.collect_resumable_snapshot(
        source_key, destination, client=InjectedCKAN(metadata, fetch_page), **kwargs,
    )


class ResumablePermitCollectorTests(unittest.TestCase):
    def test_first_page_timeout_can_restart_when_no_rows_were_checkpointed(self):
        row = source_row(1)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with self.assertRaisesRegex(collector.CollectionError, "retry bound exhausted"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (1, "g1"),
                    fetch_page=lambda offset, limit: (_ for _ in ()).throw(TimeoutError("offline")),
                    page_size=1, retries=0,
                )
            manifest = collect_resumable_snapshot(
                "active_permits", root, metadata=lambda: (1, "g1"),
                fetch_page=lambda offset, limit: response(1, [row]),
                page_size=1,
            )
            self.assertEqual(manifest["row_count"], 1)

    def test_resumes_from_atomic_checkpoint_and_verifies_overlap(self):
        rows = [source_row(i) for i in range(1, 5)]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            first_calls = []

            def interrupted(offset, limit):
                first_calls.append((offset, limit))
                if offset == 0:
                    return response(4, rows[:2])
                raise TimeoutError("synthetic timeout")

            with self.assertRaisesRegex(collector.CollectionError, "retry bound exhausted"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (4, "g1"),
                    fetch_page=interrupted, page_size=2, overlap_rows=1, retries=0,
                )
            checkpoint_path = Path(root) / "active_permits-resume.json"
            partial_path = Path(root) / "active_permits-resume.jsonl"
            saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["next_offset"], 2)
            self.assertEqual(saved["row_count"], 2)
            old_prefix = partial_path.read_bytes()
            # Simulate a crash after append but before checkpoint replacement.
            with partial_path.open("ab") as output:
                output.write(b"uncommitted-tail")

            second_calls = []

            def resumed(offset, limit):
                second_calls.append((offset, limit))
                if offset == 1 and limit == 1:
                    return response(4, [rows[1]])
                if offset == 2 and limit == 2:
                    return response(4, rows[2:])
                raise AssertionError((offset, limit))

            manifest = collect_resumable_snapshot(
                "active_permits", root, metadata=lambda: (4, "g1"),
                fetch_page=resumed, page_size=2, overlap_rows=1, retries=0,
            )
            self.assertEqual(first_calls, [(0, 2), (2, 2)])
            self.assertEqual(second_calls, [(1, 1), (2, 2)])
            self.assertEqual(manifest["row_count"], 4)
            self.assertEqual(manifest["first_id"], 1)
            self.assertEqual(manifest["last_id"], 4)
            snapshot = Path(root) / manifest["snapshot_file"]
            self.assertEqual(len(snapshot.read_text(encoding="utf-8").splitlines()), 4)
            self.assertFalse(checkpoint_path.exists())
            self.assertFalse(partial_path.exists())
            self.assertEqual(old_prefix.count(b"\n"), 2)

    def test_resume_rejects_changed_generation_before_fetching(self):
        rows = [source_row(i) for i in range(1, 3)]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            def interrupted(offset, limit):
                if offset == 0:
                    return response(3, rows)
                raise TimeoutError("stop after checkpoint")

            with self.assertRaisesRegex(collector.CollectionError, "retry bound exhausted"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=interrupted, page_size=2, overlap_rows=1, retries=0,
                )
            calls = []
            with self.assertRaisesRegex(collector.CollectionError, "generation, count"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (3, "g2"),
                    fetch_page=lambda offset, limit: calls.append((offset, limit)),
                    page_size=2, overlap_rows=1,
                )
            self.assertEqual(calls, [])

    def test_resume_rejects_overlap_change_without_advancing_checkpoint(self):
        rows = [source_row(i) for i in range(1, 4)]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            def interrupted(offset, limit):
                if offset == 0:
                    return response(3, rows[:2])
                raise TimeoutError("stop after checkpoint")

            with self.assertRaisesRegex(collector.CollectionError, "retry bound exhausted"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=interrupted, page_size=2, overlap_rows=1, retries=0,
                )
            checkpoint_path = Path(root) / "active_permits-resume.json"
            before = checkpoint_path.read_bytes()
            changed = source_row(2, STATUS="Changed")
            with self.assertRaisesRegex(collector.CollectionError, "overlap changed"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=lambda offset, limit: response(3, [changed]),
                    page_size=2, overlap_rows=1, retries=0,
                )
            self.assertEqual(checkpoint_path.read_bytes(), before)

    def test_partial_file_corruption_fails_closed(self):
        rows = [source_row(i) for i in range(1, 3)]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            def interrupted(offset, limit):
                if offset == 0:
                    return response(3, rows)
                raise TimeoutError("stop")

            with self.assertRaisesRegex(collector.CollectionError, "retry bound exhausted"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=interrupted, page_size=2, overlap_rows=1, retries=0,
                )
            path = Path(root) / "active_permits-resume.jsonl"
            damaged = bytearray(path.read_bytes())
            damaged[0] ^= 1
            path.write_bytes(damaged)
            with self.assertRaisesRegex(collector.CollectionError, "hash"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=lambda offset, limit: response(3, rows),
                    page_size=2, overlap_rows=1, retries=0,
                )

    def test_timeout_and_502_503_504_retry_with_bounded_backoff(self):
        rows = [source_row(1)]
        for failure in (TimeoutError("timeout"), transient_http(502), transient_http(503), transient_http(504)):
            with self.subTest(failure=str(failure)), tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                calls = []
                delays = []

                def fetch(offset, limit):
                    calls.append((offset, limit))
                    if len(calls) == 1:
                        raise failure
                    return response(1, rows)

                manifest = collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: (1, "g1"),
                    fetch_page=fetch, page_size=1, overlap_rows=1, retries=1,
                    sleep=delays.append,
                )
                self.assertEqual(manifest["row_count"], 1)
                self.assertEqual(len(calls), 2)
                self.assertEqual(delays, [0.5])

    def test_401_and_403_stop_without_retry(self):
        for code in (401, 403):
            with self.subTest(status=code), tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                calls = []

                def fetch(offset, limit):
                    calls.append((offset, limit))
                    raise HTTPError("https://ckan0.cf.opendata.inter.prod-toronto.ca/", code, "denied", {}, None)

                with self.assertRaisesRegex(collector.CollectionError, f"HTTP {code}"):
                    collect_resumable_snapshot(
                        "active_permits", root, metadata=lambda: (1, "g1"),
                        fetch_page=fetch, page_size=1, retries=2,
                    )
                self.assertEqual(len(calls), 1)

    def test_out_of_order_or_duplicate_source_ids_stop_before_manifest(self):
        for ids in ([2, 1], [1, 1]):
            with self.subTest(ids=ids), tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                with self.assertRaisesRegex(collector.CollectionError, "missing, duplicated, or unordered"):
                    collect_resumable_snapshot(
                        "active_permits", root, metadata=lambda: (2, "g1"),
                        fetch_page=lambda offset, limit: response(2, [source_row(i) for i in ids]),
                        page_size=2,
                    )
                self.assertFalse((Path(root) / "active_permits-manifest.json").exists())

    def test_source_change_before_eof_preserves_last_good_manifest(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            prior = collector.collect_snapshot(
                "active_permits", root, metadata=lambda: (1, "old"),
                fetch_page=lambda offset, limit: response(1, [source_row(1)]), page_size=1,
            )
            manifest_path = Path(root) / "active_permits-manifest.json"
            before = manifest_path.read_bytes()
            metadata_values = iter([(2, "new"), (2, "newer")])
            with self.assertRaisesRegex(collector.CollectionError, "generation or count changed"):
                collect_resumable_snapshot(
                    "active_permits", root, metadata=lambda: next(metadata_values),
                    fetch_page=lambda offset, limit: response(2, [source_row(2), source_row(3)]),
                    page_size=2,
                )
            self.assertEqual(manifest_path.read_bytes(), before)
            self.assertTrue((Path(root) / prior["snapshot_file"]).is_file())


if __name__ == "__main__":
    unittest.main()
