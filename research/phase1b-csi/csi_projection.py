"""Synthetic-only fixed-grid projection for the quarterly CSI prototype.

This module requires the existing version-bound validated snapshot and never
enables a publisher. A complete official HOOD_158 registry is still pending.
"""
from __future__ import annotations

import re
from typing import Any

import csi_adapter as csi


def build_projection_candidate(
    rows: csi.ValidatedSnapshot,
    version: csi.SourceVersion,
    *,
    report_quarter: str,
    neighbourhood_registry: dict[str, str],
) -> dict[str, Any]:
    """Build one completed-quarter projection from a validated source snapshot.

    The registry must eventually be the complete verified official HOOD_158
    code/name crosswalk. The caller-supplied synthetic registry used in tests
    does not qualify that prerequisite; output stays explicitly disabled.
    """
    if not isinstance(rows, csi.ValidatedSnapshot):
        raise csi.ContractError("Projection requires a paged validated snapshot")
    if not isinstance(neighbourhood_registry, dict) or not neighbourhood_registry:
        raise csi.ContractError("A nonempty verified neighbourhood registry is required")
    registry: dict[str, str] = {}
    names: set[str] = set()
    for code, name in neighbourhood_registry.items():
        if not isinstance(code, str) or not re.fullmatch(r"(?:00[1-9]|0[1-9][0-9]|1[0-5][0-8])", code):
            raise csi.ContractError("Registry codes must be zero-padded HOOD_158 identifiers")
        if not isinstance(name, str) or not name.strip() or name.strip().upper() == csi.UNASSIGNED_NEIGHBOURHOOD:
            raise csi.ContractError("Registry names must be assigned nonempty labels")
        name = name.strip()
        if name.casefold() in names:
            raise csi.ContractError("Registry display names must be unique")
        registry[code] = name
        names.add(name.casefold())
    if not isinstance(report_quarter, str) or not re.fullmatch(r"\d{4}-Q[1-4]", report_quarter):
        raise csi.ContractError("Projection requires one explicit report quarter")

    internal = csi.build_report_quarter_candidate(rows, version)
    cells_by_key: dict[tuple[str, str], int] = {}
    for cell in internal["cells"]:
        if set(cell) != {"neighbourhood", "category", "report_quarter", "source_record_count"}:
            raise csi.ContractError("Internal aggregate cell has an unexpected schema")
        code, category, quarter, count = (
            cell["neighbourhood"], cell["category"], cell["report_quarter"], cell["source_record_count"]
        )
        if type(count) is not int or count < 0 or category not in csi.KNOWN_CSI_CATEGORIES:
            raise csi.ContractError("Internal aggregate cell has an invalid category or count")
        if quarter != report_quarter:
            continue
        if not isinstance(code, str) or code not in registry:
            raise csi.ContractError("Aggregate cell is outside the supplied verified registry")
        key = (code, category)
        if key in cells_by_key:
            raise csi.ContractError("Duplicate neighbourhood/category aggregate cell")
        cells_by_key[key] = count
    if not cells_by_key:
        raise csi.ContractError("No validated cells exist for the requested completed quarter")

    projected_cells = []
    for code, name in sorted(registry.items()):
        for category in sorted(csi.KNOWN_CSI_CATEGORIES):
            value = cells_by_key.get((code, category), 0)
            projected_cells.append({
                "neighbourhood_code": code,
                "neighbourhood": name,
                "category": category,
                "report_quarter": report_quarter,
                "count": value if value >= 5 else "0-4",
            })

    source = internal["source"]
    return {
        "publication_status": "disabled_pending_verified_neighbourhood_registry_and_privacy_review",
        "grain": ["neighbourhood", "CSI category", "Toronto report quarter"],
        "count_semantics": "source records, not unique incidents or people",
        "source": {key: source[key] for key in (
            "name", "service_item_id", "layer_id", "url", "terms_review_url",
            "edit_date_utc", "coverage_start_date", "coverage_end_date",
            "coverage_basis", "queried_at_utc", "schema_sha256",
        )},
        "neighbourhood_registry_status": "caller_supplied_synthetic_or_unverified_registry",
        "unassigned_note": "Some source records may lack a verified neighbourhood assignment; no exact unassigned total is exposed.",
        "cells": projected_cells,
        "limitations": [
            "Historical and preliminary TPS data; not live dispatch.",
            "Counts are source records, not unique incidents or people.",
            "Values from zero through four are banded as 0-4; values of five or more are exact.",
            "No marginal totals, rankings, overlapping time grains, event identifiers, offence text, event dates, coordinates, addresses, or joins are emitted.",
            "Banding limits direct small-cell republication but is not an anonymity guarantee or legal threshold.",
            "Public output remains disabled until a complete official HOOD_158 registry and privacy review are qualified.",
        ],
    }

