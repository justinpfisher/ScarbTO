"""Checkpointed, read-only CKAN snapshot acquisition for permit research.

The checkpoint and partial JSONL file are local staging artifacts only. A
completed run advances the existing last-good manifest atomically; no public
export or live source request is performed by this module's tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError

import permit_collector as collector


CHECKPOINT_SCHEMA = 1
DEFAULT_RETRIES = 2
MAX_RETRIES = 2
MAX_BACKOFF_SECONDS = 5.0
DEFAULT_OVERLAP_ROWS = 3


def _canonical_row(row: dict[str, Any]) -> bytes:
    return (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _hash_prefix(path: Path, byte_count: int) -> str:
    digest = sha256()
    remaining = byte_count
    with path.open("rb") as stream:
        while remaining:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise collector.CollectionError("Resume file is shorter than its checkpoint")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def _copy_prefix_atomically(source: Path, destination: Path, byte_count: int) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=".resume-truncate-", suffix=".tmp", dir=destination.parent)
    try:
        remaining = byte_count
        with source.open("rb") as input_stream, os.fdopen(fd, "wb") as output:
            while remaining:
                chunk = input_stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise collector.CollectionError("Resume file is shorter than its checkpoint")
                output.write(chunk)
                remaining -= len(chunk)
            output.flush()
            os.fsync(output.fileno())
        os.replace(tmp_name, destination)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, URLError):
        return isinstance(exc.reason, TimeoutError) or "timed out" in str(exc.reason).lower()
    if isinstance(exc, collector.CollectionError):
        return "timed out" in str(exc).lower()
    return False


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, HTTPError):
        return exc.code in {502, 503, 504}
    if _is_timeout(exc):
        return True
    if isinstance(exc, collector.CollectionError):
        return any(str(exc).startswith(f"CKAN returned HTTP {status}") for status in (502, 503, 504))
    return False


def _retry_delay(exc: BaseException, attempt: int) -> float:
    if isinstance(exc, HTTPError):
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        if retry_after is not None:
            try:
                return min(MAX_BACKOFF_SECONDS, max(0.0, float(retry_after)))
            except ValueError:
                pass
    return min(MAX_BACKOFF_SECONDS, 0.5 * (2 ** attempt))


def _fetch_with_backoff(
    fetch_page: Callable[[int, int], dict[str, Any]],
    offset: int,
    limit: int,
    *,
    retries: int,
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    for attempt in range(retries + 1):
        try:
            return fetch_page(offset, limit)
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise collector.CollectionError(f"CKAN access denied (HTTP {exc.code}); resume stopped") from exc
            if not _retryable(exc) or attempt >= retries:
                if _retryable(exc):
                    raise collector.CollectionError(f"CKAN retry bound exhausted (HTTP {exc.code})") from exc
                raise
            sleep(_retry_delay(exc, attempt))
        except Exception as exc:
            message = str(exc).lower()
            if "http 401" in message or "http 403" in message or "access denied" in message:
                raise collector.CollectionError("CKAN access denied; resume stopped") from exc
            if not _retryable(exc) or attempt >= retries:
                if _retryable(exc):
                    raise collector.CollectionError("CKAN retry bound exhausted after timeout/transient failure") from exc
                raise
            sleep(_retry_delay(exc, attempt))
    raise collector.CollectionError("CKAN retry bound exhausted")


def _load_checkpoint(path: Path) -> dict[str, Any]:
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise collector.CollectionError("Resume checkpoint is unreadable") from exc
    if not isinstance(checkpoint, dict) or checkpoint.get("schema_version") != CHECKPOINT_SCHEMA:
        raise collector.CollectionError("Resume checkpoint schema is invalid")
    return checkpoint


def _validated_previous_manifest(root: Path, source_key: str) -> tuple[dict[str, Any] | None, int | None]:
    path = root / f"{source_key}-manifest.json"
    if not path.exists():
        return None, None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise collector.CollectionError("Existing last-good manifest is unreadable") from exc
    if not isinstance(manifest, dict) or manifest.get("source_key") != source_key:
        raise collector.CollectionError("Existing last-good manifest is malformed")
    count = manifest.get("row_count")
    name = manifest.get("snapshot_file")
    if type(count) is not int or count < 0 or not isinstance(name, str) or Path(name).name != name:
        raise collector.CollectionError("Existing last-good manifest is malformed")
    prior_snapshot = root / name
    if not prior_snapshot.is_file() or collector._file_sha256(prior_snapshot) != manifest.get("sha256"):
        raise collector.CollectionError("Existing last-good snapshot is missing or corrupt")
    return manifest, count


def collect_resumable_snapshot(
    source_key: str,
    destination: str | Path,
    *,
    client: Any,
    page_size: int = collector.DEFAULT_PAGE_SIZE,
    max_rows: int = collector.MAX_ROWS,
    max_pages: int = collector.MAX_PAGES,
    max_snapshot_bytes: int = collector.MAX_SNAPSHOT_BYTES,
    overlap_rows: int = DEFAULT_OVERLAP_ROWS,
    retries: int = DEFAULT_RETRIES,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Acquire one complete snapshot with atomic page checkpoints and safe resume.

    `client` must provide the existing `TorontoCKAN.metadata(source_key)` and
    `.page(source_key, offset=..., limit=...)` interface. That binds each page
    to the fixed source resource and explicit source-specific field projection.
    Only timeout and 502/503/504 errors retry; 401/403, schema failures, source
    changes, and overlap mismatches stop immediately.
    """
    source = collector._safe_source(source_key)
    if not callable(getattr(client, "metadata", None)) or not callable(getattr(client, "page", None)):
        raise collector.CollectionError("Resumable collection requires the qualified CKAN client interface")
    if type(page_size) is not int or not 1 <= page_size <= collector.MAX_PAGE_SIZE:
        raise collector.CollectionError("Page size exceeds the qualified maximum")
    if type(overlap_rows) is not int or not 1 <= overlap_rows <= collector.MAX_PAGE_SIZE:
        raise collector.CollectionError("Resume overlap is outside the bounded range")
    overlap_limit = min(overlap_rows, page_size)
    if type(retries) is not int or not 0 <= retries <= MAX_RETRIES:
        raise collector.CollectionError("Retry count exceeds the bounded maximum")
    if type(max_rows) is not int or max_rows < 0 or type(max_pages) is not int or max_pages < 1:
        raise collector.CollectionError("Invalid source row/page limit")
    if type(max_snapshot_bytes) is not int or max_snapshot_bytes < 1:
        raise collector.CollectionError("Invalid snapshot byte limit")

    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    partial_path = root / f"{source_key}-resume.jsonl"
    checkpoint_path = root / f"{source_key}-resume.json"
    manifest_path = root / f"{source_key}-manifest.json"
    total, generation = client.metadata(source_key)
    if type(total) is not int or not 0 <= total <= max_rows:
        raise collector.CollectionError("Source count is estimated, malformed, or exceeds the configured limit")
    if not isinstance(generation, str) or not generation.strip():
        raise collector.CollectionError("Source generation marker is empty")
    if (total + page_size - 1) // page_size > max_pages:
        raise collector.CollectionError("Source count exceeds the configured page limit")
    previous_manifest, previous_count = _validated_previous_manifest(root, source_key)
    if total == 0 and (previous_count is None or previous_count > 0):
        raise collector.CollectionError("Empty source result is not accepted without a qualified empty-source policy")
    if previous_count and total < previous_count * source["minimum_row_retention"]:
        raise collector.CollectionError("Source row count fell below its source-specific retention floor")

    if checkpoint_path.exists():
        checkpoint = _load_checkpoint(checkpoint_path)
        expected = {
            "source_key": source_key,
            "resource_id": source["resource_id"],
            "generation": generation,
            "total": total,
            "page_size": page_size,
            "overlap_rows": overlap_limit,
        }
        if any(checkpoint.get(key) != value for key, value in expected.items()):
            raise collector.CollectionError("Source resource, generation, count, or page size changed since checkpoint")
        offset = checkpoint.get("next_offset")
        row_count = checkpoint.get("row_count")
        byte_count = checkpoint.get("byte_count")
        prefix_hash = checkpoint.get("sha256")
        last_id = checkpoint.get("last_id")
        overlap = checkpoint.get("overlap")
        if (
            type(offset) is not int or offset < 0 or offset > total
            or offset != row_count
            or type(row_count) is not int
            or type(byte_count) is not int or byte_count < 0
            or byte_count > max_snapshot_bytes or row_count > max_rows
            or not isinstance(prefix_hash, str)
            or (last_id is not None and (type(last_id) is not int or last_id <= 0))
            or not isinstance(overlap, list) or len(overlap) > min(overlap_limit, row_count)
            or not partial_path.is_file()
        ):
            raise collector.CollectionError("Resume checkpoint fields are malformed")
        if partial_path.stat().st_size < byte_count or _hash_prefix(partial_path, byte_count) != prefix_hash:
            raise collector.CollectionError("Resume partial file hash does not match its checkpoint")
        if partial_path.stat().st_size > byte_count:
            # Discard only bytes written after the last atomic checkpoint.
            _copy_prefix_atomically(partial_path, partial_path, byte_count)
        if offset:
            expected_overlap = overlap
            overlap_offset = offset - len(expected_overlap)
            if not expected_overlap:
                raise collector.CollectionError("Resume checkpoint has no overlap proof")
            response = _fetch_with_backoff(
                lambda offset, limit: client.page(source_key, offset=offset, limit=limit),
                overlap_offset, len(expected_overlap), retries=retries, sleep=sleep,
            )
            result = collector._validate_response(response, fields=source["fields"], required_fields=source["required_fields"], limit=page_size)
            if result["total"] != total or len(result["records"]) != len(expected_overlap):
                raise collector.CollectionError("Resume overlap page does not match the checkpoint count")
            actual = [{"id": row.get("_id"), "sha256": sha256(_canonical_row(row)).hexdigest()} for row in result["records"]]
            if actual != expected_overlap:
                raise collector.CollectionError("Resume overlap changed; refusing to join source generations")
    else:
        if partial_path.exists():
            # A completed run can be interrupted after the manifest update but
            # before cleanup. Only remove its partial if it exactly matches the
            # now-active content-addressed snapshot.
            if partial_path.stat().st_size == 0:
                partial_path.unlink()
            elif previous_manifest and collector._file_sha256(partial_path) == previous_manifest.get("sha256"):
                partial_path.unlink()
            else:
                raise collector.CollectionError("Uncheckpointed partial source file exists")
        offset = 0
        row_count = 0
        byte_count = 0
        prefix_hash = sha256(b"").hexdigest()
        last_id = None
        overlap = []
        partial_path.touch(exist_ok=False)

    while offset < total:
        request_limit = min(page_size, total - offset)
        response = _fetch_with_backoff(
            lambda page_offset, limit: client.page(source_key, offset=page_offset, limit=limit),
            offset, request_limit, retries=retries, sleep=sleep,
        )
        result = collector._validate_response(response, fields=source["fields"], required_fields=source["required_fields"], limit=page_size)
        if result["total"] != total:
            raise collector.CollectionError("Source total changed during resumed pagination")
        records = result["records"]
        if len(records) != request_limit:
            raise collector.CollectionError("Unexpected empty, partial, or truncated page")
        encoded_rows = []
        next_overlap = []
        prior_id = last_id or 0
        for row in records:
            row_id = row.get("_id")
            if type(row_id) is not int or row_id <= prior_id:
                raise collector.CollectionError("Source row IDs are missing, duplicated, or unordered")
            prior_id = row_id
            encoded = _canonical_row(row)
            encoded_rows.append(encoded)
            next_overlap.append({"id": row_id, "sha256": sha256(encoded).hexdigest()})
        added = sum(len(item) for item in encoded_rows)
        if byte_count + added > max_snapshot_bytes:
            raise collector.CollectionError("Snapshot exceeds the configured byte limit")
        with partial_path.open("ab") as output:
            for encoded in encoded_rows:
                output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        row_count += len(records)
        offset += len(records)
        byte_count += added
        last_id = prior_id
        overlap = (overlap + next_overlap)[-overlap_limit:]
        prefix_hash = collector._file_sha256(partial_path)
        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA,
            "source_key": source_key,
            "resource_id": source["resource_id"],
            "generation": generation,
            "total": total,
            "page_size": page_size,
            "overlap_rows": overlap_limit,
            "next_offset": offset,
            "row_count": row_count,
            "last_id": last_id,
            "byte_count": byte_count,
            "sha256": prefix_hash,
            "overlap": overlap,
        }
        collector._atomic_write_text(checkpoint_path, json.dumps(checkpoint, sort_keys=True, separators=(",", ":")) + "\n")

    total_after, generation_after = client.metadata(source_key)
    if total_after != total or generation_after != generation:
        raise collector.CollectionError("Source generation or count changed before EOF certification")
    if row_count != total or partial_path.stat().st_size != byte_count or collector._file_sha256(partial_path) != prefix_hash:
        raise collector.CollectionError("Completed resume candidate failed final count/hash certification")
    if offset and (last_id is None or not overlap):
        raise collector.CollectionError("Completed snapshot is missing final source-ID proof")

    content_hash = prefix_hash
    snapshot_name = f"{source_key}-{content_hash}.jsonl"
    snapshot_path = root / snapshot_name
    if snapshot_path.exists():
        if not snapshot_path.is_file() or collector._file_sha256(snapshot_path) != content_hash:
            raise collector.CollectionError("Existing content-addressed snapshot is corrupt")
    else:
        fd, temp_name = tempfile.mkstemp(prefix=".resume-final-", suffix=".tmp", dir=root)
        try:
            with partial_path.open("rb") as input_stream, os.fdopen(fd, "wb") as output:
                while True:
                    chunk = input_stream.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp_name, snapshot_path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
    first_id = None
    if row_count:
        with snapshot_path.open("rb") as input_stream:
            first_line = input_stream.readline()
        first_id = json.loads(first_line).get("_id")
    manifest = {
        "schema_version": 1,
        "source_key": source_key,
        "resource_id": source["resource_id"],
        "generation": generation,
        "row_count": row_count,
        "first_id": first_id,
        "last_id": last_id,
        "sha256": content_hash,
        "snapshot_file": snapshot_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "publication_status": "disabled_pending_source_geography_and_privacy_review",
    }
    collector._atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    checkpoint_path.unlink(missing_ok=True)
    partial_path.unlink(missing_ok=True)
    return manifest
