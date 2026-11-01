"""Source-free checks for the existing public snapshot and its exports."""
from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

DATASET_URL = "https://open.toronto.ca/dataset/dinesafe/"
LICENCE_URL = "https://open.toronto.ca/open-data-licence/"
SNAPSHOT_KEYS = {"schema_version", "ready", "published_at", "source", "quality", "establishments", "activity"}
SOURCE_KEYS = {"name", "dataset_url", "licence_url", "resource_url", "last_refreshed"}
QUALITY_KEYS = {"source_rows", "geocoded_rows", "scarborough_rows", "scarborough_establishments", "unassigned_neighbourhoods"}
ENTRY_KEYS = {"id", "name", "address", "type", "inspection_detail", "status", "inspection_date", "latitude", "longitude", "ward", "neighbourhood"}
ACTIVITY_KEYS = {"id", "feed", "kind", "establishment_id", "name", "address", "neighbourhood", "inspection_date", "detected_at", "status", "previous_status", "latitude", "longitude", "source_url"}
CSV_FIELDS = ["id", "name", "address", "type", "inspection_detail", "status", "inspection_date", "latitude", "longitude", "ward", "neighbourhood", "source_url", "licence_url", "collected_at"]
STATUSES = {"Pass", "Conditional Pass", "Closed"}
ACTIVITY_KINDS = {"first_seen", "new_inspection", "status_changed"}


class SnapshotIntegrityError(ValueError):
    pass


def is_snapshot_fresh(published_at: datetime, now: datetime, max_age: timedelta = timedelta(hours=3)) -> bool:
    """Keep the ordinary release gate: aware timestamps no more than three hours old."""
    if published_at.tzinfo is None or now.tzinfo is None:
        return False
    age = now.astimezone(timezone.utc) - published_at.astimezone(timezone.utc)
    # Preserve verify_snapshot.py's existing behavior, including its treatment of
    # a slightly future timestamp (the code-only path separately caps clock skew).
    return age <= max_age


