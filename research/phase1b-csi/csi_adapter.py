"""Offline-first, aggregate-only CSI source-contract prototype.

This module deliberately has no network client and no public exporter. It is
exercised only with fabricated rows until source and privacy review authorize
activation.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable
from zoneinfo import ZoneInfo


SOURCE_NAME = "CSI_OPEN_DATA"
LAYER_ID = 0
SERVICE_ITEM_ID = "0a239a5563a344a3bbf8452504ed8d68"
ORDER_BY_FIELDS = "OBJECTID ASC"
SOURCE_URL = (
    "https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services/"
    "Major_Crime_Indicators_Open_Data/FeatureServer/0"
)
TPS_TERMS_URL = (
    "https://torontops.maps.arcgis.com/sharing/rest/content/items/"
    "0a239a5563a344a3bbf8452504ed8d68?f=pjson"
)
TORONTO = ZoneInfo("America/Toronto")
UNASSIGNED_NEIGHBOURHOOD = "NSA"
KNOWN_CSI_CATEGORIES = frozenset({
    "Assault", "Auto Theft", "Break and Enter", "Robbery", "Theft Over",
})
REQUIRED_FIELDS = {
    "OBJECTID",
    "EVENT_UNIQUE_ID",
    "REPORT_DATE",
    "OCC_DATE",
    "CSI_CATEGORY",
    "OFFENCE",
    "NEIGHBOURHOOD_158",
}
EXPECTED_FIELD_TYPES = {
    "OBJECTID": "esriFieldTypeOID",
    "EVENT_UNIQUE_ID": "esriFieldTypeString",
    "REPORT_DATE": "esriFieldTypeDate",
    "OCC_DATE": "esriFieldTypeDate",
    "REPORT_YEAR": "esriFieldTypeString",
    "REPORT_MONTH": "esriFieldTypeString",
    "CSI_CATEGORY": "esriFieldTypeString",
    "OFFENCE": "esriFieldTypeString",
    "NEIGHBOURHOOD_158": "esriFieldTypeString",
    "LONG_WGS84": "esriFieldTypeDouble",
    "LAT_WGS84": "esriFieldTypeDouble",
}
FORBIDDEN_PUBLIC_FIELDS = {
    "OBJECTID", "EVENT_UNIQUE_ID", "OFFENCE", "LONG_WGS84", "LAT_WGS84"
}


class ContractError(ValueError):
    """Input does not satisfy the currently reviewed source contract."""


class PublicExportDisabled(RuntimeError):
    """Public CSI output is blocked pending a reviewed privacy policy."""


@dataclass(frozen=True)
class SourceVersion:
    service_item_id: str
    layer_id: int
    layer_name: str
    edit_date_utc: str
    schema_sha256: str
    field_types: dict[str, str]
    max_record_count: int
    supports_pagination: bool
    supports_order_by: bool
    date_fields_time_zone_iana: str
    coverage_start_date: str
    coverage_end_date: str
    coverage_basis: str
    queried_at_utc: str
    expected_total: int

    def validate(self) -> None:
        if self.service_item_id != SERVICE_ITEM_ID:
            raise ContractError("Unexpected ArcGIS service item identity")
        if self.layer_id != LAYER_ID or self.layer_name != SOURCE_NAME:
            raise ContractError("Unexpected CSI service layer identity")
        if self.max_record_count <= 0 or self.expected_total <= 0:
            raise ContractError("Invalid source pagination metadata")
        if self.supports_pagination is not True or self.supports_order_by is not True:
            raise ContractError("Source does not support required stable pagination")
        if self.date_fields_time_zone_iana != "Etc/UTC":
            raise ContractError("CSI date field metadata is not Etc/UTC")
        normalized_types = {
            str(name).strip().upper(): str(field_type).strip()
            for name, field_type in self.field_types.items()
        }
        if len(normalized_types) != len(self.field_types):
            raise ContractError("Duplicate CSI field names in metadata")
        field_names = set(normalized_types)
        # Require every selected query field so metadata and rows cannot omit
        # the same field and validate together.
        missing_types = set(EXPECTED_FIELD_TYPES) - field_names
        if missing_types:
            raise ContractError(f"CSI metadata missing required field types: {sorted(missing_types)}")
        if schema_signature(field_names) != self.schema_sha256.lower():
            raise ContractError("CSI metadata field types do not match schema signature")
        mismatched = {
            name: (expected, normalized_types.get(name))
            for name, expected in EXPECTED_FIELD_TYPES.items()
            if name in normalized_types and normalized_types[name] != expected
        }
        if mismatched:
            raise ContractError(f"CSI field type mismatch: {mismatched}")
        for label, value in (("edit date", self.edit_date_utc), ("query time", self.queried_at_utc)):
            parse_utc(value, label)
        coverage_start = parse_source_coverage_date(self.coverage_start_date, "coverage start")
        coverage_end = parse_source_coverage_date(self.coverage_end_date, "coverage end")
        if self.coverage_basis != "published_extract_metadata":
            raise ContractError("Report-quarter coverage must come from published extract metadata")
        if coverage_start > coverage_end:
            raise ContractError("Source coverage starts after it ends")
        if len(self.schema_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.schema_sha256.lower()
        ):
            raise ContractError("Invalid source schema signature")

    def stable_key(self) -> tuple[Any, ...]:
        """Fields that must not change while a paged snapshot is collected."""
        return (
            self.service_item_id,
            self.layer_id,
            self.layer_name,
            self.edit_date_utc,
            self.schema_sha256.lower(),
            tuple(sorted((name.upper(), value) for name, value in self.field_types.items())),
            self.max_record_count,
            self.supports_pagination,
            self.supports_order_by,
            self.date_fields_time_zone_iana,
            self.coverage_start_date,
            self.coverage_end_date,
            self.coverage_basis,
            self.expected_total,
        )


class ValidatedSnapshot(list[dict[str, Any]]):
    """Rows accepted by complete pagination validation for one source version."""

    def __init__(self, rows: list[dict[str, Any]], source_version_key: tuple[Any, ...]):
        super().__init__(rows)
        self.source_version_key = source_version_key


def parse_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"Missing UTC {label}")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ContractError(f"Invalid UTC {label}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractError(f"{label} must carry an explicit UTC offset")
    if parsed.utcoffset().total_seconds() != 0:
        raise ContractError(f"{label} must be UTC")
    return parsed.astimezone(timezone.utc)


def parse_source_coverage_date(value: str, label: str) -> date:
    """Parse an inclusive Toronto calendar date from published extract metadata."""
    if not isinstance(value, str):
        raise ContractError(f"{label} must be an inclusive ISO calendar date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"{label} must be an inclusive ISO calendar date") from exc
    if parsed.isoformat() != value:
        raise ContractError(f"{label} must be an inclusive ISO calendar date")
    return parsed


def schema_signature(field_names: Iterable[str]) -> str:
    canonical = "\n".join(sorted(str(name).strip().upper() for name in field_names))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _attrs(feature: dict[str, Any]) -> dict[str, Any]:
    attrs = feature.get("attributes", feature)
    if not isinstance(attrs, dict):
        raise ContractError("Feature attributes must be an object")
    return attrs


def validate_schema(field_names: Iterable[str]) -> None:
    names = {str(name).strip().upper() for name in field_names}
    missing = REQUIRED_FIELDS - names
    if missing:
        raise ContractError(f"CSI schema missing fields: {sorted(missing)}")


def validate_pages(
    pages: list[dict[str, Any]],
    version_before: SourceVersion,
    version_after: SourceVersion,
) -> ValidatedSnapshot:
    """Require contiguous, complete, duplicate-safe pages from one source version."""
    version_before.validate()
    version_after.validate()
    if version_before.stable_key() != version_after.stable_key():
        raise ContractError("CSI source version changed during pagination")
    if not pages:
        raise ContractError("CSI query returned no pages for a non-empty source")

    collected: list[dict[str, Any]] = []
    seen_object_ids: set[int] = set()
    expected_offset = 0
    previous_object_id: int | None = None
    for index, page in enumerate(pages):
        offset = page.get("offset")
        if type(offset) is not int or offset != expected_offset:
            raise ContractError("CSI pages are not contiguous from offset zero")
        requested = page.get("requested_count")
        features = page.get("features")
        if type(requested) is not int or requested < 1:
            raise ContractError("Invalid requested page size")
        order_by = " ".join(str(page.get("order_by_fields", "")).upper().split())
        if order_by != ORDER_BY_FIELDS:
            raise ContractError("CSI pagination must use stable OBJECTID ASC ordering")
        if requested > version_before.max_record_count:
            raise ContractError("Requested page exceeds current source maxRecordCount")
        if not isinstance(features, list) or not features:
            raise ContractError("Unexpected empty CSI page")
        if len(features) > requested:
            raise ContractError("CSI page exceeded its requested record count")
        more = bool(page.get("exceeded_transfer_limit", False))
        if more and len(features) < requested:
            raise ContractError("Transfer-limited page is short; pagination is ambiguous")
        for feature in features:
            attrs = _attrs(feature)
            _validate_row_types(attrs)
            object_id = attrs.get("OBJECTID")
            if type(object_id) is not int:
                raise ContractError("Missing or invalid integer snapshot OBJECTID")
            if object_id in seen_object_ids:
                raise ContractError("Duplicate OBJECTID across pages")
            if previous_object_id is not None and object_id <= previous_object_id:
                raise ContractError("CSI OBJECTID order is not strictly ascending")
            seen_object_ids.add(object_id)
            previous_object_id = object_id
            collected.append(attrs)
        expected_offset += len(features)
        if index < len(pages) - 1 and not more:
            raise ContractError("Pagination continued after source said it was complete")
        if index == len(pages) - 1 and more:
            raise ContractError("Final CSI page reports more records")

    if expected_offset != version_before.expected_total:
        raise ContractError(
            f"Incomplete CSI pagination: got {expected_offset}, expected {version_before.expected_total}"
        )
    validate_schema(collected[0].keys())
    first_schema = {str(name).strip().upper() for name in collected[0].keys()}
    actual_schema = schema_signature(first_schema)
    if actual_schema != version_before.schema_sha256.lower():
        raise ContractError("CSI row schema does not match source metadata signature")
    if any({str(name).strip().upper() for name in row.keys()} != first_schema for row in collected[1:]):
        raise ContractError("CSI row schema changed within the paged response")
    return ValidatedSnapshot(collected, version_before.stable_key())


def _date_utc(value: Any, field: str) -> datetime:
    """ArcGIS date fields may be ISO strings or milliseconds since epoch."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise ContractError(f"Invalid UTC {field}") from exc
    if isinstance(value, str):
        return parse_utc(value, field)
    raise ContractError(f"Missing or invalid UTC {field}")


