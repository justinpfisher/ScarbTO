"""Synthetic-only Toronto permit/development source normalizers.

No CKAN transport, geocoder, CRS conversion, scheduler, or public exporter is
included. Real-data ingestion and publication remain disabled.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import math
import re
from typing import Any
from urllib.parse import urlparse


PUBLICATION_ENABLED = False
FALLBACK_PLANNING_URL = "https://www.toronto.ca/city-government/planning-development/application-information-centre/"
ALLOWED_TORONTO_HOSTS = {"www.toronto.ca", "secure.toronto.ca"}
SCARBOROUGH_WARDS = {20, 21, 22, 23, 24, 25}
PLANNING_XY_SOURCE_CRS = "NAD27 / MTM Zone 10"


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


def _optional_source_text(row: dict[str, Any], field: str) -> str | None:
    value = row.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise PermitContractError(f"{field} must remain source text")
    return value.strip() or None


def _source_number(row: dict[str, Any], field: str, *, integer_only: bool = False) -> tuple[int | float | None, bool]:
    """Normalize a safe nonnegative numeric source value without retaining prose."""
    value = row.get(field)
    if value is None or value == "":
        return None, False
    if isinstance(value, bool):
        return None, True
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None, False
        if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", text):
            return None, True
        text = text.replace(",", "")
    elif type(value) in (int, float):
        text = str(value)
    else:
        return None, True
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None, True
    if not number.is_finite() or number < 0:
        return None, True
    if integer_only and number != number.to_integral_value():
        return None, True
    if number == number.to_integral_value():
        return int(number), False
    converted = float(number)
    if not math.isfinite(converted):
        return None, True
    return converted, False


def _planning_source_coordinates(row: dict[str, Any]) -> tuple[dict[str, str] | None, str | None]:
    """Retain source X/Y as explicitly projected coordinates; never treat them as lon/lat."""
    x, y = row.get("X"), row.get("Y")
    if x in (None, "") and y in (None, ""):
        return None, None
    if x in (None, "") or y in (None, ""):
        return None, "planning_xy:incomplete"
    if type(x) not in (str, int, float) or type(y) not in (str, int, float) or isinstance(x, bool) or isinstance(y, bool):
        return None, "planning_xy:invalid_numeric"
    x_text, y_text = str(x).strip(), str(y).strip()
    number_pattern = r"-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?"
    if not re.fullmatch(number_pattern, x_text) or not re.fullmatch(number_pattern, y_text):
        return None, "planning_xy:invalid_numeric"
    if not math.isfinite(float(x_text.replace(",", ""))) or not math.isfinite(float(y_text.replace(",", ""))):
        return None, "planning_xy:invalid_numeric"
    digest = sha256(
        (PLANNING_XY_SOURCE_CRS + "\0" + x_text + "\0" + y_text).encode("utf-8")
    ).hexdigest()
    return {
        "source_location_key": digest,
        "source_coordinate_reference_system": PLANNING_XY_SOURCE_CRS,
    }, None


def _date_value(row: dict[str, Any], field: str) -> str | None:
    value = row.get(field)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise PermitContractError(f"{field} must remain a source date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise PermitContractError(f"{field} must be an ISO calendar date") from exc
    if parsed.isoformat() != value:
        raise PermitContractError(f"{field} must be an ISO calendar date")
    return value


def _planning_submitted_value(row: dict[str, Any]) -> tuple[str | None, str | None]:
    """Preserve DATE_SUBMITTED's source form without assigning a timezone."""
    value = row.get("DATE_SUBMITTED")
    if value is None or value == "":
        return None, None
    if not isinstance(value, str):
        raise PermitContractError("DATE_SUBMITTED must remain source text")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise PermitContractError("DATE_SUBMITTED must be an ISO date or timestamp") from exc
        if parsed.isoformat() != value:
            raise PermitContractError("DATE_SUBMITTED must be an ISO date or timestamp")
        return value, None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?", value):
        raise PermitContractError("DATE_SUBMITTED must be an ISO date or timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PermitContractError("DATE_SUBMITTED must be an ISO date or timestamp") from exc
    return value[:10], value


def _oar_geometry_value(value: Any) -> list[Any] | None:
    """Parse OAR CSV geometry text and accept only Point or singleton MultiPoint."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, dict):
        return None
    geometry_type = value.get("type")
    coordinates = value.get("coordinates")
    if geometry_type == "Point" and isinstance(coordinates, list) and len(coordinates) == 2:
        return coordinates
    if (
        geometry_type == "MultiPoint" and isinstance(coordinates, list)
        and len(coordinates) == 1 and isinstance(coordinates[0], list)
        and len(coordinates[0]) == 2
    ):
        return coordinates[0]
    return None


def _point_on_segment(x: float, y: float, a: list[Any], b: list[Any]) -> bool:
    cross = (x - a[0]) * (b[1] - a[1]) - (y - a[1]) * (b[0] - a[0])
    if abs(cross) > 1e-10:
        return False
    return min(a[0], b[0]) - 1e-10 <= x <= max(a[0], b[0]) + 1e-10 and min(a[1], b[1]) - 1e-10 <= y <= max(a[1], b[1]) + 1e-10


def _validate_ring(ring: list[list[float]]) -> None:
    if not isinstance(ring, list) or len(ring) < 4:
        raise PermitContractError("Neighbourhood polygon ring is malformed")
    if ring[0] != ring[-1]:
        raise PermitContractError("Neighbourhood polygon ring must be closed")
    for position in ring:
        if (
            not isinstance(position, (list, tuple)) or len(position) < 2
            or type(position[0]) not in (int, float) or type(position[1]) not in (int, float)
            or not math.isfinite(position[0]) or not math.isfinite(position[1])
        ):
            raise PermitContractError("Neighbourhood polygon coordinates must be numeric")
        if not (-180 <= position[0] <= 180 and -90 <= position[1] <= 90):
            raise PermitContractError("Neighbourhood polygon coordinates must be WGS84")


def _ring_contains(lon: float, lat: float, ring: list[list[float]]) -> bool:
    _validate_ring(ring)
    inside = False
    for index, current in enumerate(ring):
        prior = ring[index - 1]
        if _point_on_segment(lon, lat, prior, current):
            return True
        if (current[1] > lat) != (prior[1] > lat):
            crossing = (prior[0] - current[0]) * (lat - current[1]) / (prior[1] - current[1]) + current[0]
            if lon < crossing:
                inside = not inside
    return inside


def _validated_neighbourhood_polygons(features: list[dict[str, Any]]) -> list[list[list[list[float]]]]:
    if not isinstance(features, list) or not features:
        raise PermitContractError("Scarborough neighbourhood polygons are required")
    normalized_polygons: list[list[list[list[float]]]] = []
    for feature in features:
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not isinstance(geometry, dict):
            raise PermitContractError("Neighbourhood feature geometry is missing")
        if geometry.get("type") == "Polygon":
            polygons = [geometry.get("coordinates")]
        elif geometry.get("type") == "MultiPolygon":
            polygons = geometry.get("coordinates")
        else:
            raise PermitContractError("Neighbourhood geometry must be Polygon or MultiPolygon")
        if not isinstance(polygons, list):
            raise PermitContractError("Neighbourhood polygon coordinates are malformed")
        if not polygons:
            raise PermitContractError("Neighbourhood feature has no polygon geometry")
        for rings in polygons:
            if not isinstance(rings, list) or not rings or not isinstance(rings[0], list):
                raise PermitContractError("Neighbourhood polygon rings are malformed")
            for ring in rings:
                _validate_ring(ring)
            normalized_polygons.append(rings)
    if not normalized_polygons:
        raise PermitContractError("Scarborough neighbourhood polygon set is empty")
    return normalized_polygons


def _point_in_validated_polygons(lon: float, lat: float, polygons: list[list[list[list[float]]]]) -> bool:
    for rings in polygons:
        if _ring_contains(lon, lat, rings[0]) and not any(_ring_contains(lon, lat, hole) for hole in rings[1:]):
            return True
    return False


def point_in_scarborough_neighbourhoods(lon: float, lat: float, features: list[dict[str, Any]]) -> bool:
    """Test WGS84 point against the supplied authoritative neighbourhood polygons."""
    if (
        type(lon) not in (int, float) or type(lat) not in (int, float)
        or not math.isfinite(lon) or not math.isfinite(lat)
        or not (-180 <= lon <= 180 and -90 <= lat <= 90)
    ):
        raise PermitContractError("Point must be finite WGS84 coordinates")
    return _point_in_validated_polygons(float(lon), float(lat), _validated_neighbourhood_polygons(features))


def normalize_oar_address_points(
    rows: list[dict[str, Any]], *, neighbourhood_features: list[dict[str, Any]], geometry_crs: str
) -> dict[str, Any]:
    """Map the qualified OAR4326 WARD/ADDRESS_FULL/geometry schema with explicit accounting."""
    if not isinstance(rows, list):
        raise PermitContractError("OAR rows must be a list")
    if geometry_crs != "EPSG:4326":
        raise PermitContractError("OAR geometry CRS must be explicitly qualified as EPSG:4326")
    boundary_polygons = _validated_neighbourhood_polygons(neighbourhood_features)
    points: dict[int, dict[str, Any]] = {}
    grouped_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    rejected = 0
    for row in rows:
        if not isinstance(row, dict):
            rejected += 1
            continue
        point_id = row.get("ADDRESS_POINT_ID")
        if isinstance(point_id, str) and point_id.isascii() and point_id.isdecimal():
            point_id = int(point_id)
        if type(point_id) is not int or point_id <= 0:
            rejected += 1
            continue
        grouped_rows[point_id].append(row)
    unlocated = 0
    for point_id, occurrences in grouped_rows.items():
        signatures = {
            json.dumps({
                "ADDRESS_ID": row.get("ADDRESS_ID"),
                "WARD": row.get("WARD"),
                "ADDRESS_FULL": row.get("ADDRESS_FULL"),
                "geometry": row.get("geometry"),
            }, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
            for row in occurrences
        }
        if len(signatures) > 1:
            rejected += len(occurrences)
            continue
        if len(occurrences) > 1:
            rejected += len(occurrences) - 1
        row = occurrences[0]
        ward = _qualified_ward(row.get("WARD"))
        address = row.get("ADDRESS_FULL")
        if ward is None or not isinstance(address, str) or not address.strip():
            rejected += 1
            continue
        geometry = row.get("geometry")
        if geometry is None or geometry == "":
            unlocated += 1
            continue
        coordinates = _oar_geometry_value(geometry)
        if ward is None or not isinstance(address, str) or not address.strip():
            rejected += 1
            continue
        if not isinstance(coordinates, list) or len(coordinates) != 2 or any(type(value) not in (int, float) for value in coordinates):
            rejected += 1
            continue
        lon, lat = coordinates
        if not all(math.isfinite(value) for value in (lon, lat)) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
            rejected += 1
            continue
        if not _point_in_validated_polygons(float(lon), float(lat), boundary_polygons):
            rejected += 1
            continue
        points[point_id] = {
            "ADDRESS_POINT_ID": point_id,
            "ADDRESS_ID": row.get("ADDRESS_ID"),
            "address": address.strip(),
            "longitude": float(lon),
            "latitude": float(lat),
            "WARD_NUMBER": int(ward),
        }
    total = len(rows)
    return {
        "address_points": [points[point_id] for point_id in sorted(points)],
        "total_count": total,
        "located_count": len(points),
        "unlocated_count": unlocated,
        "rejected_count": rejected,
        "accounted_count": len(points) + unlocated + rejected,
    }


def _official_url(value: Any, *, fallback: str | None = FALLBACK_PLANNING_URL) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return fallback
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_TORONTO_HOSTS:
        return fallback
    if parsed.username or parsed.password:
        return fallback
    return candidate


def _source_address(row: dict[str, Any]) -> str | None:
    for field in ("ADDRESS", "STREET_ADDRESS", "address"):
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    number = row.get("STREET_NUM")
    name = row.get("STREET_NAME")
    if number is None and not name:
        return None
    if number is None or not isinstance(name, str) or not name.strip():
        raise PermitContractError("Incomplete source street address components")
    components = [str(number).strip(), name.strip()]
    for field in ("STREET_TYPE", "STREET_DIRECTION"):
        value = row.get(field)
        if value is not None and str(value).strip():
            components.append(str(value).strip())
    return " ".join(components)


def _address_match_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


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
    # Broad Toronto-area sanity bounds only; ward polygon membership remains a
    # separate activation check.
    if not (-79.9 <= lon <= -78.8 and 43.4 <= lat <= 44.1):
        raise PermitContractError("OAR point is outside the qualified Toronto-area envelope")
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
    oar_accounting: dict[str, Any] | None = None,
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
    if oar_accounting is not None:
        names = ("total_count", "located_count", "unlocated_count", "rejected_count", "accounted_count")
        if any(type(oar_accounting.get(name)) is not int or oar_accounting[name] < 0 for name in names):
            raise PermitContractError("OAR mapper accounting must contain nonnegative integer counts")
        if (
            oar_accounting["located_count"] != len(points)
            or oar_accounting["accounted_count"] != oar_accounting["total_count"]
            or oar_accounting["located_count"] + oar_accounting["unlocated_count"] + oar_accounting["rejected_count"] != oar_accounting["total_count"]
        ):
            raise PermitContractError("OAR mapper accounting does not reconcile with mapped points")

    normalized_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    quarantined: list[str] = []
    unlocated_permit_count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise PermitContractError("Permit row must be an object")
        permit_number = _required_string(row, "PERMIT_NUM")
        revision = _required_string(row, "REVISION_NUM")
        permit_type = _required_string(row, "PERMIT_TYPE")
        status_value = row.get("STATUS")
        normalized_status = _optional_source_text(row, "STATUS")
        key = (permit_number, revision)
        geo_id = row.get("GEO_ID")
        location = _address_for_geo_id(geo_id, points)
        if location is None:
            unlocated_permit_count += 1
        estimated_cost, cost_invalid = _source_number(row, "EST_CONST_COST")
        units_created, units_created_invalid = _source_number(
            row, "DWELLING_UNITS_CREATED", integer_only=True
        )
        units_lost, units_lost_invalid = _source_number(
            row, "DWELLING_UNITS_LOST", integer_only=True
        )
        quality_flags = [
            field + ":invalid_numeric"
            for field, invalid in (
                ("EST_CONST_COST", cost_invalid),
                ("DWELLING_UNITS_CREATED", units_created_invalid),
                ("DWELLING_UNITS_LOST", units_lost_invalid),
            )
            if invalid
        ]
        source_address = _source_address(row)
        if source_address and location and location.get("address"):
            if _address_match_key(source_address) != _address_match_key(location["address"]):
                raise PermitContractError("Source permit address disagrees with its OAR point")
        display_address = location["address"] if location else source_address
        item = {
            "record_type": "permit",
            "record_key": f"permit:{permit_number}:{revision}",
            "permit_number": permit_number,
            "revision": revision,
            "source_collection": source_collection,
            "permit_type": permit_type,
            "status": normalized_status,
            "raw_status": status_value,
            "application_date": _date_value(row, "APPLICATION_DATE"),
            "issued_date": _date_value(row, "ISSUED_DATE"),
            "completed_date": _date_value(row, "COMPLETED_DATE"),
            "estimated_cost": estimated_cost,
            "dwelling_units_created": units_created,
            "dwelling_units_lost": units_lost,
            "quality_flags": quality_flags,
            "address": display_address,
            "ward": location["ward"] if location else None,
            "locations": [location] if location else [],
            "official_url": _official_url(row.get("APPLICATION_URL"), fallback=None),
            "construction_state": "not_inferred",
        }
        stable = {
            k: item[k] for k in (
                "record_type", "record_key", "permit_type", "status", "application_date",
                "issued_date", "completed_date", "estimated_cost", "dwelling_units_created",
                "dwelling_units_lost", "quality_flags", "address", "ward"
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
        "location_accounting": {
            "address_points_total": oar_accounting.get("total_count") if oar_accounting else None,
            "address_points_located": oar_accounting.get("located_count") if oar_accounting else len(points),
            "address_points_unlocated": oar_accounting.get("unlocated_count") if oar_accounting else None,
            "address_points_rejected": oar_accounting.get("rejected_count") if oar_accounting else None,
            "permit_rows_unlocated": unlocated_permit_count,
        },
    }


def combine_permit_collections(*collections: dict[str, Any]) -> dict[str, Any]:
    """Quarantine active/cleared conflicts rather than guessing project identity."""
    entries: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    quarantined: set[str] = set()
    accounting: dict[str, int] = {}
    for collection in collections:
        if collection.get("source_collection") not in {"active", "cleared"}:
            raise PermitContractError("Unexpected permit collection")
        for row in collection.get("records", []):
            entries[(row["permit_number"], row["revision"])].append(row)
        quarantined.update(collection.get("quarantined_record_keys", []))
        for name, value in collection.get("location_accounting", {}).items():
            if type(value) is int:
                if name == "permit_rows_unlocated":
                    accounting[name] = accounting.get(name, 0) + value
                elif name in accounting and accounting[name] != value:
                    raise PermitContractError("OAR location accounting changed across permit collections")
                else:
                    accounting[name] = value
    records = []
    for key, matches in sorted(entries.items()):
        fingerprints = {row["fingerprint"] for row in matches}
        if len(fingerprints) > 1:
            quarantined.update(row["record_key"] for row in matches)
        elif matches[0]["record_key"] in quarantined:
            continue
        else:
            # Prefer the current active collection when an identical row is
            # present in both snapshots; output must not depend on argument
            # ordering.
            records.append(sorted(
                matches,
                key=lambda row: (row["source_collection"] != "active", row["source_collection"]),
            )[0])
    return {
        "publication_status": "disabled_pending_source_and_privacy_review",
        "records": records,
        "quarantined_record_keys": sorted(quarantined),
        "location_accounting": dict(accounting),
    }


def normalize_development_applications(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Group source address rows by folder/application while retaining all locations."""
    groups: dict[str, dict[str, Any]] = {}
    quarantined: set[str] = set()
    folders_by_application: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if not isinstance(row, dict):
            continue
        application_number = row.get("APPLICATION#")
        folder = row.get("FOLDERRSN")
        if isinstance(application_number, str) and application_number.strip() and folder not in (None, ""):
            if isinstance(folder, bool) or not isinstance(folder, (str, int)):
                continue
            folder_value = str(folder).strip()
            if folder_value:
                folders_by_application[application_number.strip()].add(folder_value)
    ambiguous_applications = {
        application for application, folders in folders_by_application.items() if len(folders) > 1
    }
    for row in rows:
        if not isinstance(row, dict):
            raise PermitContractError("Development row must be an object")
        ward = _qualified_ward(row.get("WARD_NUMBER"))
        if ward is None:
            continue
        application_number = _required_string(row, "APPLICATION#")
        folder = row.get("FOLDERRSN")
        if application_number in ambiguous_applications:
            folders = folders_by_application[application_number]
            if folders:
                quarantined.update(f"development:folder:{value}" for value in folders)
            else:
                quarantined.add(f"development:application:{application_number}")
            continue
        if folder is not None and folder != "":
            if not isinstance(folder, (str, int)) or isinstance(folder, bool):
                raise PermitContractError("FOLDERRSN must be a string or integer")
            folder_value = str(folder).strip()
            if not folder_value:
                raise PermitContractError("FOLDERRSN cannot be blank")
            key = f"development:folder:{folder_value}"
            fallback = False
            resolved_from_other_row = False
        elif folders_by_application.get(application_number):
            folder_value = next(iter(folders_by_application[application_number]))
            key = f"development:folder:{folder_value}"
            fallback = False
            resolved_from_other_row = True
        else:
            key = f"development:application:{application_number}"
            fallback = True
            resolved_from_other_row = False
        group = groups.get(key)
        if group and group["application_number"] != application_number:
            quarantined.add(key)
            continue
        application_type = _optional_source_text(row, "APPLICATION_TYPE")
        raw_status = row.get("STATUS")
        status = _optional_source_text(row, "STATUS")
        if group and any(group[field] != value for field, value in (
            ("application_type", application_type),
            ("submission_date", _planning_submitted_value(row)[0]),
            ("submission_timestamp", _planning_submitted_value(row)[1]),
            ("status", status),
            ("official_url", _official_url(row.get("APPLICATION_URL"))),
        )):
            quarantined.add(key)
            continue
        if group is None:
            group = {
                "record_type": "development_application",
                "record_key": key,
                "application_type": application_type,
                "raw_application_type": row.get("APPLICATION_TYPE"),
                "application_number": application_number,
                "submission_date": _planning_submitted_value(row)[0],
                "submission_timestamp": _planning_submitted_value(row)[1],
                "status": status,
                "raw_status": raw_status,
                "wards": set(),
                "official_url": _official_url(row.get("APPLICATION_URL")),
                "locations": [],
                "quality_flags": set(),
                "folder_fallback_used": fallback,
                "missing_folder_resolved_from_other_row": resolved_from_other_row,
                "construction_state": "not_inferred",
            }
            groups[key] = group
        elif resolved_from_other_row:
            group["missing_folder_resolved_from_other_row"] = True
        group["wards"].add(ward)
        address = _source_address(row)
        if address is not None and not isinstance(address, str):
            raise PermitContractError("address must be source text when present")
        source_coordinates, coordinate_issue = _planning_source_coordinates(row)
        if coordinate_issue:
            group["quality_flags"].add(coordinate_issue)
        if (address and address.strip()) or source_coordinates:
            location = {
                "address": address.strip() if address and address.strip() else None,
                "ward": ward,
                "coordinate_source": "projected_source_only" if source_coordinates else "not_used",
            }
            if source_coordinates:
                location.update(source_coordinates)
            group["locations"].append(location)

    records = []
    for key, group in sorted(groups.items()):
        if key in quarantined:
            continue
        # Multiple locations are retained; stable fingerprint ignores their order.
        unique_locations = {
            (
                location["address"], location["ward"],
                location.get("source_location_key"),
            ): location
            for location in group["locations"]
        }
        group["locations"] = sorted(
            unique_locations.values(),
            key=lambda loc: (
                loc["address"] or "", loc["ward"] or "",
                loc.get("source_location_key") or "",
            ),
        )
        group["wards"] = sorted(group["wards"], key=int)
        group["quality_flags"] = sorted(group["quality_flags"])
        stable_fields = {
            k: group[k] for k in (
                "record_key", "application_type", "application_number", "submission_date", "submission_timestamp",
                "status", "official_url", "folder_fallback_used",
                "missing_folder_resolved_from_other_row", "quality_flags",
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


