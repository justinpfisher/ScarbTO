"""Bounded, allowlisted CKAN snapshot collector for the permits prototype.

The collector has no scheduler and does not publish data. Callers must choose a
fixed destination and reviewed source key. Tests use an injected fake transport.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


API_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/"
API_HOST = "ckan0.cf.opendata.inter.prod-toronto.ca"
DEFAULT_PAGE_SIZE = 1000
MAX_PAGE_SIZE = 2000
MAX_PAGE_BYTES = 16 * 1024 * 1024
MAX_PAGES = 1000
MAX_ROWS = 1_000_000
MAX_SNAPSHOT_BYTES = 512 * 1024 * 1024
RETRYABLE_HTTP = {502, 503, 504}

SOURCE_RESOURCES = {
    "active_permits": {
        "package_id": "building-permits-active-permits",
        "resource_id": "6d0229af-bc54-46de-9c2b-26759b01dd05",
        "fields": frozenset({
            "_id", "PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "GEO_ID",
            "APPLICATION_DATE", "ISSUED_DATE", "COMPLETED_DATE", "STATUS",
            "EST_CONST_COST", "DWELLING_UNITS_CREATED", "DWELLING_UNITS_LOST",
            "STREET_NUM", "STREET_NAME", "STREET_TYPE", "STREET_DIRECTION",
        }),
        "required_fields": frozenset({
            "_id", "PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "GEO_ID",
            "APPLICATION_DATE", "ISSUED_DATE", "COMPLETED_DATE", "STATUS",
            "EST_CONST_COST", "DWELLING_UNITS_CREATED", "DWELLING_UNITS_LOST",
            "STREET_NUM", "STREET_NAME", "STREET_TYPE", "STREET_DIRECTION",
        }),
        "minimum_row_retention": 0.5,
    },
    "cleared_permits_since_2017": {
        "package_id": "building-permits-cleared-permits",
        "resource_id": "a96c0ba4-3026-402b-b09d-5b1268b8f810",
        "fields": frozenset({
            "_id", "PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "GEO_ID",
            "APPLICATION_DATE", "ISSUED_DATE", "COMPLETED_DATE", "STATUS",
            "EST_CONST_COST", "DWELLING_UNITS_CREATED", "DWELLING_UNITS_LOST",
            "STREET_NUM", "STREET_NAME", "STREET_TYPE", "STREET_DIRECTION",
        }),
        "required_fields": frozenset({
            "_id", "PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "GEO_ID",
            "APPLICATION_DATE", "ISSUED_DATE", "COMPLETED_DATE", "STATUS",
            "EST_CONST_COST", "DWELLING_UNITS_CREATED", "DWELLING_UNITS_LOST",
            "STREET_NUM", "STREET_NAME", "STREET_TYPE", "STREET_DIRECTION",
        }),
        "minimum_row_retention": 0.5,
    },
    "development_applications": {
        "package_id": "development-applications",
        "resource_id": "8907d8ed-c515-4ce9-b674-9f8c6eefcf0d",
        "fields": frozenset({
            "_id", "APPLICATION_TYPE", "APPLICATION#", "FOLDERRSN",
            "DATE_SUBMITTED", "STATUS", "STREET_NUM", "STREET_NAME",
            "STREET_TYPE", "STREET_DIRECTION", "APPLICATION_URL", "WARD_NUMBER",
            "X", "Y",
        }),
        "required_fields": frozenset({
            "_id", "APPLICATION_TYPE", "APPLICATION#", "FOLDERRSN", "DATE_SUBMITTED",
            "STATUS", "STREET_NUM", "STREET_NAME", "STREET_TYPE",
            "STREET_DIRECTION", "WARD_NUMBER", "X", "Y",
        }),
        "minimum_row_retention": 0.5,
    },
    "oar_address_points": {
        "package_id": "address-points-municipal-toronto-one-address-repository",
        "resource_id": "0b3756af-9caf-4f0f-ac28-9c6617adede4",
        "fields": frozenset({
            "_id", "ADDRESS_POINT_ID", "ADDRESS_ID", "WARD", "ADDRESS_FULL", "geometry",
        }),
        "required_fields": frozenset({
            "_id", "ADDRESS_POINT_ID", "ADDRESS_ID", "WARD", "ADDRESS_FULL", "geometry",
        }),
        "minimum_row_retention": 0.5,
    },
}


class CollectionError(RuntimeError):
    """A source response or candidate snapshot did not qualify."""


class _RejectRedirects(HTTPRedirectHandler):
    """Never follow a redirect, even briefly to an unqualified host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "CKAN redirect rejected", headers, fp)


