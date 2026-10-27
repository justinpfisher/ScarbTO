"""Offline adapter for the Toronto operational beach-status API.

No HTTP transport or public exporter is included. Inputs are fixtures or
prevalidated API envelopes. Public output remains disabled pending source-rights
and privacy review.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo


TORONTO = ZoneInfo("America/Toronto")
OFFICIAL_VIEW_URL = "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/beach-water-quality/"
CATALOGUE_LICENCE_URL = "https://open.toronto.ca/open-data-licence/"
TERMS_URL = "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/swimsafe-terms-of-use/"
PUBLICATION_ENABLED = False
STATUS_LABELS = {
    "SAFE": "safe",
    "UNSAFE": "caution",
    "NO_DATA": "unavailable",
}
DEFAULT_CONTROL_FRESHNESS_LIMIT = timedelta(hours=24)


class BeachContractError(ValueError):
    """Input does not satisfy the reviewed operational-source contract."""


class BeachExportDisabled(RuntimeError):
    """Public beach snapshots are held pending source-rights validation."""


def _aware_utc(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise BeachContractError(f"{label} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _season(value: Any) -> bool | None:
    if type(value) is bool and value:
        return True
    if type(value) is bool and not value:
        return False
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def _maintenance(value: Any) -> bool | None:
    if type(value) is bool and not value:
        return False
    if type(value) is bool and value:
        return True
    if value == "N":
        return False
    if value == "Y":
        return True
    return None


def _sample_date(value: Any) -> date:
    if not isinstance(value, str):
        raise BeachContractError("CollectionDate must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise BeachContractError("CollectionDate must be an ISO date string") from exc
    if parsed.isoformat() != value:
        raise BeachContractError("CollectionDate must not include a time or offset")
    return parsed


def _parse_source_date(value: Any) -> datetime | None:
    """Parse only an explicitly offset source timestamp; keep raw text separately."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise BeachContractError("lastUpdate must be a non-empty string or null")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise BeachContractError("lastUpdate is not a valid ISO timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _result_for_beach(
    envelopes: list[dict[str, Any]] | None, beach_id: int
) -> tuple[date | None, dict[str, Any] | None]:
    if envelopes is None:
        return None, None
    if not isinstance(envelopes, list):
        raise BeachContractError("results must be an array or null")
    parsed: list[tuple[date, dict[str, Any] | None]] = []
    for envelope in envelopes:
        if not isinstance(envelope, dict):
            raise BeachContractError("Each result envelope must be an object")
        collection_date = _sample_date(envelope.get("CollectionDate"))
        rows = envelope.get("data")
        if rows is None:
            parsed.append((collection_date, None))
            continue
        if not isinstance(rows, list):
            raise BeachContractError("Result data must be an array or null")
        matches = []
        for row in rows:
            if not isinstance(row, dict):
                raise BeachContractError("Each result row must be an object")
            row_id = row.get("beachId")
            if type(row_id) is int and row_id == beach_id:
                matches.append(row)
        if len(matches) > 1:
            raise BeachContractError("Duplicate result rows for beach and collection date")
        parsed.append((collection_date, matches[0] if matches else None))
    if not parsed:
        return None, None
    latest = max(day for day, _ in parsed)
    latest_values = [row for day, row in parsed if day == latest]
    if len(latest_values) != 1:
        raise BeachContractError("Duplicate result envelopes for latest collection date")
    return latest, latest_values[0]