def _validate_row_types(row: dict[str, Any]) -> None:
    for name, expected in EXPECTED_FIELD_TYPES.items():
        if name not in row:
            continue
        value = row[name]
        if value is None:
            continue
        if expected == "esriFieldTypeOID":
            valid = type(value) is int
        elif expected == "esriFieldTypeString":
            valid = isinstance(value, str)
        elif expected == "esriFieldTypeDouble":
            valid = type(value) in (int, float)
        elif expected == "esriFieldTypeDate":
            _optional_date_utc(value, name)
            valid = True
        else:
            valid = False
        if not valid:
            if name == "OBJECTID":
                raise ContractError("Missing or invalid integer snapshot OBJECTID")
            raise ContractError(f"CSI {name} value does not match {expected}")


def _optional_date_utc(value: Any, field: str) -> datetime | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return _date_utc(value, field)


def build_aggregate_candidate(rows: list[dict[str, Any]], version: SourceVersion) -> dict[str, Any]:
    """Return only coarse internal aggregates; never expose row IDs or coordinates."""
    version.validate()
    if len(rows) != version.expected_total:
        raise ContractError("Validated rows no longer match source count")

    # Keep row counts separate from distinct occurrence counts. Repeated IDs
    # remain legitimate rows, including when one occurrence spans categories.
    groups: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"source_row_count": 0, "occurrence_ids": set()}
    )
    occurred_days: list[date] = []
    report_days: list[date] = []
    unaggregated_rows = 0
    # These bounds come from the published extract's declared coverage
    # metadata. Observed row min/max dates are reported for QA only and never
    # establish that a quarter is complete.
    coverage_start = parse_source_coverage_date(version.coverage_start_date, "coverage start")
    coverage_end = parse_source_coverage_date(version.coverage_end_date, "coverage end")
    for row in rows:
        occurred = _optional_date_utc(row.get("OCC_DATE"), "OCC_DATE")
        reported = _optional_date_utc(row.get("REPORT_DATE"), "REPORT_DATE")
        reported_local_date = reported.astimezone(TORONTO).date() if reported is not None else None
        if reported_local_date is not None and not coverage_start <= reported_local_date <= coverage_end:
            raise ContractError("REPORT_DATE falls outside the reported source coverage")
        if occurred is not None:
            occurred_days.append(occurred.date())
        if reported is not None:
            report_days.append(reported.date())
        neighbourhood = str(row.get("NEIGHBOURHOOD_158") or "").strip()
        category = str(row.get("CSI_CATEGORY") or "").strip()
        occurrence_id = str(row.get("EVENT_UNIQUE_ID") or "").strip()
        if category and category not in KNOWN_CSI_CATEGORIES:
            raise ContractError("Unknown CSI category value")
        if (
            not neighbourhood or neighbourhood.upper() == UNASSIGNED_NEIGHBOURHOOD
            or not category or not occurrence_id or occurred is None or reported is None
        ):
            # Preserve source totals in pagination metadata, but do not create
            # a misleadingly located/category-labelled aggregate cell.
            unaggregated_rows += 1
            continue
        local_month = occurred.astimezone(TORONTO).strftime("%Y-%m")
        group = groups[(neighbourhood, category, local_month)]
        group["source_row_count"] += 1
        group["occurrence_ids"].add(occurrence_id)

    cells = []
    for (neighbourhood, category, month), counts in sorted(groups.items()):
        cells.append({
            "neighbourhood": neighbourhood,
            "category": category,
            "occurrence_month_toronto": month,
            "source_row_count": counts["source_row_count"],
            "distinct_occurrence_ids": len(counts["occurrence_ids"]),
        })

    if not cells:
        raise ContractError("No aggregateable CSI rows; refuse an empty candidate")

    return {
        "publication_status": "disabled_pending_privacy_review",
        "source": {
            "name": version.layer_name,
            "service_item_id": version.service_item_id,
            "layer_id": version.layer_id,
            "url": SOURCE_URL,
            "terms_review_url": TPS_TERMS_URL,
            "edit_date_utc": version.edit_date_utc,
            "coverage_start_date": version.coverage_start_date,
            "coverage_end_date": version.coverage_end_date,
            "coverage_basis": version.coverage_basis,
            "queried_at_utc": version.queried_at_utc,
            "schema_sha256": version.schema_sha256,
            "max_record_count": version.max_record_count,
        },
        "source_rows": version.expected_total,
        "unaggregated_rows": unaggregated_rows,
        "aggregate_cell_count": len(cells),
        "occurrence_date_min_utc": min(occurred_days).isoformat() if occurred_days else None,
        "occurrence_date_max_utc": max(occurred_days).isoformat() if occurred_days else None,
        "report_date_min_utc": min(report_days).isoformat() if report_days else None,
        "report_date_max_utc": max(report_days).isoformat() if report_days else None,
        "cells": cells,
        "limitations": [
            "Historical/preliminary offence-level source; not live dispatch.",
            "One occurrence may have multiple rows and may appear in multiple categories.",
            "Locations are deliberately offset; this candidate contains no coordinates or row identifiers.",
            "Aggregate cells are internal candidates only; no sparse-cell threshold or public release is approved.",
        ],
    }


