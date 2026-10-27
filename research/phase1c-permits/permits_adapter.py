"""Synthetic-only Toronto permit/development source normalizers.

No CKAN transport, geocoder, CRS conversion, scheduler, or public exporter is
included. Real-data ingestion and publication remain disabled.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from typing import Any
from urllib.parse import urlparse


PUBLICATION_ENABLED = False
FALLBACK_PLANNING_URL = "https://www.toronto.ca/city-government/planning-development/application-information-centre/"
ALLOWED_TORONTO_HOSTS = {"www.toronto.ca", "secure.toronto.ca"}
SCARBOROUGH_WARDS = {20, 21, 22, 23, 24, 25}


class PermitContractError(ValueError):
    """Source row or snapshot violates the reviewed contract."""


class PermitExportDisabled(RuntimeError):
    """Public permit output is held pending source and privacy review."""


def validate_snapshot_pages(
    pages: list[dict[str, Any]],
    *,
    generation_before: str,
    generation_after: str,
    total_before: int,
    total_after: int,
    id_field: str = "_id",
) -> list[dict[str, Any]]:
    """Accept only a complete ordered snapshot from one unchanged generation."""
    if not generation_before or generation_before != generation_after:
        raise PermitContractError("Source generation changed during pagination")
    if (
        type(total_before) is not int or type(total_after) is not int
        or total_before < 0 or total_before != total_after
    ):
        raise PermitContractError("Source total changed during pagination")
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    expected_offset = 0
    previous = 0
    for page in pages:
        if (
            not isinstance(page, dict)
            or type(page.get("offset")) is not int
            or page.get("offset") != expected_offset
        ):
            raise PermitContractError("Pages must be contiguous from offset zero")
        items = page.get("records")
        if not isinstance(items, list) or not items:
            raise PermitContractError("Unexpected empty or malformed page")
        if type(page.get("limit")) is not int or page["limit"] < 1 or len(items) > page["limit"]:
            raise PermitContractError("Page exceeds requested limit")
        for row in items:
            if not isinstance(row, dict):
                raise PermitContractError("Each source record must be an object")
            row_id = row.get(id_field)
            if type(row_id) is not int or row_id <= 0:
                raise PermitContractError("Missing numeric datastore row ID")
            if row_id in seen or row_id <= previous:
                raise PermitContractError("Duplicate or unordered datastore row ID")
            seen.add(row_id)
            previous = row_id
            rows.append(row)
        expected_offset += len(items)
    if expected_offset != total_before:
        raise PermitContractError("Incomplete or truncated source snapshot")
    return rows


def _required_string(row: dict[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PermitContractError(f"{field} must be a non-empty string")
    return value.strip()


def _date_value(row: dict[str, Any], field: str) -> str | None:
    value = row.get(field)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise PermitContractError(f"{field} must remain a source date string")
    return value


def _official_url(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return FALLBACK_PLANNING_URL
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_TORONTO_HOSTS:
        return FALLBACK_PLANNING_URL
    if parsed.username or parsed.password:
        return FALLBACK_PLANNING_URL
    return candidate


def _qualified_ward(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        ward = int(value)
    except (TypeError, ValueError):
        return None
    if str(ward) != str(value).strip() and not isinstance(value, int):
        return None
    return str(ward) if ward in SCARBOROUGH_WARDS else None


def _fingerprint(fields: dict[str, Any]) -> str:
    stable = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(stable.encode("utf-8")).hexdigest()


def _address_for_geo_id(
    geo_id: Any, address_points_by_point_id: dict[int, dict[str, Any]]
) -> dict[str, Any] | None:
    if geo_id is None or geo_id == "":
        return None
    # CKAN declares GEO_ID as text although its values identify numeric OAR
    # ADDRESS_POINT_IDs. Accept integers from normalized sources and strict
    # decimal strings from the live datastore; reject lossy/coercive forms.
    if type(geo_id) is int:
        point_id = geo_id
    elif isinstance(geo_id, str) and geo_id.isascii() and geo_id.isdecimal():
        point_id = int(geo_id)
    else:
        raise PermitContractError("GEO_ID must be a numeric string or integer when present")
    if point_id <= 0:
        raise PermitContractError("GEO_ID must be positive when present")
    point = address_points_by_point_id.get(point_id)
    if point is None:
        return None
    if type(point.get("ADDRESS_POINT_ID")) is not int or point["ADDRESS_POINT_ID"] != point_id:
        raise PermitContractError("Address join must use OAR ADDRESS_POINT_ID")
    lon, lat = point.get("longitude"), point.get("latitude")
    ward = _qualified_ward(point.get("WARD_NUMBER"))
    if ward is None:
        return None
    if type(lon) not in (int, float) or type(lat) not in (int, float):
        raise PermitContractError("OAR coordinates must be prequalified WGS84 values")
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise PermitContractError("OAR coordinates are outside WGS84 ranges")
    return {
        "address_point_id": point_id,
        "address": point.get("address") if isinstance(point.get("address"), str) else None,
        "longitude": float(lon),
        "latitude": float(lat),
        "ward": ward,
    }


def normalize_permits(
    rows: list[dict[str, Any]],
    *,
    source_collection: str,
    address_points: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize active/cleared permit rows; never infer construction from status."""
    if source_collection not in {"active", "cleared"}:
        raise PermitContractError("source_collection must be active or cleared")
    points: dict[int, dict[str, Any]] = {}
    for point in address_points:
        point_id = point.get("ADDRESS_POINT_ID")
        if type(point_id) is not int or point_id <= 0:
            raise PermitContractError("OAR ADDRESS_POINT_ID must be a positive integer")
        if point_id in points:
            raise PermitContractError("Duplicate OAR ADDRESS_POINT_ID")
        points[point_id] = point

    normalized_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    quarantined: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise PermitContractError("Permit row must be an object")
        permit_number = _required_string(row, "PERMIT_NUM")
        revision = _required_string(row, "REVISION_NUM")
        permit_type = _required_string(row, "PERMIT_TYPE")
        status_value = row.get("STATUS")
        if status_value is not None and not isinstance(status_value, str):
            raise PermitContractError("STATUS must remain source text")
        key = (permit_number, revision)
        geo_id = row.get("GEO_ID")
        location = _address_for_geo_id(geo_id, points)
        item = {
            "record_type": "permit",
            "record_key": f"{source_collection}:{permit_number}:{revision}",
            "permit_number": permit_number,
            "revision": revision,
            "source_collection": source_collection,
            "permit_type": permit_type,
            "status": status_value,
            "application_date": _date_value(row, "APPLICATION_DATE"),
            "issued_date": _date_value(row, "ISSUED_DATE"),
            "completed_date": _date_value(row, "COMPLETED_DATE"),
            "address": location["address"] if location else None,
            "ward": location["ward"] if location else None,
            "locations": [location] if location else [],
            "official_url": _official_url(row.get("APPLICATION_URL")),
            "construction_state": "not_inferred",
        }
        stable = {
            k: item[k] for k in (
                "record_type", "record_key", "permit_type", "status", "application_date",
                "issued_date", "completed_date", "address", "ward"
            )
        }
        stable["locations"] = sorted(item["locations"], key=lambda loc: loc["address_point_id"])
        item["fingerprint"] = _fingerprint(stable)
        prior = normalized_by_key.get(key)
        if prior is not None and prior["fingerprint"] != item["fingerprint"]:
            quarantined.append(item["record_key"])
            normalized_by_key.pop(key, None)
            continue
        if prior is None and item["record_key"] not in quarantined:
            normalized_by_key[key] = item
    return {
        "publication_status": "disabled_pending_source_and_privacy_review",
        "source_collection": source_collection,
        "coverage_note": "Cleared-permit source begins in 2017; 2000-2016 legacy resource intentionally omitted.",
        "records": [normalized_by_key[key] for key in sorted(normalized_by_key)],
        "quarantined_record_keys": sorted(set(quarantined)),
    }


