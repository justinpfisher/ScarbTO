"""Synthetic-only projection from validated ArcGIS grouped-statistics output."""
from __future__ import annotations

import re
from datetime import datetime, time, timezone
from typing import Any

import csi_adapter as csi


ATTRIBUTION = "Contains information licensed under the Open Government Licence - Ontario."
ROOT_KEYS = {
    "publication_status", "grain", "count_semantics", "source",
    "neighbourhood_registry_status", "unassigned_note", "attribution",
    "cells", "limitations",
}
SOURCE_KEYS = {
    "name", "service_item_id", "layer_id", "url", "terms_review_url",
    "edit_date_utc", "coverage_start_date", "coverage_end_date",
    "coverage_basis", "queried_at_utc", "schema_sha256",
}
CELL_KEYS = {"neighbourhood_code", "neighbourhood", "category", "report_quarter", "count"}
STAT_KEYS = {"HOOD_158", "CSI_CATEGORY", "source_record_count"}
STAT_METADATA_KEYS = {
    "service_item_id", "layer_id", "layer_name", "edit_date_utc",
    "schema_sha256", "coverage_start_date", "coverage_end_date",
    "coverage_basis", "queried_at_utc",
}
QUERY_BOUND_KEYS = {
    "report_quarter", "start_utc", "end_utc", "count_before_where",
    "statistics_where", "count_after_where",
}
STAT_RESPONSE_REQUIRED_KEYS = {
    "objectIdFieldName", "globalIdFieldName", "geometryType",
    "spatialReference", "fields", "features", "exceededTransferLimit",
}
STAT_RESPONSE_OPTIONAL_KEYS = {"displayFieldName", "fieldAliases", "hasZ", "hasM"}
STAT_FIELD_TYPES = {
    "HOOD_158": "esriFieldTypeString",
    "CSI_CATEGORY": "esriFieldTypeString",
    "source_record_count": "esriFieldTypeInteger",
}
STAT_FIELD_METADATA_KEYS = {"name", "type", "alias", "sqlType", "length", "nullable", "editable"}


def _validate_registry(registry: dict[str, str]) -> dict[str, str]:
    if not isinstance(registry, dict) or not registry:
        raise csi.ContractError("A nonempty verified neighbourhood registry is required")
    result: dict[str, str] = {}
    names: set[str] = set()
    for code, name in registry.items():
        if not isinstance(code, str) or not re.fullmatch(r"\d{3}", code):
            raise csi.ContractError("Registry codes must be three-digit HOOD_158 identifiers")
        if not isinstance(name, str) or not name.strip() or name.strip().upper() == csi.UNASSIGNED_NEIGHBOURHOOD:
            raise csi.ContractError("Registry names must be assigned nonempty labels")
        name = name.strip()
        if name.casefold() in names:
            raise csi.ContractError("Registry display names must be unique")
        result[code] = name
        names.add(name.casefold())
    return result


