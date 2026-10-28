"""Hash-pinned validation for the qualified Toronto HOOD_158 registry."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path
from typing import Any

EXPECTED_SHA256 = "0f16bf16cde47f382f21003050a978251f71c258581746d64c9a8c9f5ae8564e"
EXPECTED_BYTES = 108_863
EXPECTED_CODES = 158
EXPECTED_SELECTED = (
    "116", "118", "119", "120", "121", "122", "123", "124", "125", "126",
    "128", "129", "130", "133", "134", "135", "136", "138", "139", "140",
    "141", "142", "143", "144", "145", "146", "147", "148", "156", "157",
)


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class VerifiedNeighbourhoodRegistry:
    sha256: str
    source_effective_date: str
    by_code: dict[str, dict[str, Any]]
    scarborough_codes: tuple[str, ...]

    @property
    def display_names(self) -> dict[str, str]:
        return {code: row["AREA_NAME"] for code, row in self.by_code.items()}

    def lookup_tps_code(self, raw_code: Any, publisher_name: Any = None) -> dict[str, Any]:
        """Join by padded HOOD_158 only; preserve any publisher name mismatch."""
        if not isinstance(raw_code, str) or not re.fullmatch(r"[0-9]{3}", raw_code):
            return {"state": "unassigned_or_invalid", "raw_code": raw_code, "publisher_name": publisher_name}
        row = self.by_code.get(raw_code)
        if row is None:
            return {"state": "unknown_code", "raw_code": raw_code, "publisher_name": publisher_name}
        name_matches = isinstance(publisher_name, str) and publisher_name.strip().casefold() == row["AREA_NAME"].casefold()
        return {
            "state": "matched" if name_matches else "code_matched_name_differs_or_missing",
            "code": raw_code,
            "registry_name": row["AREA_NAME"],
            "publisher_name": publisher_name,
            "registry_area_id": row["AREA_ID"],
        }


def load_verified_registry(path: str | Path) -> VerifiedNeighbourhoodRegistry:
    """Load only the exact independently qualified contract artifact."""
    try:
        payload = Path(path).read_bytes()
    except OSError as exc:
        raise RegistryError("Neighbourhood contract cannot be read") from exc
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != EXPECTED_BYTES or digest != EXPECTED_SHA256:
        raise RegistryError("Neighbourhood contract size or SHA-256 does not match the qualified artifact")
    try:
        contract = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError("Neighbourhood contract is not valid UTF-8 JSON") from exc
    geography = contract.get("geography", {})
    identifier = contract.get("identifier_contract", {})
    if (
        contract.get("schema_version") != 1
        or geography.get("publisher") != "City of Toronto, Social Development, Finance & Administration"
        or geography.get("citation") != "Toronto Social Planning Neighbourhoods v3.0, City of Toronto 2022"
        or geography.get("effective_date") != "2022-04-12"
        or geography.get("count") != EXPECTED_CODES
        or geography.get("publisher_package_id") != "fc443770-ef0a-4025-9c2c-2cb558bfab00"
        or geography.get("publisher_datastore_resource_id") != "5e6095fc-1bef-4776-887c-28d37f722c51"
        or identifier.get("primary_key") != "AREA_SHORT_CODE"
        or identifier.get("format") != "exact publisher three-digit string"
    ):
        raise RegistryError("Contract publisher, edition, resource, or join-key identity is unexpected")

    registry_rows = contract.get("registry")
    crosswalk = contract.get("spatial_crosswalk")
    if not isinstance(registry_rows, list) or len(registry_rows) != EXPECTED_CODES:
        raise RegistryError("Contract does not contain exactly 158 registry rows")
    if not isinstance(crosswalk, list) or len(crosswalk) != EXPECTED_CODES:
        raise RegistryError("Contract does not contain exactly 158 crosswalk rows")
    by_code: dict[str, dict[str, Any]] = {}
    area_ids: set[int] = set()
    for row in registry_rows:
        code = row.get("AREA_SHORT_CODE") if isinstance(row, dict) else None
        name = row.get("AREA_NAME") if isinstance(row, dict) else None
        area_id = row.get("AREA_ID") if isinstance(row, dict) else None
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{3}", code):
            raise RegistryError("Registry contains a non-padded or malformed publisher code")
        if code in by_code or not isinstance(name, str) or not name.strip() or type(area_id) is not int or area_id <= 0 or area_id in area_ids:
            raise RegistryError("Registry contains a duplicate or invalid code/name/area identity")
        if row.get("AREA_LONG_CODE") != code:
            raise RegistryError("Short and long publisher codes disagree")
        by_code[code] = row
        area_ids.add(area_id)

    crosswalk_by_code: dict[str, dict[str, Any]] = {}
    for row in crosswalk:
        code = row.get("code") if isinstance(row, dict) else None
        if not isinstance(code, str) or code not in by_code or code in crosswalk_by_code or type(row.get("selected")) is not bool:
            raise RegistryError("Crosswalk has an unknown, duplicate, or malformed code")
        crosswalk_by_code[code] = row
    if set(crosswalk_by_code) != set(by_code):
        raise RegistryError("Crosswalk code set does not exactly match registry")

    selection = contract.get("scarborough_selection", {})
    selected = tuple(sorted(code for code, row in crosswalk_by_code.items() if row["selected"]))
    declared = selection.get("selected_codes")
    if (
        selection.get("publisher_supplied_membership_attribute") is not False
        or selection.get("area_crs") != "EPSG:2952"
        or selection.get("threshold") != 0.5
        or selection.get("selected_count") != len(EXPECTED_SELECTED)
        or not isinstance(declared, list)
        or tuple(sorted(declared)) != EXPECTED_SELECTED
        or selected != EXPECTED_SELECTED
    ):
        raise RegistryError("Scarborough overlay selection does not match the qualified 30-code set")
    return VerifiedNeighbourhoodRegistry(
        sha256=digest,
        source_effective_date=geography["effective_date"],
        by_code=by_code,
        scarborough_codes=selected,
    )
