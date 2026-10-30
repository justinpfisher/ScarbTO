import json
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

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
    return HTTPError(
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/datastore_search",
        code, f"synthetic HTTP {code}", hdrs={}, fp=None,
    )


class InjectedCKAN:
    """Injected logical client for checkpoint-state tests; no network access."""
    def __init__(self, metadata, fetch_page, *, eof_records=None):
        self._metadata = metadata
        self._fetch_page = fetch_page
        self._eof_records = eof_records or []
        self.total = None
        self.calls = []

    def metadata(self, source_key):
        collector._safe_source(source_key)
        self.total, generation = self._metadata()
        return self.total, generation

    def page(self, source_key, *, offset, limit):
        collector._safe_source(source_key)
        self.calls.append((offset, limit))
        if offset == self.total:
            return response(self.total, self._eof_records)
        return self._fetch_page(offset, limit)


def collect(source_key, destination, *, metadata, fetch_page, eof_records=None, **kwargs):
    client = InjectedCKAN(metadata, fetch_page, eof_records=eof_records)
    return resumable.collect_resumable_snapshot(source_key, destination, client=client, **kwargs)


class JsonResponse:
    def __init__(self, payload, url):
        self._body = json.dumps(payload).encode("utf-8")
        self._offset = 0
        self.headers = {}
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return self.url

    def read(self, limit=-1):
        if limit < 0:
            result = self._body[self._offset:]
            self._offset = len(self._body)
            return result
        result = self._body[self._offset:self._offset + limit]
        self._offset += len(result)
        return result


class InjectedHTTPTransport:
    """Transport seam for the actual TorontoCKAN URL/schema/retry implementation."""
    def __init__(self, rows, failures=None, action_failures=None):
        self.rows = rows
        self.failures = failures or {}
        self.action_failures = action_failures or {}
        self.page_calls = []
        self.calls = []

    def __call__(self, request, *, timeout):
        url = request.full_url
        self.calls.append((url, timeout))
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        action = parsed.path.rsplit("/", 1)[-1]
        action_failures = self.action_failures.get(action, [])
        if action_failures:
            raise action_failures.pop(0)
        if action == "package_show":
            resource = collector.SOURCE_RESOURCES["active_permits"]
            payload = {
                "success": True,
                "result": {
                    "metadata_modified": "package-generation",
                    "resources": [{"id": resource["resource_id"], "last_modified": "resource-generation"}],
                },
            }
            return JsonResponse(payload, url)
        if action != "datastore_search":
            raise AssertionError(action)
        offset = int(query.get("offset", ["0"])[0])
        limit = int(query["limit"][0])
        if limit == 0:
            return JsonResponse(response(len(self.rows), []), url)
        self.page_calls.append((offset, limit))
        failures = self.failures.get(offset, [])
        if failures:
            raise failures.pop(0)
        return JsonResponse(response(len(self.rows), self.rows[offset:offset + limit]), url)


def seeded_empty_manifest(root):
    source_key = "active_permits"
    digest = sha256(b"").hexdigest()
    name = f"{source_key}-{digest}.jsonl"
    (Path(root) / name).write_bytes(b"")
    manifest = {
        "schema_version": 1,
        "source_key": source_key,
        "row_count": 0,
        "sha256": digest,
        "snapshot_file": name,
    }
    collector._atomic_write_text(Path(root) / f"{source_key}-manifest.json", json.dumps(manifest))


