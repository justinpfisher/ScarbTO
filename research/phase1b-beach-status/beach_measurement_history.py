"""Bounded validator for Toronto's licensed beach-sample history dataset.

This module is deliberately separate from the SwimSafe advisory adapter:
numeric measurements never become current safety labels. It has no scheduler,
network access, or public publisher. Callers provide bounded CKAN pages.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable
from urllib.parse import urlencode


API_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/"
API_HOST = "ckan0.cf.opendata.inter.prod-toronto.ca"
RESOURCE_ID = "8102bd4c-83cd-4354-9788-eecc0c7a09b4"
PACKAGE_ID = "92b0de8f-1ada-44a7-84cf-adc04868e990"
BEACH_ID = 10
FIELDS = ("_id", "beachId", "beachName", "siteName", "collectionDate", "eColi")
MAX_PAGE_SIZE = 2000
MAX_ROWS = 20_000
MAX_PAGES = 100
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024


class BeachHistoryError(ValueError):
    """A catalogue response did not qualify as a complete sample snapshot."""


def query_url(*, offset: int, limit: int) -> str:
    if type(offset) is not int or offset < 0:
        raise BeachHistoryError("offset must be a nonnegative integer")
    if type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
        raise BeachHistoryError("limit exceeds the bounded page size")
    params = {
        "resource_id": RESOURCE_ID,
        "limit": limit,
        "offset": offset,
        "fields": ",".join(FIELDS),
        "filters": json.dumps({"beachId": BEACH_ID}, separators=(",", ":")),
        "sort": "_id asc",
    }
    return API_BASE + "datastore_search?" + urlencode(params)


def _validate_generation(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BeachHistoryError(f"{label} generation marker is missing")
    return value


def validate_page(payload: Any, *, limit: int) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise BeachHistoryError("CKAN response is not successful")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise BeachHistoryError("CKAN result object is missing")
    if result.get("resource_id") != RESOURCE_ID:
        raise BeachHistoryError("CKAN returned an unexpected resource")
    filters = result.get("filters")
    if not isinstance(filters, dict) or filters.get("beachId") not in (10, "10"):
        raise BeachHistoryError("CKAN response does not confirm the beach filter")
    if result.get("total_was_estimated") is not False:
        raise BeachHistoryError("CKAN total is estimated or lacks an exactness flag")
    total = result.get("total")
    records = result.get("records")
    if type(total) is not int or not 0 <= total <= MAX_ROWS:
        raise BeachHistoryError("CKAN total exceeds the configured snapshot bound")
    if not isinstance(records, list) or len(records) > limit:
        raise BeachHistoryError("CKAN records are malformed or exceed page limit")
    normalized = []
    for row in records:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise BeachHistoryError("CKAN sample row does not match the exact field allowlist")
        if type(row["_id"]) is not int or row["_id"] < 1:
            raise BeachHistoryError("CKAN sample row ID is invalid")
        if type(row["beachId"]) is not int or row["beachId"] != BEACH_ID:
            raise BeachHistoryError("CKAN sample row is for an unexpected beach")
        for field in ("beachName", "siteName"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise BeachHistoryError(f"CKAN {field} is missing")
        sample_day = row["collectionDate"]
        if not isinstance(sample_day, str):
            raise BeachHistoryError("collectionDate must be an ISO calendar date")
        try:
            parsed_day = date.fromisoformat(sample_day)
        except ValueError as exc:
            raise BeachHistoryError("collectionDate must be an ISO calendar date") from exc
        if parsed_day.isoformat() != sample_day:
            raise BeachHistoryError("collectionDate must not contain a time or offset")
        measurement = row["eColi"]
        if measurement is not None and (type(measurement) is not int or measurement < 0):
            raise BeachHistoryError("eColi must be a nonnegative integer or null")
        normalized.append(dict(row))
    return {"total": total, "records": normalized}


def build_complete_snapshot(
    pages: Iterable[dict[str, Any]],
    *,
    total_before: int,
    generation_before: str,
    total_after: int,
    generation_after: str,
    page_size: int,
    retrieved_at: datetime,
) -> dict[str, Any]:
    """Build only after exact, contiguous pages and unchanged source metadata."""
    if type(total_before) is not int or not 0 <= total_before <= MAX_ROWS:
        raise BeachHistoryError("initial exact total exceeds snapshot bound")
    if type(total_after) is not int or total_after != total_before:
        raise BeachHistoryError("source total changed during pagination")
    if _validate_generation(generation_before, "initial") != _validate_generation(generation_after, "final"):
        raise BeachHistoryError("source generation changed during pagination")
    if not isinstance(retrieved_at, datetime) or retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise BeachHistoryError("retrieval timestamp must be timezone-aware")
    if type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise BeachHistoryError("page size exceeds configured maximum")
    expected_pages = (total_before + page_size - 1) // page_size
    if expected_pages > MAX_PAGES:
        raise BeachHistoryError("snapshot exceeds configured page count")

    all_rows = []
    previous_id = 0
    page_count = 0
    for index, payload in enumerate(pages):
        if index >= expected_pages:
            raise BeachHistoryError("unexpected extra page")
        result = validate_page(payload, limit=page_size)
        if result["total"] != total_before:
            raise BeachHistoryError("page total changed during pagination")
        start = index * page_size
        expected_size = min(page_size, total_before - start)
        rows = result["records"]
        if len(rows) != expected_size:
            raise BeachHistoryError("page is partial or truncated")
        for row in rows:
            if row["_id"] <= previous_id:
                raise BeachHistoryError("sample row IDs are duplicated or unordered")
            previous_id = row["_id"]
            all_rows.append(row)
        page_count += 1
    if page_count != expected_pages or len(all_rows) != total_before:
        raise BeachHistoryError("snapshot pagination is incomplete")

    retrieved = retrieved_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    canonical = ("\n".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for row in all_rows) + ("\n" if all_rows else "")).encode("utf-8")
    if len(canonical) > MAX_SNAPSHOT_BYTES:
        raise BeachHistoryError("snapshot exceeds configured byte limit")
    return {
        "schema_version": 1,
        "resource_id": RESOURCE_ID,
        "package_id": PACKAGE_ID,
        "beach_id": BEACH_ID,
        "row_count": len(all_rows),
        "generation": generation_before,
        "retrieved_at_utc": retrieved,
        "sha256": sha256(canonical).hexdigest(),
        "records": all_rows,
        "interpretation": "dated catalogue measurements only; not current swimming advice",
        "publication_status": "candidate_requires_application_integration_review",
    }


def collect_and_store_snapshot(
    *,
    metadata_before: tuple[int, str],
    fetch_page,
    metadata_after,
    destination: str | Path,
    page_size: int = 1000,
    retrieved_at: datetime,
) -> dict[str, Any]:
    """Fetch bounded pages and atomically advance a content-addressed snapshot pointer."""
    if not isinstance(metadata_before, tuple) or len(metadata_before) != 2:
        raise BeachHistoryError("initial metadata must be an exact count and generation")
    total_before, generation_before = metadata_before
    if type(total_before) is not int or not 0 <= total_before <= MAX_ROWS:
        raise BeachHistoryError("initial exact total exceeds snapshot bound")
    if total_before == 0:
        raise BeachHistoryError("empty historical source result is not accepted")
    if type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise BeachHistoryError("page size exceeds configured maximum")
    expected_pages = (total_before + page_size - 1) // page_size
    if expected_pages > MAX_PAGES:
        raise BeachHistoryError("snapshot exceeds configured page count")
    pages = []
    for page_index in range(expected_pages):
        offset = page_index * page_size
        limit = min(page_size, total_before - offset)
        payload = fetch_page(offset, limit)
        result = validate_page(payload, limit=limit)
        if result["total"] != total_before:
            raise BeachHistoryError("page total changed during pagination")
        pages.append(payload)
    if not isinstance(metadata_after, tuple) or len(metadata_after) != 2:
        raise BeachHistoryError("final metadata must be an exact count and generation")
    total_after, generation_after = metadata_after
    snapshot = build_complete_snapshot(
        pages,
        total_before=total_before,
        generation_before=generation_before,
        total_after=total_after,
        generation_after=generation_after,
        page_size=page_size,
        retrieved_at=retrieved_at,
    )
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "beach-10-history-manifest.json"
    if manifest_path.exists():
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous_name = previous["snapshot_file"]
            if not isinstance(previous_name, str) or Path(previous_name).name != previous_name:
                raise BeachHistoryError("existing snapshot manifest path is invalid")
            previous_file = root / previous_name
            if not previous_file.is_file() or _file_sha256(previous_file) != previous.get("sha256"):
                raise BeachHistoryError("existing last-good beach snapshot failed hash validation")
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise BeachHistoryError("existing last-good beach manifest is malformed") from exc

    rows_text = "\n".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for row in snapshot["records"]
    ) + "\n"
    rows_bytes = rows_text.encode("utf-8")
    digest = sha256(rows_bytes).hexdigest()
    if digest != snapshot["sha256"] or len(rows_bytes) > MAX_SNAPSHOT_BYTES:
        raise BeachHistoryError("candidate beach snapshot failed content verification")
    snapshot_name = f"beach-10-history-{digest}.jsonl"
    snapshot_path = root / snapshot_name
    if snapshot_path.exists():
        if not snapshot_path.is_file() or _file_sha256(snapshot_path) != digest:
            raise BeachHistoryError("existing content-addressed beach snapshot is corrupt")
    else:
        _atomic_write_bytes(snapshot_path, rows_bytes, root)
    manifest = {
        "schema_version": 1,
        "source": "Toronto Open Data beach water-quality history",
        "package_id": PACKAGE_ID,
        "resource_id": RESOURCE_ID,
        "beach_id": BEACH_ID,
        "generation": snapshot["generation"],
        "row_count": snapshot["row_count"],
        "sha256": digest,
        "snapshot_file": snapshot_name,
        "retrieved_at_utc": snapshot["retrieved_at_utc"],
        "interpretation": snapshot["interpretation"],
        "publication_status": snapshot["publication_status"],
    }
    _atomic_write_text(manifest_path, json.dumps(manifest, sort_keys=True, indent=2) + "\n", root)
    return manifest


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_bytes(path: Path, content: bytes, root: Path) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=".beach-candidate-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _atomic_write_text(path: Path, content: str, root: Path) -> None:
    _atomic_write_bytes(path, content.encode("utf-8"), root)