def _quarter_for_toronto(value: datetime) -> tuple[int, int]:
    local = value.astimezone(TORONTO)
    return local.year, ((local.month - 1) // 3) + 1


def _quarter_interval_toronto(year: int, quarter: int) -> tuple[date, date]:
    """Return inclusive Toronto-local calendar dates for a report quarter."""
    if quarter not in (1, 2, 3, 4):
        raise ContractError("Invalid report quarter")
    first_month = (quarter - 1) * 3 + 1
    start_local = date(year, first_month, 1)
    if quarter == 4:
        next_local = date(year + 1, 1, 1)
    else:
        next_local = date(year, first_month + 3, 1)
    return start_local, next_local - timedelta(days=1)


def build_report_quarter_candidate(
    rows: list[dict[str, Any]], version: SourceVersion
) -> dict[str, Any]:
    """Build internal neighborhood/category counts by completed report quarter.

    This is the qualified historical presentation grain. It counts source rows,
    not unique events, and excludes incomplete coverage quarters. Output remains
    private until the separately proposed suppression/coarsening policy is
    approved; no exact row dates or event identifiers are emitted.
    """
    version.validate()
    if not isinstance(rows, ValidatedSnapshot):
        raise ContractError("Report-quarter aggregation requires a paged validated snapshot")
    if rows.source_version_key != version.stable_key():
        raise ContractError("Validated report snapshot belongs to a different source version")
    if len(rows) != version.expected_total:
        raise ContractError("Validated rows no longer match source count")

    # The wrapper is a runtime guard, not a cryptographic capability: callers
    # can still mutate its list or row dictionaries after pagination. Recheck
    # the invariants that make it unsafe to count duplicate snapshot rows.
    expected_schema = {str(name).strip().upper() for name in version.field_types}
    seen_object_ids: set[int] = set()
    previous_object_id: int | None = None
    for row in rows:
        normalized_schema = {str(name).strip().upper() for name in row} if isinstance(row, dict) else set()
        if not isinstance(row, dict) or normalized_schema != expected_schema:
            raise ContractError("Validated report snapshot row schema changed")
        _validate_row_types(row)
        object_id = row.get("OBJECTID")
        if type(object_id) is not int or object_id in seen_object_ids:
            raise ContractError("Validated report snapshot has duplicate or invalid OBJECTID")
        if previous_object_id is not None and object_id <= previous_object_id:
            raise ContractError("Validated report snapshot OBJECTID order changed")
        seen_object_ids.add(object_id)
        previous_object_id = object_id

    coverage_start = parse_source_coverage_date(version.coverage_start_date, "coverage start")
    coverage_end = parse_source_coverage_date(version.coverage_end_date, "coverage end")
    groups: dict[tuple[str, str, int, int], dict[str, Any]] = defaultdict(
        lambda: {"source_record_count": 0, "report_dates": []}
    )
    unaggregated_rows = 0
    incomplete_quarter_rows = 0
    report_dates: list[datetime] = []

    for row in rows:
        reported = _optional_date_utc(row.get("REPORT_DATE"), "REPORT_DATE")
        neighbourhood = str(row.get("NEIGHBOURHOOD_158") or "").strip()
        category = str(row.get("CSI_CATEGORY") or "").strip()
        if category and category not in KNOWN_CSI_CATEGORIES:
            raise ContractError("Unknown CSI category value")
        reported_local_date = reported.astimezone(TORONTO).date() if reported is not None else None
        if reported_local_date is not None and not coverage_start <= reported_local_date <= coverage_end:
            raise ContractError("REPORT_DATE falls outside the reported source coverage")
        if (
            reported is None or not neighbourhood or not category
            or neighbourhood.upper() == UNASSIGNED_NEIGHBOURHOOD
        ):
            unaggregated_rows += 1
            continue
        report_dates.append(reported)
        year, quarter = _quarter_for_toronto(reported)
        quarter_start_date, quarter_end_date = _quarter_interval_toronto(year, quarter)
        # Coverage fields are inclusive Toronto calendar dates copied from
        # published extract metadata. Observed row dates cannot prove coverage.
        if coverage_start > quarter_start_date or coverage_end < quarter_end_date:
            incomplete_quarter_rows += 1
            continue
        group = groups[(neighbourhood, category, year, quarter)]
        group["source_record_count"] += 1
        group["report_dates"].append(reported)

    cells = []
    for (neighbourhood, category, year, quarter), counts in sorted(groups.items()):
        cells.append({
            "neighbourhood": neighbourhood,
            "category": category,
            "report_quarter": f"{year}-Q{quarter}",
            "source_record_count": counts["source_record_count"],
        })
    if not cells:
        raise ContractError("No completed-quarter CSI rows; refuse an empty candidate")

    return {
        "publication_status": "disabled_pending_privacy_review",
        "source": {
            "name": version.layer_name,
            "service_item_id": version.service_item_id,
            "layer_id": version.layer_id,
            "url": SOURCE_URL,
            "terms_review_url": TPS_TERMS_URL,
            "edit_date_utc": version.edit_date_utc,
            "coverage_start_date": version.coverage_start_date,
            "coverage_end_date": version.coverage_end_date,
            "coverage_basis": version.coverage_basis,
            "queried_at_utc": version.queried_at_utc,
            "schema_sha256": version.schema_sha256,
            "max_record_count": version.max_record_count,
        },
        "source_record_total": version.expected_total,
        "aggregated_source_record_total": sum(c["source_record_count"] for c in cells),
        "unaggregated_rows": unaggregated_rows,
        "incomplete_quarter_rows": incomplete_quarter_rows,
        "aggregate_cell_count": len(cells),
        "observed_report_date_min_utc": min(report_dates).date().isoformat() if report_dates else None,
        "observed_report_date_max_utc": max(report_dates).date().isoformat() if report_dates else None,
        "cells": cells,
        "limitations": [
            "Historical/preliminary source; not live dispatch.",
            "Counts are source records, not unique incidents or people.",
            "No event identifiers, offence text, coordinates, address joins, or rankings are emitted.",
            "Only fully covered report quarters are included.",
            "Public export remains disabled; no suppression policy is selected.",
        ],
    }


def write_candidate_atomically(path: Path, candidate: dict[str, Any]) -> None:
    """Write a private candidate file with last-good retention on failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = handle.name
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def export_public(*_args: Any, **_kwargs: Any) -> None:
    raise PublicExportDisabled(
        "Public CSI export is disabled until the source and aggregate privacy policy are reviewed"
    )