def combine_permit_collections(*collections: dict[str, Any]) -> dict[str, Any]:
    """Quarantine active/cleared conflicts rather than guessing project identity."""
    entries: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for collection in collections:
        if collection.get("source_collection") not in {"active", "cleared"}:
            raise PermitContractError("Unexpected permit collection")
        for row in collection.get("records", []):
            entries[(row["permit_number"], row["revision"])].append(row)
    records = []
    quarantined = []
    for key, matches in sorted(entries.items()):
        fingerprints = {row["fingerprint"] for row in matches}
        if len(matches) > 1 and (
            len(fingerprints) > 1 or len({row["source_collection"] for row in matches}) > 1
        ):
            quarantined.extend(row["record_key"] for row in matches)
        else:
            records.append(matches[0])
    return {
        "publication_status": "disabled_pending_source_and_privacy_review",
        "records": records,
        "quarantined_record_keys": sorted(quarantined),
    }


def normalize_development_applications(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Group source address rows by folder/application while retaining all locations."""
    groups: dict[str, dict[str, Any]] = {}
    quarantined: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise PermitContractError("Development row must be an object")
        ward = _qualified_ward(row.get("WARD_NUMBER"))
        if ward is None:
            continue
        application_number = _required_string(row, "APPLICATION#")
        folder = row.get("FOLDERRSN")
        if folder is not None and folder != "":
            if not isinstance(folder, (str, int)) or isinstance(folder, bool):
                raise PermitContractError("FOLDERRSN must be a string or integer")
            folder_value = str(folder).strip()
            if not folder_value:
                raise PermitContractError("FOLDERRSN cannot be blank")
            key = f"development:folder:{folder_value}"
            fallback = False
        else:
            key = f"development:application:{application_number}"
            fallback = True
        group = groups.get(key)
        if group and group["application_number"] != application_number:
            quarantined.add(key)
            continue
        if group and any(group[field] != value for field, value in (
            ("application_type", row.get("APPLICATION_TYPE") if isinstance(row.get("APPLICATION_TYPE"), str) else None),
            ("submission_date", _date_value(row, "DATE_SUBMITTED")),
            ("status", row.get("STATUS") if isinstance(row.get("STATUS"), str) else None),
            ("official_url", _official_url(row.get("APPLICATION_URL"))),
        )):
            quarantined.add(key)
            continue
        if group is None:
            group = {
                "record_type": "development_application",
                "record_key": key,
                "application_type": row.get("APPLICATION_TYPE") if isinstance(row.get("APPLICATION_TYPE"), str) else None,
                "application_number": application_number,
                "submission_date": _date_value(row, "DATE_SUBMITTED"),
                "status": row.get("STATUS") if isinstance(row.get("STATUS"), str) else None,
                "wards": set(),
                "official_url": _official_url(row.get("APPLICATION_URL")),
                "locations": [],
                "folder_fallback_used": fallback,
                "construction_state": "not_inferred",
            }
            groups[key] = group
        group["wards"].add(ward)
        address = row.get("address")
        if address is not None and not isinstance(address, str):
            raise PermitContractError("address must be source text when present")
        if address and address.strip():
            group["locations"].append({
                "address": address.strip(),
                "ward": ward,
                "coordinate_source": "not_used",
            })

    records = []
    for key, group in sorted(groups.items()):
        if key in quarantined:
            continue
        # Multiple locations are retained; stable fingerprint ignores their order.
        unique_locations = {
            (location["address"], location["ward"]): location
            for location in group["locations"]
        }
        group["locations"] = sorted(
            unique_locations.values(), key=lambda loc: (loc["address"], loc["ward"] or "")
        )
        group["wards"] = sorted(group["wards"], key=int)
        stable_fields = {
            k: group[k] for k in (
                "record_key", "application_type", "application_number", "submission_date",
                "status", "official_url", "folder_fallback_used",
            )
        }
        stable_fields["wards"] = group["wards"]
        stable_fields["locations"] = group["locations"]
        group["fingerprint"] = _fingerprint(stable_fields)
        records.append(group)
    return {
        "publication_status": "disabled_pending_source_and_privacy_review",
        "records": records,
        "quarantined_record_keys": sorted(quarantined),
    }


def export_public(*_args: Any, **_kwargs: Any) -> None:
    raise PermitExportDisabled(
        "Public permit/development output is disabled pending source, geography, and privacy review"
    )