def _validate_projection_keys(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != ROOT_KEYS:
        raise csi.ContractError("Projection root contains missing or unexpected keys")
    if not isinstance(value["source"], dict) or set(value["source"]) != SOURCE_KEYS:
        raise csi.ContractError("Projection source contains missing or unexpected keys")
    if not isinstance(value["cells"], list):
        raise csi.ContractError("Projection cells must be a list")
    for cell in value["cells"]:
        if not isinstance(cell, dict) or set(cell) != CELL_KEYS:
            raise csi.ContractError("Projection cell contains missing or unexpected keys")
    if not isinstance(value["grain"], list) or not isinstance(value["limitations"], list):
        raise csi.ContractError("Projection descriptive fields have invalid types")


def _quarter_query_interval(report_quarter: str) -> tuple[datetime, datetime, str]:
    if not isinstance(report_quarter, str) or not re.fullmatch(r"\d{4}-Q[1-4]", report_quarter):
        raise csi.ContractError("Projection requires one explicit report quarter")
    year, quarter = map(int, report_quarter.split("-Q"))
    first_local, last_local = csi._quarter_interval_toronto(year, quarter)
    if quarter == 4:
        next_local = first_local.replace(year=year + 1, month=1, day=1)
    else:
        next_local = first_local.replace(month=first_local.month + 3, day=1)
    start = datetime.combine(first_local, time.min, tzinfo=csi.TORONTO).astimezone(timezone.utc)
    end = datetime.combine(next_local, time.min, tzinfo=csi.TORONTO).astimezone(timezone.utc)
    start_text = start.strftime("%Y-%m-%d %H:%M:%S")
    end_text = end.strftime("%Y-%m-%d %H:%M:%S")
    where = f"REPORT_DATE >= TIMESTAMP '{start_text}' AND REPORT_DATE < TIMESTAMP '{end_text}'"
    return start, end, where


def _validate_query_bounds(bounds: Any) -> str:
    if not isinstance(bounds, dict) or set(bounds) != QUERY_BOUND_KEYS:
        raise csi.ContractError("Quarter query bounds are missing or unexpected")
    quarter = bounds["report_quarter"]
    expected_start, expected_end, expected_where = _quarter_query_interval(quarter)
    try:
        start = csi.parse_utc(bounds["start_utc"], "query start")
        end = csi.parse_utc(bounds["end_utc"], "query end")
    except (KeyError, TypeError, ValueError) as exc:
        raise csi.ContractError("Quarter query bounds are invalid") from exc
    if start != expected_start or end != expected_end:
        raise csi.ContractError("Query interval does not match its Toronto report quarter")
    for key in ("count_before_where", "statistics_where", "count_after_where"):
        if bounds[key] != expected_where:
            raise csi.ContractError("Count and grouped queries use different quarter bounds")
    local_start = start.astimezone(csi.TORONTO)
    derived_quarter = f"{local_start.year}-Q{((local_start.month - 1) // 3) + 1}"
    if quarter != derived_quarter:
        raise csi.ContractError("Report quarter does not match the Toronto query interval")
    return derived_quarter


def _validate_statistics_headers(response: Any) -> None:
    if not isinstance(response, dict):
        raise csi.ContractError("ArcGIS statistics response is invalid")
    keys = set(response)
    if not STAT_RESPONSE_REQUIRED_KEYS <= keys or keys - STAT_RESPONSE_REQUIRED_KEYS - STAT_RESPONSE_OPTIONAL_KEYS:
        raise csi.ContractError("ArcGIS statistics response has missing or unexpected headers")
    if response["geometryType"] is not None:
        raise csi.ContractError("Grouped statistics response unexpectedly describes geometry")
    for key in ("objectIdFieldName", "globalIdFieldName"):
        if response[key] not in (None, ""):
            raise csi.ContractError("Grouped statistics response unexpectedly identifies source records")
    spatial = response["spatialReference"]
    if not isinstance(spatial, dict) or set(spatial) - {"wkid", "latestWkid"} or not spatial:
        raise csi.ContractError("Grouped statistics spatial reference is invalid")
    if any(value != 4326 for value in spatial.values()):
        raise csi.ContractError("Grouped statistics spatial reference is unexpected")
    fields = response["fields"]
    if not isinstance(fields, list) or len(fields) != len(STAT_FIELD_TYPES):
        raise csi.ContractError("Grouped statistics field metadata is invalid")
    aliases: dict[str, str] = {}
    for field in fields:
        if not isinstance(field, dict) or set(field) - STAT_FIELD_METADATA_KEYS:
            raise csi.ContractError("Grouped statistics field metadata has unexpected keys")
        name = field.get("name")
        if name not in STAT_FIELD_TYPES or field.get("type") != STAT_FIELD_TYPES[name]:
            raise csi.ContractError("Grouped statistics field name or type is unexpected")
        alias = field.get("alias", name)
        if not isinstance(alias, str) or not alias:
            raise csi.ContractError("Grouped statistics field alias is invalid")
        aliases[name] = alias
    if set(aliases) != set(STAT_FIELD_TYPES):
        raise csi.ContractError("Grouped statistics fields are incomplete")
    if "fieldAliases" in response and response["fieldAliases"] != aliases:
        raise csi.ContractError("Grouped statistics field aliases do not match the schema")
    if response.get("displayFieldName", "") not in ("", None):
        raise csi.ContractError("Grouped statistics display field is unexpected")
    if response.get("hasZ", False) is not False or response.get("hasM", False) is not False:
        raise csi.ContractError("Grouped statistics response unexpectedly includes Z or M values")


def build_projection_candidate(
    statistics: dict[str, Any],
    *,
    neighbourhood_registry: dict[str, str],
) -> dict[str, Any]:
    """Validate a count-controlled grouped response and emit a disabled candidate.

    `statistics` is a synthetic representation of the ArcGIS grouped response:
    source metadata before/after, count controls before/after, and rows grouped
    by HOOD_158 and CSI_CATEGORY. Raw feature rows are deliberately not accepted.
    """
    if not isinstance(statistics, dict) or set(statistics) != {
        "metadata_before", "metadata_after", "count_before", "count_after", "statistics_response", "query_bounds"
    }:
        raise csi.ContractError("Grouped statistics response has an unexpected envelope")
    before = statistics["metadata_before"]
    after = statistics["metadata_after"]
    if (
        not isinstance(before, dict) or not isinstance(after, dict)
        or set(before) != STAT_METADATA_KEYS or set(after) != STAT_METADATA_KEYS
    ):
        raise csi.ContractError("Grouped statistics metadata is missing")
    version_fields = (
        "service_item_id", "layer_id", "layer_name", "edit_date_utc",
        "schema_sha256", "coverage_start_date", "coverage_end_date", "coverage_basis",
    )
    if any(before.get(key) != after.get(key) for key in version_fields):
        raise csi.ContractError("Source metadata changed during grouped statistics query")
    if (
        before["service_item_id"] != csi.SERVICE_ITEM_ID
        or before["layer_id"] != csi.LAYER_ID
        or before["layer_name"] != csi.SOURCE_NAME
    ):
        raise csi.ContractError("Grouped statistics source identity is unexpected")
    if before["coverage_basis"] != "published_extract_metadata":
        raise csi.ContractError("Quarter completeness requires published coverage metadata")
    for key in ("edit_date_utc", "queried_at_utc"):
        csi.parse_utc(before[key], f"metadata {key}")
    csi.parse_utc(after["queried_at_utc"], "metadata after queried_at_utc")
    if not isinstance(before["schema_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", before["schema_sha256"]):
        raise csi.ContractError("Grouped statistics schema fingerprint is invalid")
    count_before, count_after = statistics["count_before"], statistics["count_after"]
    if type(count_before) is not int or count_before < 0 or type(count_after) is not int or count_after != count_before:
        raise csi.ContractError("Source count changed or is invalid across grouped query")
    report_quarter = _validate_query_bounds(statistics["query_bounds"])
    registry = _validate_registry(neighbourhood_registry)

    try:
        year, quarter = map(int, report_quarter.split("-Q"))
        quarter_start, quarter_end = csi._quarter_interval_toronto(year, quarter)
        coverage_start = csi.parse_source_coverage_date(before["coverage_start_date"], "coverage start")
        coverage_end = csi.parse_source_coverage_date(before["coverage_end_date"], "coverage end")
    except (KeyError, TypeError, ValueError) as exc:
        raise csi.ContractError("Source coverage metadata is invalid") from exc
    if coverage_start > quarter_start or coverage_end < quarter_end:
        raise csi.ContractError("Requested quarter is unavailable or incomplete in published source coverage")

    response = statistics["statistics_response"]
    _validate_statistics_headers(response)
    if response.get("exceededTransferLimit", False) is not False:
        raise csi.ContractError("ArcGIS statistics response is transfer-limited")
    groups = response.get("features")
    if not isinstance(groups, list):
        raise csi.ContractError("ArcGIS statistics response features must be a list")
    counts: dict[tuple[str, str], int] = {}
    seen_groups: set[tuple[str, str]] = set()
    accounted_total = 0
    for feature in groups:
        if not isinstance(feature, dict) or set(feature) != {"attributes"}:
            raise csi.ContractError("Grouped statistics feature has unexpected fields or geometry")
        group = feature.get("attributes")
        if not isinstance(group, dict) or set(group) != STAT_KEYS:
            raise csi.ContractError("Grouped statistics row has missing or unexpected fields")
        code = group["HOOD_158"]
        category = group["CSI_CATEGORY"]
        count = group["source_record_count"]
        if not isinstance(code, str) or (code != csi.UNASSIGNED_NEIGHBOURHOOD and code not in registry):
            raise csi.ContractError("Grouped statistics contain an unregistered HOOD_158 code")
        if not isinstance(category, str) or category not in csi.KNOWN_CSI_CATEGORIES:
            raise csi.ContractError("Grouped statistics contain an unknown CSI category")
        if type(count) is not int or count <= 0:
            raise csi.ContractError("Returned grouped statistics counts must be positive integers")
        key = (code, category)
        if key in seen_groups:
            raise csi.ContractError("Duplicate neighbourhood/category statistics group")
        seen_groups.add(key)
        accounted_total += count
        if code == csi.UNASSIGNED_NEIGHBOURHOOD:
            continue
        counts[key] = count
    if accounted_total != count_before:
        raise csi.ContractError("Grouped statistics do not reconcile to count control")
    if count_before > 0 and not any(code != csi.UNASSIGNED_NEIGHBOURHOOD for code, _ in counts):
        raise csi.ContractError("No assigned grouped statistics exist for the requested quarter")

    cells = []
    for code, name in sorted(registry.items()):
        for category in sorted(csi.KNOWN_CSI_CATEGORIES):
            value = counts.get((code, category), 0)
            cells.append({
                "neighbourhood_code": code,
                "neighbourhood": name,
                "category": category,
                "report_quarter": report_quarter,
                "count": value if value >= 5 else "0-4",
            })

    candidate = {
        "publication_status": "disabled_pending_verified_neighbourhood_registry_and_privacy_review",
        "grain": ["neighbourhood", "CSI category", "Toronto report quarter"],
        "count_semantics": "source records, not unique incidents or people",
        "source": {
            "name": csi.SOURCE_NAME,
            "service_item_id": before["service_item_id"],
            "layer_id": before["layer_id"],
            "url": csi.SOURCE_URL,
            "terms_review_url": csi.TPS_TERMS_URL,
            "edit_date_utc": before["edit_date_utc"],
            "coverage_start_date": before["coverage_start_date"],
            "coverage_end_date": before["coverage_end_date"],
            "coverage_basis": before["coverage_basis"],
            "queried_at_utc": after["queried_at_utc"],
            "schema_sha256": before["schema_sha256"],
        },
        "neighbourhood_registry_status": "caller_supplied_synthetic_or_unverified_registry",
        "unassigned_note": "Some source records may lack a verified neighbourhood assignment; no exact unassigned total is exposed.",
        "attribution": ATTRIBUTION,
        "cells": cells,
        "limitations": [
            "Historical and preliminary TPS data; not live dispatch.",
            "Counts are source records, not unique incidents or people.",
            "Values from zero through four are banded as 0-4; values of five or more are exact.",
            "No marginal totals, rankings, overlapping time grains, event identifiers, offence text, event dates, coordinates, addresses, or joins are emitted.",
            "Banding limits direct small-cell republication but is not an anonymity guarantee or legal threshold.",
            "Public output remains disabled until a complete official HOOD_158 registry and privacy review are qualified.",
        ],
    }
    _validate_projection_keys(candidate)
    return candidate


