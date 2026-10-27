"""Synthetic-only projection from validated ArcGIS grouped-statistics output."""
from __future__ import annotations

import re
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


def build_projection_candidate(
    statistics: dict[str, Any],
    *,
    report_quarter: str,
    neighbourhood_registry: dict[str, str],
) -> dict[str, Any]:
    """Validate a count-controlled grouped response and emit a disabled candidate.

    `statistics` is a synthetic representation of the ArcGIS grouped response:
    source metadata before/after, count controls before/after, and rows grouped
    by HOOD_158 and CSI_CATEGORY. Raw feature rows are deliberately not accepted.
    """
    if not isinstance(statistics, dict) or set(statistics) != {
        "metadata_before", "metadata_after", "count_before", "count_after", "statistics_response"
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
    if not isinstance(report_quarter, str) or not re.fullmatch(r"\d{4}-Q[1-4]", report_quarter):
        raise csi.ContractError("Projection requires one explicit report quarter")
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
    if not isinstance(response, dict) or set(response) - {"features", "exceededTransferLimit"}:
        raise csi.ContractError("ArcGIS statistics response has an unexpected envelope")
    if response.get("exceededTransferLimit", False) is not False:
        raise csi.ContractError("ArcGIS statistics response is transfer-limited")
    groups = response.get("features")
    if not isinstance(groups, list):
        raise csi.ContractError("ArcGIS statistics response features must be a list")
    counts: dict[tuple[str, str], int] = {}
    accounted_total = 0
    for feature in groups:
        group = feature.get("attributes") if isinstance(feature, dict) else None
        if not isinstance(group, dict) or set(group) != STAT_KEYS:
            raise csi.ContractError("Grouped statistics row has missing or unexpected fields")
        code = group["HOOD_158"]
        category = group["CSI_CATEGORY"]
        count = group["source_record_count"]
        if not isinstance(code, str) or (code != csi.UNASSIGNED_NEIGHBOURHOOD and code not in registry):
            raise csi.ContractError("Grouped statistics contain an unregistered HOOD_158 code")
        if not isinstance(category, str) or category not in csi.KNOWN_CSI_CATEGORIES:
            raise csi.ContractError("Grouped statistics contain an unknown CSI category")
        if type(count) is not int or count < 0:
            raise csi.ContractError("Grouped statistics count must be a nonnegative integer")
        accounted_total += count
        if code == csi.UNASSIGNED_NEIGHBOURHOOD:
            continue
        key = (code, category)
        if key in counts:
            raise csi.ContractError("Duplicate neighbourhood/category statistics group")
        counts[key] = count
    if accounted_total != count_before:
        raise csi.ContractError("Grouped statistics do not reconcile to count control")
    if not any(code != csi.UNASSIGNED_NEIGHBOURHOOD for code, _ in counts):
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