class ResumablePermitCollectorTests(unittest.TestCase):
    def test_first_page_timeout_can_restart_when_no_rows_were_checkpointed(self):
        row = source_row(1)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            with self.assertRaisesRegex(TimeoutError, "offline"):
                collect(
                    "active_permits", root, metadata=lambda: (1, "g1"),
                    fetch_page=lambda offset, limit: (_ for _ in ()).throw(TimeoutError("offline")),
                    page_size=1,
                )
            manifest = collect(
                "active_permits", root, metadata=lambda: (1, "g1"),
                fetch_page=lambda offset, limit: response(1, [row]),
                page_size=1,
            )
            self.assertEqual(manifest["row_count"], 1)

    def test_resumes_from_atomic_checkpoint_verifies_overlap_and_truncates_uncommitted_tail(self):
        rows = [source_row(i) for i in range(1, 5)]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            first_calls = []

            def interrupted(offset, limit):
                first_calls.append((offset, limit))
                if offset == 0:
                    return response(4, rows[:2])
                raise TimeoutError("synthetic timeout")

            with self.assertRaisesRegex(TimeoutError, "synthetic timeout"):
                collect(
                    "active_permits", root, metadata=lambda: (4, "g1"),
                    fetch_page=interrupted, page_size=2, overlap_rows=1,
                )
            checkpoint_path = Path(root) / "active_permits-resume.json"
            partial_path = Path(root) / "active_permits-resume.jsonl"
            saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["next_offset"], 2)
            self.assertEqual(saved["row_count"], 2)
            old_prefix = partial_path.read_bytes()
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

            manifest = collect(
                "active_permits", root, metadata=lambda: (4, "g1"),
                fetch_page=resumed, page_size=2, overlap_rows=1,
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

    def test_stale_generation_quarantines_and_restarts_without_losing_last_good_on_failure(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            prior_rows = [source_row(i, STATUS="Prior") for i in range(1, 3)]
            prior = collector.collect_snapshot(
                "active_permits", root, metadata=lambda: (2, "prior"),
                fetch_page=lambda offset, limit: response(2, prior_rows[offset:offset + limit]),
                page_size=2,
            )
            manifest_path = Path(root) / "active_permits-manifest.json"
            last_good_manifest = manifest_path.read_bytes()
            last_good_snapshot = Path(root) / prior["snapshot_file"]

            generation_a = [source_row(i, STATUS="Generation A") for i in range(1, 5)]

            def interrupted_a(offset, limit):
                if offset == 0:
                    return response(4, generation_a[:2])
                raise TimeoutError("stop after checkpoint")

            with self.assertRaisesRegex(TimeoutError, "stop after checkpoint"):
                collect(
                    "active_permits", root, metadata=lambda: (4, "generation-a"),
                    fetch_page=interrupted_a, page_size=2, overlap_rows=1,
                )

            checkpoint_path = Path(root) / "active_permits-resume.json"
            partial_path = Path(root) / "active_permits-resume.jsonl"
            checkpoint_a = checkpoint_path.read_bytes()
            partial_a = partial_path.read_bytes()
            generation_b = [source_row(i, STATUS="Generation B") for i in range(1, 5)]
            failed_b_calls = []

            def fail_b(offset, limit):
                failed_b_calls.append((offset, limit))
                if offset == 0:
                    return response(4, generation_b[:2])
                raise TimeoutError("generation B interrupted")

            with self.assertRaisesRegex(TimeoutError, "generation B interrupted"):
                collect(
                    "active_permits", root, metadata=lambda: (4, "generation-b"),
                    fetch_page=fail_b, page_size=2, overlap_rows=1,
                )

            self.assertEqual(failed_b_calls, [(0, 2), (2, 2)])
            self.assertEqual(manifest_path.read_bytes(), last_good_manifest)
            self.assertTrue(last_good_snapshot.is_file())
            checkpoint_b = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint_b["generation"], "generation-b")
            self.assertEqual(checkpoint_b["next_offset"], 2)
            self.assertEqual(
                [json.loads(line) for line in partial_path.read_text(encoding="utf-8").splitlines()],
                generation_b[:2],
            )
            quarantine_files = list((Path(root) / "active_permits-stale").iterdir())
            self.assertEqual(len(quarantine_files), 2)
            checkpoint_backup = next(path for path in quarantine_files if path.name.endswith(".json"))
            prefix_backup = next(path for path in quarantine_files if path.name.endswith(".jsonl"))
            self.assertEqual(checkpoint_backup.read_bytes(), checkpoint_a)
            self.assertEqual(prefix_backup.read_bytes(), partial_a)

            resumed_calls = []

            def resume_b(offset, limit):
                resumed_calls.append((offset, limit))
                if offset == 1 and limit == 1:
                    return response(4, [generation_b[1]])
                if offset == 2 and limit == 2:
                    return response(4, generation_b[2:])
                raise AssertionError((offset, limit))

            manifest = collect(
                "active_permits", root, metadata=lambda: (4, "generation-b"),
                fetch_page=resume_b, page_size=2, overlap_rows=1,
            )
            self.assertEqual(resumed_calls, [(1, 1), (2, 2)])
            self.assertEqual(manifest["row_count"], 4)
            self.assertEqual(manifest["generation"], "generation-b")
            self.assertNotEqual(manifest_path.read_bytes(), last_good_manifest)
            self.assertTrue(last_good_snapshot.is_file())
            rows = [json.loads(line) for line in (Path(root) / manifest["snapshot_file"]).read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows, generation_b)

    def test_stale_checkpoint_with_corrupt_prefix_fails_closed_without_quarantine(self):
        rows = [source_row(i) for i in range(1, 3)]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            def interrupted(offset, limit):
                if offset == 0:
                    return response(3, rows)
                raise TimeoutError("stop after checkpoint")

            with self.assertRaisesRegex(TimeoutError, "stop after checkpoint"):
                collect(
                    "active_permits", root, metadata=lambda: (3, "generation-a"),
                    fetch_page=interrupted, page_size=2, overlap_rows=1,
                )
            partial_path = Path(root) / "active_permits-resume.jsonl"
            damaged = bytearray(partial_path.read_bytes())
            damaged[0] ^= 1
            partial_path.write_bytes(damaged)
            checkpoint_before = (Path(root) / "active_permits-resume.json").read_bytes()
            calls = []
            with self.assertRaisesRegex(collector.CollectionError, "hash"):
                collect(
                    "active_permits", root, metadata=lambda: (3, "generation-b"),
                    fetch_page=lambda offset, limit: calls.append((offset, limit)),
                    page_size=2, overlap_rows=1,
                )
            self.assertEqual(calls, [])
            self.assertEqual((Path(root) / "active_permits-resume.json").read_bytes(), checkpoint_before)
            quarantine_dir = Path(root) / "active_permits-stale"
            self.assertEqual(list(quarantine_dir.glob("*")) if quarantine_dir.exists() else [], [])

    def test_zero_row_generation_churn_counts_quarantined_checkpoint_metadata(self):
        row = source_row(1, STATUS="Generation X")
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            def interrupt_x(offset, limit):
                if offset == 0:
                    return response(2, [row])
                raise TimeoutError("generation X interrupted")

            with self.assertRaisesRegex(TimeoutError, "generation X interrupted"):
                collect(
                    "active_permits", root, metadata=lambda: (2, "generation-x"),
                    fetch_page=interrupt_x, page_size=1, overlap_rows=1,
                    max_snapshot_bytes=10_000,
                )

            def interrupt_a(offset, limit):
                raise TimeoutError("generation A interrupted before its first page")

            with self.assertRaisesRegex(TimeoutError, "generation A interrupted"):
                collect(
                    "active_permits", root, metadata=lambda: (2, "generation-a"),
                    fetch_page=interrupt_a, page_size=1, overlap_rows=1,
                    max_snapshot_bytes=10_000,
                )

            quarantine_dir = Path(root) / "active_permits-stale"
            entries_before_b = list(quarantine_dir.iterdir())
            self.assertEqual(len(entries_before_b), 2)
            quarantined_bytes = sum(path.stat().st_size for path in entries_before_b)
            checkpoint_path = Path(root) / "active_permits-resume.json"
            partial_path = Path(root) / "active_permits-resume.jsonl"
            checkpoint_a = checkpoint_path.read_bytes()
            self.assertEqual(partial_path.stat().st_size, 0)

            b_page_calls = []
            with self.assertRaisesRegex(collector.CollectionError, "bounded storage limit"):
                collect(
                    "active_permits", root, metadata=lambda: (2, "generation-b"),
                    fetch_page=lambda offset, limit: b_page_calls.append((offset, limit)),
                    page_size=1, overlap_rows=1,
                    max_snapshot_bytes=quarantined_bytes + len(checkpoint_a) - 1,
                )

            self.assertEqual(b_page_calls, [])
            self.assertEqual(checkpoint_path.read_bytes(), checkpoint_a)
            self.assertEqual(partial_path.stat().st_size, 0)
            self.assertEqual(list(quarantine_dir.iterdir()), entries_before_b)

    def test_resume_rejects_overlap_change_without_advancing_checkpoint(self):
        rows = [source_row(i) for i in range(1, 4)]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            def interrupted(offset, limit):
                if offset == 0:
                    return response(3, rows[:2])
                raise TimeoutError("stop after checkpoint")

            with self.assertRaisesRegex(TimeoutError, "stop after checkpoint"):
                collect(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=interrupted, page_size=2, overlap_rows=1,
                )
            checkpoint_path = Path(root) / "active_permits-resume.json"
            before = checkpoint_path.read_bytes()
            changed = source_row(2, STATUS="Changed")
            with self.assertRaisesRegex(collector.CollectionError, "overlap changed"):
                collect(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=lambda offset, limit: response(3, [changed]),
                    page_size=2, overlap_rows=1,
                )
            self.assertEqual(checkpoint_path.read_bytes(), before)

    def test_partial_file_corruption_fails_closed(self):
        rows = [source_row(i) for i in range(1, 3)]
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            def interrupted(offset, limit):
                if offset == 0:
                    return response(3, rows)
                raise TimeoutError("stop")

            with self.assertRaisesRegex(TimeoutError, "stop"):
                collect(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=interrupted, page_size=2, overlap_rows=1,
                )
            path = Path(root) / "active_permits-resume.jsonl"
            damaged = bytearray(path.read_bytes())
            damaged[0] ^= 1
            path.write_bytes(damaged)
            with self.assertRaisesRegex(collector.CollectionError, "hash"):
                collect(
                    "active_permits", root, metadata=lambda: (3, "g1"),
                    fetch_page=lambda offset, limit: response(3, rows),
                    page_size=2, overlap_rows=1,
                )

    def test_eof_page_is_requested_and_extra_record_fails_closed(self):
        row = source_row(1)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            prior = collector.collect_snapshot(
                "active_permits", root, metadata=lambda: (1, "prior"),
                fetch_page=lambda offset, limit: response(1, [row]), page_size=1,
            )
            manifest_path = Path(root) / "active_permits-manifest.json"
            previous_manifest = manifest_path.read_bytes()
            client = InjectedCKAN(
                lambda: (1, "g1"),
                lambda offset, limit: response(1, [source_row(2)]),
                eof_records=[source_row(2)],
            )
            with self.assertRaisesRegex(collector.CollectionError, "EOF certification"):
                resumable.collect_resumable_snapshot("active_permits", root, client=client, page_size=1)
            self.assertEqual(client.calls, [(0, 1), (1, 1)])
            self.assertEqual(manifest_path.read_bytes(), previous_manifest)
            self.assertTrue((Path(root) / prior["snapshot_file"]).is_file())

    def test_empty_source_still_requires_and_checks_zero_offset_eof(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            seeded_empty_manifest(root)
            client = InjectedCKAN(lambda: (0, "g0"), lambda offset, limit: self.fail("No data page expected"))
            result = resumable.collect_resumable_snapshot("active_permits", root, client=client, page_size=1)
            self.assertEqual(result["row_count"], 0)
            self.assertEqual(client.calls, [(0, 1)])

    def test_zero_total_eof_extra_record_fails_without_advancing_manifest(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            seeded_empty_manifest(root)
            manifest_path = Path(root) / "active_permits-manifest.json"
            previous = manifest_path.read_bytes()
            client = InjectedCKAN(
                lambda: (0, "g0"), lambda offset, limit: self.fail("No data page expected"),
                eof_records=[source_row(1)],
            )
            with self.assertRaisesRegex(collector.CollectionError, "EOF certification"):
                resumable.collect_resumable_snapshot("active_permits", root, client=client, page_size=1)
            self.assertEqual(client.calls, [(0, 1)])
            self.assertEqual(manifest_path.read_bytes(), previous)

    def test_out_of_order_or_duplicate_source_ids_stop_before_manifest(self):
        for ids in ([2, 1], [1, 1]):
            with self.subTest(ids=ids), tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                with self.assertRaisesRegex(collector.CollectionError, "missing, duplicated, or unordered"):
                    collect(
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
                collect(
                    "active_permits", root, metadata=lambda: next(metadata_values),
                    fetch_page=lambda offset, limit: response(2, [source_row(2), source_row(3)]),
                    page_size=2,
                )
            self.assertEqual(manifest_path.read_bytes(), before)
            self.assertTrue((Path(root) / prior["snapshot_file"]).is_file())

    def test_real_ckan_client_owns_exact_retry_budget_and_status_scope(self):
        row = source_row(1)
        for failure in (TimeoutError("timeout"), transient_http(502), transient_http(503), transient_http(504)):
            with self.subTest(failure=str(failure)), tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                transport = InjectedHTTPTransport([row], failures={0: [failure]})
                delays = []
                client = collector.TorontoCKAN(retries=1, sleep=delays.append, opener=transport)
                manifest = resumable.collect_resumable_snapshot("active_permits", root, client=client, page_size=1)
                self.assertEqual(manifest["row_count"], 1)
                self.assertEqual(transport.page_calls, [(0, 1), (0, 1), (1, 1)])
                self.assertEqual(delays, [0.5])

    def test_actual_package_metadata_request_uses_same_single_retry_owner(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            transport = InjectedHTTPTransport(
                [source_row(1)], action_failures={"package_show": [TimeoutError("metadata timeout")]},
            )
            delays = []
            client = collector.TorontoCKAN(retries=1, sleep=delays.append, opener=transport)
            manifest = resumable.collect_resumable_snapshot("active_permits", root, client=client, page_size=1)
            package_requests = [url for url, _ in transport.calls if urlparse(url).path.endswith("/package_show")]
            self.assertEqual(manifest["row_count"], 1)
            # Initial metadata retries once; final generation verification makes
            # one additional package_show request without another failure.
            self.assertEqual(len(package_requests), 3)
            self.assertEqual(delays, [0.5])

    def test_metadata_retry_zero_makes_one_request(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
            transport = InjectedHTTPTransport(
                [source_row(1)], action_failures={"package_show": [transient_http(502), transient_http(502)]},
            )
            delays = []
            client = collector.TorontoCKAN(retries=0, sleep=delays.append, opener=transport)
            with self.assertRaises(collector.CollectionError):
                resumable.collect_resumable_snapshot("active_permits", root, client=client, page_size=1)
            package_requests = [url for url, _ in transport.calls if urlparse(url).path.endswith("/package_show")]
            self.assertEqual(len(package_requests), 1)
            self.assertEqual(transport.page_calls, [])
            self.assertEqual(delays, [])

    def test_retry_zero_means_one_request_and_401_403_429_other_url_errors_do_not_retry(self):
        row = source_row(1)
        cases = [
            (502, transient_http(502)),
            (401, transient_http(401)),
            (403, transient_http(403)),
            (429, transient_http(429)),
            ("url-error", URLError("connection reset")),
        ]
        for name, failure in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                transport = InjectedHTTPTransport([row], failures={0: [failure, failure]})
                delays = []
                client = collector.TorontoCKAN(retries=0, sleep=delays.append, opener=transport)
                with self.assertRaises(collector.CollectionError):
                    resumable.collect_resumable_snapshot("active_permits", root, client=client, page_size=1)
                self.assertEqual(transport.page_calls, [(0, 1)])
                self.assertEqual(delays, [])

    def test_auth_and_nonretryable_failures_stop_immediately_with_retry_budget_available(self):
        cases = [
            ("401", transient_http(401)),
            ("403", transient_http(403)),
            ("429", transient_http(429)),
            ("generic-url-error", URLError("connection reset")),
        ]
        for name, failure in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory(dir=Path.cwd()) as root:
                transport = InjectedHTTPTransport([source_row(1)], failures={0: [failure, failure]})
                delays = []
                client = collector.TorontoCKAN(retries=2, sleep=delays.append, opener=transport)
                with self.assertRaises(collector.CollectionError):
                    resumable.collect_resumable_snapshot("active_permits", root, client=client, page_size=1)
                self.assertEqual(transport.page_calls, [(0, 1)])
                self.assertEqual(delays, [])


if __name__ == "__main__":
    unittest.main()