def _open_no_redirect(request: Request, *, timeout: float):
    return build_opener(_RejectRedirects()).open(request, timeout=timeout)


def _safe_source(source_key: str) -> dict[str, Any]:
    try:
        source = SOURCE_RESOURCES[source_key]
    except KeyError as exc:
        raise CollectionError("Unknown CKAN source key") from exc
    return source


def _validate_response(
    payload: Any, *, fields: frozenset[str], required_fields: frozenset[str], limit: int
) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise CollectionError("CKAN response is not a successful result")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise CollectionError("CKAN result object is missing")
    total = result.get("total")
    total_was_estimated = result.get("total_was_estimated")
    records = result.get("records")
    if total_was_estimated is not False:
        raise CollectionError("CKAN total is estimated or lacks an exactness flag")
    if type(total) is not int or total < 0 or not isinstance(records, list) or len(records) > limit:
        raise CollectionError("CKAN total or records are malformed")
    for row in records:
        if not isinstance(row, dict) or not set(row).issubset(fields):
            raise CollectionError("CKAN row contains unapproved fields or is not an object")
        if not required_fields.issubset(row):
            raise CollectionError("CKAN row is missing required source fields")
    return result


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TorontoCKAN:
    """Small GET-only CKAN client with capped responses and bounded retries."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15,
        max_page_bytes: int = MAX_PAGE_BYTES,
        retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        if timeout_seconds <= 0 or max_page_bytes < 1024 or retries < 0 or retries > 2:
            raise ValueError("Invalid CKAN client bounds")
        self.timeout_seconds = timeout_seconds
        self.max_page_bytes = max_page_bytes
        self.retries = retries
        self.sleep = sleep
        self.opener = opener or _open_no_redirect

    def _get_json(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        query = dict(params)
        if isinstance(query.get("fields"), (list, tuple)):
            # CKAN datastore_search expects this as a comma-separated list.
            # JSON-encoding the array is rejected by CKAN's validator.
            query["fields"] = ",".join(str(field) for field in query["fields"])
        url = API_BASE + action + "?" + urlencode(query)
        if urlparse(url).hostname != API_HOST or not url.startswith("https://"):
            raise CollectionError("CKAN request target is not the qualified HTTPS host")
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "ScarbTO-open-data-client/1.0"})
        for attempt in range(self.retries + 1):
            try:
                with self.opener(request, timeout=self.timeout_seconds) as response:
                    if urlparse(response.geturl()).hostname != API_HOST or urlparse(response.geturl()).scheme != "https":
                        raise CollectionError("CKAN redirected outside the qualified host")
                    length = response.headers.get("Content-Length")
                    if length:
                        try:
                            declared_length = int(length)
                        except ValueError as exc:
                            raise CollectionError("CKAN Content-Length is malformed") from exc
                        if declared_length < 0 or declared_length > self.max_page_bytes:
                            raise CollectionError("CKAN page exceeds the response byte limit")
                    body = response.read(self.max_page_bytes + 1)
                    if len(body) > self.max_page_bytes:
                        raise CollectionError("CKAN page exceeds the response byte limit")
                    try:
                        payload = json.loads(body)
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise CollectionError("CKAN response is not valid JSON") from exc
                    if not isinstance(payload, dict):
                        raise CollectionError("CKAN response root must be an object")
                    return payload
            except HTTPError as exc:
                if 300 <= exc.code < 400:
                    raise CollectionError(f"CKAN redirect rejected (HTTP {exc.code})") from exc
                if exc.code not in RETRYABLE_HTTP or attempt >= self.retries:
                    raise CollectionError(f"CKAN returned HTTP {exc.code}") from exc
                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = min(5.0, max(0.0, float(retry_after))) if retry_after else 0.5 * (2 ** attempt)
                except ValueError:
                    delay = 0.5 * (2 ** attempt)
                self.sleep(delay)
            except (TimeoutError, URLError) as exc:
                is_timeout = isinstance(exc, TimeoutError) or (
                    isinstance(exc, URLError)
                    and (isinstance(exc.reason, TimeoutError) or "timed out" in str(exc.reason).lower())
                )
                if not is_timeout:
                    raise CollectionError("CKAN transport failed outside the retryable timeout scope") from exc
                if attempt >= self.retries:
                    raise CollectionError("CKAN request timed out after bounded retries") from exc
                self.sleep(0.5 * (2 ** attempt))
        raise CollectionError("CKAN retry bound exhausted")

    def metadata(self, source_key: str) -> tuple[int, str]:
        source = _safe_source(source_key)
        package_payload = self._get_json("package_show", {"id": source["package_id"]})
        package = package_payload.get("result") if package_payload.get("success") is True else None
        if not isinstance(package, dict) or not isinstance(package.get("resources"), list):
            raise CollectionError("CKAN package metadata is malformed")
        resource = next((item for item in package["resources"] if item.get("id") == source["resource_id"]), None)
        if not isinstance(resource, dict):
            raise CollectionError("Expected CKAN resource is missing from its package")
        metadata_modified = package.get("metadata_modified")
        resource_modified = resource.get("last_modified") or resource.get("metadata_modified")
        generation_parts = [str(value) for value in (metadata_modified, resource_modified) if isinstance(value, str) and value]
        if not isinstance(resource_modified, str) or not resource_modified:
            raise CollectionError("CKAN resource metadata has no usable generation marker")
        generation = "|".join(generation_parts)
        payload = self._get_json("datastore_search", {
            "resource_id": source["resource_id"],
            "limit": 0,
            "fields": sorted(source["fields"]),
        })
        result = _validate_response(
            payload, fields=source["fields"],
            required_fields=source["required_fields"], limit=0,
        )
        if not generation.strip():
            raise CollectionError("CKAN resource generation marker is empty")
        return result["total"], generation

    def page(self, source_key: str, *, offset: int, limit: int) -> dict[str, Any]:
        source = _safe_source(source_key)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
            raise CollectionError("Invalid CKAN page bounds")
        payload = self._get_json("datastore_search", {
            "resource_id": source["resource_id"],
            "limit": limit,
            "offset": offset,
            "sort": "_id asc",
            "fields": sorted(source["fields"]),
        })
        _validate_response(
            payload, fields=source["fields"],
            required_fields=source["required_fields"], limit=limit,
        )
        return payload


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".staged-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def collect_snapshot(
    source_key: str,
    destination: str | Path,
    *,
    metadata: Callable[[], tuple[int, str]],
    fetch_page: Callable[[int, int], dict[str, Any]],
    page_size: int = DEFAULT_PAGE_SIZE,
    max_rows: int = MAX_ROWS,
    max_pages: int = MAX_PAGES,
    max_snapshot_bytes: int = MAX_SNAPSHOT_BYTES,
) -> dict[str, Any]:
    """Stream one complete allowlisted snapshot; atomically advance its manifest pointer."""
    source = _safe_source(source_key)
    if type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise CollectionError("Page size exceeds the qualified maximum")
    if (
        type(max_rows) is not int or max_rows < 0
        or type(max_pages) is not int or max_pages < 1
        or type(max_snapshot_bytes) is not int or max_snapshot_bytes < 1
    ):
        raise CollectionError("Invalid snapshot limits")
    total_before, generation_before = metadata()
    if type(total_before) is not int or total_before < 0 or total_before > max_rows:
        raise CollectionError("Source count exceeds the configured snapshot limit")
    if not isinstance(generation_before, str) or not generation_before.strip():
        raise CollectionError("Source generation marker is empty")
    expected_pages = (total_before + page_size - 1) // page_size
    if expected_pages > max_pages:
        raise CollectionError("Source count exceeds the configured page limit")

    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / f"{source_key}-manifest.json"
    previous_count = None
    if manifest_path.exists():
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            previous_count = previous.get("row_count")
        except (OSError, json.JSONDecodeError) as exc:
            raise CollectionError("Existing last-good manifest is unreadable") from exc
        if (
            not isinstance(previous, dict) or previous.get("source_key") != source_key
            or type(previous_count) is not int or previous_count < 0
        ):
            raise CollectionError("Existing last-good manifest is malformed")
        snapshot_name = previous.get("snapshot_file")
        if not isinstance(snapshot_name, str) or Path(snapshot_name).name != snapshot_name:
            raise CollectionError("Existing last-good snapshot path is invalid")
        previous_snapshot = root / snapshot_name
        if not previous_snapshot.is_file():
            raise CollectionError("Existing last-good snapshot is missing")
        if _file_sha256(previous_snapshot) != previous.get("sha256"):
            raise CollectionError("Existing last-good snapshot hash does not match")
    if total_before == 0 and (previous_count is None or previous_count > 0):
        raise CollectionError("Empty source result is not accepted without a qualified empty-source policy")
    if previous_count and total_before < previous_count * source["minimum_row_retention"]:
        raise CollectionError("Source row count fell below its source-specific retention floor")
    fd, staged_name = tempfile.mkstemp(prefix=".candidate-", suffix=".jsonl.tmp", dir=root)
    digest = sha256()
    rows_written = 0
    last_id = 0
    first_id: int | None = None
    try:
        with os.fdopen(fd, "wb") as staged:
            offset = 0
            while offset < total_before:
                response = fetch_page(offset, min(page_size, total_before - offset))
                result = _validate_response(
                    response, fields=source["fields"],
                    required_fields=source["required_fields"], limit=page_size,
                )
                if result["total"] != total_before:
                    raise CollectionError("Source total changed during pagination")
                records = result["records"]
                requested = min(page_size, total_before - offset)
                if len(records) != requested:
                    raise CollectionError("Unexpected empty, partial, or truncated page")
                for row in records:
                    row_id = row.get("_id")
                    if type(row_id) is not int or row_id <= last_id:
                        raise CollectionError("Source row IDs are missing, duplicated, or unordered")
                    if first_id is None:
                        first_id = row_id
                    last_id = row_id
                    encoded = (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                    if staged.tell() + len(encoded) > max_snapshot_bytes:
                        raise CollectionError("Snapshot exceeds the configured byte limit")
                    staged.write(encoded)
                    digest.update(encoded)
                    rows_written += 1
                offset += len(records)
            staged.flush()
            os.fsync(staged.fileno())
        total_after, generation_after = metadata()
        if total_after != total_before or generation_after != generation_before:
            raise CollectionError("Source generation or count changed during snapshot")
        if rows_written != total_before:
            raise CollectionError("Snapshot row count does not match source count")

        content_hash = digest.hexdigest()
        snapshot_name = f"{source_key}-{content_hash}.jsonl"
        snapshot_path = root / snapshot_name
        if snapshot_path.exists():
            if not snapshot_path.is_file() or _file_sha256(snapshot_path) != content_hash:
                raise CollectionError("Existing content-addressed snapshot is corrupt")
            os.unlink(staged_name)
        else:
            os.replace(staged_name, snapshot_path)
        manifest = {
            "schema_version": 1,
            "source_key": source_key,
            "resource_id": source["resource_id"],
            "generation": generation_before,
            "row_count": rows_written,
            "first_id": first_id,
            "last_id": last_id or None,
            "sha256": content_hash,
            "snapshot_file": snapshot_name,
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "publication_status": "disabled_pending_source_geography_and_privacy_review",
        }
        # The manifest is the only mutable pointer. Until its replacement,
        # readers continue to resolve the previous complete snapshot.
        _atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        return manifest
    except Exception:
        try:
            os.unlink(staged_name)
        except OSError:
            pass
        raise