def _aware_date(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise SnapshotIntegrityError(f"{label} must be a timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotIntegrityError(f"{label} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise SnapshotIntegrityError(f"{label} must retain its timezone")
    return parsed


def _is_resource_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "ckan0.cf.opendata.inter.prod-toronto.ca"
        and parsed.username is None
        and parsed.password is None
        and parsed.path.endswith("/download/dinesafe.csv")
    )


def _csv_bytes(snapshot: dict[str, Any]) -> bytes:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for entry in snapshot["establishments"]:
        row = {
            **entry,
            "source_url": DATASET_URL,
            "licence_url": LICENCE_URL,
            "collected_at": snapshot["published_at"],
        }
        for field in ("id", "name", "address", "type", "inspection_detail", "ward", "neighbourhood"):
            value = row.get(field)
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                row[field] = "'" + value
        writer.writerow(row)
    return stream.getvalue().encode("utf-8-sig")


def validate_snapshot_integrity(data_dir: str | Path, *, now: datetime | None = None) -> dict[str, Any]:
    """Validate unchanged last-good artifacts without advancing any source or build time."""
    root = Path(data_dir)
    try:
        snapshot = json.loads((root / "snapshot.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotIntegrityError("Last-good snapshot is missing or invalid JSON") from exc
    if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_KEYS:
        raise SnapshotIntegrityError("Snapshot root schema differs from the qualified DineSafe schema")
    if snapshot.get("schema_version") != 1 or snapshot.get("ready") is not True:
        raise SnapshotIntegrityError("Snapshot is not a ready schema-version-1 DineSafe release")

    published_at = _aware_date(snapshot.get("published_at"), "published_at")
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None or published_at > clock.astimezone(timezone.utc) + timedelta(minutes=5):
        raise SnapshotIntegrityError("Snapshot timestamp is in the future or validation clock is naive")

    source = snapshot.get("source")
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise SnapshotIntegrityError("Snapshot source provenance schema is incomplete or unexpected")
    if (
        not isinstance(source.get("name"), str)
        or not source["name"].startswith("City of Toronto Open Data ")
        or not source["name"].endswith(" DineSafe")
        or source.get("dataset_url") != DATASET_URL
        or source.get("licence_url") != LICENCE_URL
        or not _is_resource_url(source.get("resource_url"))
    ):
        raise SnapshotIntegrityError("Snapshot source identity or licence is not the qualified City DineSafe source")
    last_refreshed = source.get("last_refreshed")
    if last_refreshed is not None:
        if not isinstance(last_refreshed, str) or not last_refreshed.strip():
            raise SnapshotIntegrityError("City source refresh metadata is malformed")
        try:
            datetime.fromisoformat(last_refreshed.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SnapshotIntegrityError("City source refresh metadata is not an ISO timestamp") from exc

    quality = snapshot.get("quality")
    if not isinstance(quality, dict) or set(quality) != QUALITY_KEYS:
        raise SnapshotIntegrityError("Snapshot quality schema differs from the qualified DineSafe schema")
    if any(type(value) is not int or value < 0 for value in quality.values()):
        raise SnapshotIntegrityError("Snapshot quality counts must be nonnegative integers")
    if quality["geocoded_rows"] > quality["source_rows"] or quality["scarborough_rows"] > quality["geocoded_rows"]:
        raise SnapshotIntegrityError("Snapshot quality counts are internally inconsistent")

    entries = snapshot.get("establishments")
    if not isinstance(entries, list) or len(entries) < 300 or len(entries) != quality["scarborough_establishments"]:
        raise SnapshotIntegrityError("Snapshot establishment count is below threshold or disagrees with quality metadata")
    seen_ids: set[str] = set()
    for row in entries:
        if not isinstance(row, dict) or set(row) != ENTRY_KEYS:
            raise SnapshotIntegrityError("Establishment row schema is unexpected")
        ident = row.get("id")
        if not isinstance(ident, str) or not ident or ident in seen_ids:
            raise SnapshotIntegrityError("Establishment identifiers are missing or duplicated")
        seen_ids.add(ident)
        for field in ("name", "address", "type", "inspection_detail", "ward", "neighbourhood"):
            if not isinstance(row.get(field), str):
                raise SnapshotIntegrityError(f"Establishment {field} must be a string")
        if row.get("status") not in STATUSES:
            raise SnapshotIntegrityError("Establishment status is outside the validated DineSafe values")
        date = row.get("inspection_date")
        if date is not None:
            if not isinstance(date, str):
                raise SnapshotIntegrityError("Inspection date must be an ISO calendar date or null")
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError as exc:
                raise SnapshotIntegrityError("Inspection date is malformed") from exc
        lat, lon = row.get("latitude"), row.get("longitude")
        if type(lat) not in (int, float) or type(lon) not in (int, float) or not math.isfinite(lat) or not math.isfinite(lon):
            raise SnapshotIntegrityError("Establishment coordinates must be finite numbers")
        if not (-80 < lon < -78 and 43 < lat < 45):
            raise SnapshotIntegrityError("Establishment coordinate falls outside the qualified Toronto area")

    activity = snapshot.get("activity")
    if not isinstance(activity, list):
        raise SnapshotIntegrityError("Activity history must be an array")
    event_ids: set[str] = set()
    for event in activity:
        if not isinstance(event, dict) or set(event) != ACTIVITY_KEYS:
            raise SnapshotIntegrityError("Activity row schema is unexpected")
        if event.get("feed") != "dinesafe" or event.get("kind") not in ACTIVITY_KINDS:
            raise SnapshotIntegrityError("Activity row is outside the validated DineSafe history")
        if not isinstance(event.get("id"), str) or not event["id"] or event["id"] in event_ids:
            raise SnapshotIntegrityError("Activity identifiers are missing or duplicated")
        event_ids.add(event["id"])
        if event.get("source_url") != DATASET_URL:
            raise SnapshotIntegrityError("Activity source attribution is not the official DineSafe catalogue")
        _aware_date(event.get("detected_at"), "activity detected_at")

    try:
        csv_data = (root / "establishments.csv").read_bytes()
    except OSError as exc:
        raise SnapshotIntegrityError("Matching public establishments CSV is missing") from exc
    if csv_data != _csv_bytes(snapshot):
        raise SnapshotIntegrityError("Public establishments CSV does not exactly match the last-good snapshot")
    return {
        "published_at": snapshot["published_at"],
        "source_last_refreshed": source["last_refreshed"],
        "establishments": len(entries),
        "activity_records": len(activity),
    }