def build_status_card(
    *,
    beach_id: int,
    beach_name: str,
    in_season: Any,
    last_update_raw: Any,
    result_envelopes: list[dict[str, Any]] | None,
    now: datetime,
    sample_freshness_limit: timedelta | None,
    maintenance_enabled: Any = None,
    retrieved_at: datetime | None = None,
    control_retrieved_at: dict[str, datetime | None] | None = None,
    control_freshness_limit: timedelta | None = DEFAULT_CONTROL_FRESHNESS_LIMIT,
    access_closure: str | None = None,
) -> dict[str, Any]:
    """Normalize operational controls/results; never infer safety from E. coli.

    Freshness uses the sample's Toronto calendar date, not the timezone-less
    lastUpdate text. The caller must explicitly supply a proposed sample-age
    limit. That threshold is an application policy, not a City guarantee.
    Current status also requires all control/result responses to have been
    retrieved within the proposed control-freshness limit.
    """
    if type(beach_id) is not int or beach_id < 1:
        raise BeachContractError("beach_id must be a positive integer")
    if not isinstance(beach_name, str) or not beach_name.strip():
        raise BeachContractError("beach_name is required")
    now_utc = _aware_utc(now, "now")
    if last_update_raw is not None and not isinstance(last_update_raw, str):
        raise BeachContractError("lastUpdate must be a string or null")
    if sample_freshness_limit is not None and sample_freshness_limit <= timedelta(0):
        raise BeachContractError("sample_freshness_limit must be positive")
    if control_freshness_limit is not None and control_freshness_limit <= timedelta(0):
        raise BeachContractError("control_freshness_limit must be positive")
    season = _season(in_season)
    maintenance = _maintenance(maintenance_enabled)
    source_updated = _parse_source_date(last_update_raw)
    latest_date, result = _result_for_beach(result_envelopes, beach_id)
    if retrieved_at is not None:
        retrieved_at_utc = _aware_utc(retrieved_at, "retrieved_at")
        fetched_at = retrieved_at_utc.isoformat().replace("+00:00", "Z")
    else:
        # Evaluation may happen long after retrieval (for example, on a cached
        # snapshot). Never move the source fetch time forward by evaluating it.
        fetched_at = None
    control_retrieved_at = control_retrieved_at or {}
    control_timestamps = {}
    control_age_ok: dict[str, bool] = {}
    for name in ("season", "last_update", "maintenance", "results"):
        value = control_retrieved_at.get(name)
        parsed_time = _aware_utc(value, f"{name} retrieval time") if value is not None else None
        age = now_utc - parsed_time if parsed_time is not None else None
        if age is not None and age < timedelta(0):
            raise BeachContractError(f"{name} retrieval time cannot be in the future")
        control_age_ok[name] = (
            parsed_time is not None
            and (control_freshness_limit is None or age <= control_freshness_limit)
        )
        control_timestamps[f"{name}_fetched_at_utc"] = (
            parsed_time.isoformat().replace("+00:00", "Z") if parsed_time is not None else None
        )

    card: dict[str, Any] = {
        "beach_id": beach_id,
        "beach_name": beach_name.strip(),
        "sample_date": latest_date.isoformat() if latest_date else None,
        "source_update_raw": last_update_raw if isinstance(last_update_raw, str) else None,
        "source_updated_at_utc": source_updated.isoformat().replace("+00:00", "Z") if source_updated else None,
        "fetched_at_utc": fetched_at,
        **control_timestamps,
        "raw_status_flag": result.get("statusFlag") if isinstance(result, dict) else None,
        "raw_status_flag_pre": result.get("statusFlagPre") if isinstance(result, dict) else None,
        "source_view_url": OFFICIAL_VIEW_URL,
        "catalogue_licence_url": CATALOGUE_LICENCE_URL,
        "terms_url": TERMS_URL,
        "rights_status": "catalogue_claims_toronto_open_data_licence_ckan_unspecified",
        "display_state": "unknown",
        "water_quality_status": None,
        "advisory": None,
        "publication_status": "disabled_pending_source_rights_review",
        "control_freshness_limit_hours": (
            control_freshness_limit.total_seconds() / 3600
            if control_freshness_limit is not None else None
        ),
    }

    # Closure is shown only when supplied from a separately verified authority.
    if access_closure is not None:
        if not isinstance(access_closure, str) or not access_closure.strip():
            raise BeachContractError("access_closure must be non-empty text or null")
        card["display_state"] = "access_closed"
        card["advisory"] = access_closure.strip()
        return card
    if not control_age_ok["season"]:
        card["display_state"] = "season_state_stale"
        return card
    if season is False:
        card["display_state"] = "out_of_season"
        return card
    if season is None:
        card["display_state"] = "season_state_unknown"
        return card
    if not control_age_ok["maintenance"]:
        card["display_state"] = "maintenance_state_stale"
        return card
    if maintenance is True:
        card["display_state"] = "maintenance"
        return card
    if maintenance is None:
        card["display_state"] = "maintenance_state_unknown"
        return card
    if not control_age_ok["last_update"] or not control_age_ok["results"]:
        card["display_state"] = "source_controls_stale"
        return card
    if latest_date is None or result is None:
        card["display_state"] = "no_current_result"
        return card
    if sample_freshness_limit is None:
        card["display_state"] = "freshness_unqualified"
        return card
    local_today = now_utc.astimezone(TORONTO).date()
    sample_age = local_today - latest_date
    if sample_age < timedelta(0):
        raise BeachContractError("CollectionDate cannot be in the future")
    if sample_age > sample_freshness_limit:
        card["display_state"] = "stale"
        return card

    preliminary = result.get("statusFlagPre")
    official = result.get("statusFlag")
    chosen = preliminary if preliminary is not None else official
    if not isinstance(chosen, str) or chosen not in STATUS_LABELS:
        card["display_state"] = "status_unrecognized"
        return card
    advisory = result.get("advisory")
    if advisory is not None and not isinstance(advisory, str):
        raise BeachContractError("advisory must be a string or null")

    card["display_state"] = "current"
    card["water_quality_status"] = STATUS_LABELS[chosen]
    card["advisory"] = advisory
    return card


def export_public(*_args: Any, **_kwargs: Any) -> None:
    raise BeachExportDisabled(
        "Public beach export is disabled pending source-rights and privacy review"
    )

