"""Offline, aggregate-only projection of an already verified collision receipt.

This validates the receipt's shape/accounting, not its authenticity or geography.
No collector, public exporter, filesystem writer, or network path is invoked.
"""
from datetime import datetime
import re

STATUS = "complete_stable_generation_identity_collision_accounting"
SOURCE_URLS = {
    "active": "https://open.toronto.ca/dataset/building-permits-active-permits/",
    "cleared_since_2017": "https://open.toronto.ca/dataset/building-permits-cleared-permits/",
}
_TIMESTAMP = r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"
_GENERATION_PART = re.compile(_TIMESTAMP + r"(?:Z|[+-][0-9]{2}:[0-9]{2})?")
_UTC = re.compile(_TIMESTAMP.replace("[T ]", "T") + r"(?:Z|\+00:00)")


class ProjectionError(ValueError):
    """Receipt cannot safely support this projection (no input values echoed)."""


def _object(value):
    if not isinstance(value, dict):
        raise ProjectionError("Required receipt object missing or malformed")
    return value


def _count(value):
    if type(value) is not int or value < 0:
        raise ProjectionError("Counts must be nonnegative integers")
    return value


def _timestamp(value, pattern):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ProjectionError("Timestamp format is not permitted")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ProjectionError("Timestamp is not a valid calendar time") from None
    return value


def _generation(value):
    # Existing collector uses one or two CKAN timestamps joined by '|'.
    # Restrict syntax so this allowlisted string cannot carry arbitrary prose.
    if not isinstance(value, str) or not 1 <= len(value.split("|")) <= 2:
        raise ProjectionError("Source generation is missing or malformed")
    for part in value.split("|"):
        _timestamp(part, _GENERATION_PART)
    return value  # Never append a timezone to naive City metadata.


def build_projection(receipt):
    """Return only approved aggregate fields; caller supplies a verified receipt.

    utcEnded must explicitly mean UTC, not local time relabelled by this builder.
    Extra input fields are ignored, never merged into the output.
    """
    receipt = _object(receipt)
    if receipt.get("status") != STATUS:
        raise ProjectionError("Complete stable collision accounting is required")
    checked = _timestamp(receipt.get("utcEnded"), _UTC)
    per_source = _object(receipt.get("perSource"))
    if set(per_source) != set(SOURCE_URLS):
        raise ProjectionError("Exactly the two qualified collections are required")
    sources = []
    for collection, source_url in SOURCE_URLS.items():
        source = _object(per_source[collection])
        generation = _generation(_object(source.get("generation")).get("marker"))
        rows = _count(source.get("rows"))
        inside = _count(_object(source.get("counts")).get("inside_coverage"))
        disposition = _object(source.get("reconciledDisposition"))
        noncolliding = _count(disposition.get("insideNonCollidingRows"))
        collision = _count(disposition.get("insideCollisionRowsQuarantine"))
        invalid = _count(disposition.get("insideInvalidIdentityRowsQuarantine"))
        if rows == 0 or inside > rows or inside != noncolliding + collision + invalid:
            raise ProjectionError("In-footprint disposition does not reconcile with source rows")
        scope = (
            "Active collection only. " if collection == "active" else
            "Cleared collection since 2017 only; legacy 2000–2016 is excluded. "
        )
        sources.append({
            "collection": collection,
            "source_url": source_url,
            "source_generation_as_supplied": generation,
            "checked_at_utc": checked,
            "in_footprint_noncolliding_row_count": noncolliding,
            "in_footprint_quarantined_row_count": collision + invalid,
            "coverage_note": scope + (
                "Counts are source rows, not unique permits. Quarantined rows include "
                "candidate-identity collisions and invalid identities. Rows without a verified in-footprint address match are excluded. These counts do not "
                "establish construction activity or completion, or identity across generations. "
                "Source generation is retained as supplied; timezone-unspecified metadata is "
                "not UTC. Checked time is the receipt check time, not a source update time."
            ),
        })
    return {
        "schema_version": 1,
        "footprint": {
            "ward_numbers": [20, 21, 22, 23, 24, 25],
            "ward_boundary_source_url": "https://open.toronto.ca/dataset/city-wards/",
            "neighbourhood_boundary_source_url": "https://open.toronto.ca/dataset/neighbourhoods/",
            "method": ("Verified address-point match within Toronto wards 20–25 and "
                       "qualifying Scarborough neighbourhood polygons."),
        },
        "sources": sources,
        "licence_url": "https://open.toronto.ca/open-data-licence/",
        "attribution": "Contains information licensed under the Open Government Licence – Toronto.",
    }
