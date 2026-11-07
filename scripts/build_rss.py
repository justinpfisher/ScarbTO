#!/usr/bin/env python3
"""Build a source-linked RSS feed from committed, validated DineSafe history.

The feed contains observed DineSafe events only. It deliberately omits addresses
and coordinates, and keeps source inspection dates distinct from first-observed
times. No network requests or third-party packages are used.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path

FEED_URL = "https://scarb.to/feed.xml"
SITE_URL = "https://scarb.to/"
SOURCE_URL = "https://open.toronto.ca/dataset/dinesafe/"
MAX_ITEMS = 50
EVENT_ID_RE = re.compile(r"^[0-9a-f]{20}$")
EVENT_KINDS = {
    "first_seen": "First observed",
    "status_changed": "DineSafe status changed",
    "new_inspection": "New DineSafe inspection",
}


class FeedError(ValueError):
    """Raised when committed history cannot safely produce a public feed."""


def parse_timestamp(value: object, *, context: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise FeedError(f"Missing timestamp in {context}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeedError(f"Invalid timestamp in {context}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FeedError(f"Timezone missing from timestamp in {context}")
    return parsed.astimezone(timezone.utc)


def required_text(event: dict, key: str, *, limit: int, event_id: str) -> str:
    value = event.get(key)
    if not isinstance(value, str):
        raise FeedError(f"Missing {key} in DineSafe event {event_id}")
    value = " ".join(value.split())
    if not value or len(value) > limit or value.casefold() in {"none", "null", "n/a", "unknown"}:
        raise FeedError(f"Invalid {key} in DineSafe event {event_id}")
    return value


def load_events(history_dir: Path) -> list[dict]:
    paths = sorted(history_dir.glob("*.json"))
    if not history_dir.is_dir() or not paths:
        raise FeedError("Committed activity history is missing")

    events: list[dict] = []
    seen_ids: set[str] = set()
    for path in paths:
        month = path.stem
        try:
            if len(month) != 7 or datetime.strptime(month, "%Y-%m").strftime("%Y-%m") != month:
                raise ValueError("bad month")
        except ValueError as exc:
            raise FeedError(f"Invalid activity archive name: {path.name}") from exc
        try:
            archive = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FeedError(f"Invalid activity archive: {path.name}") from exc
        if not isinstance(archive, dict) or archive.get("schema_version") != 1 or archive.get("month") != month or not isinstance(archive.get("events"), list):
            raise FeedError(f"Invalid activity archive envelope: {path.name}")

        for index, event in enumerate(archive["events"]):
            context = f"{path.name} event {index}"
            if not isinstance(event, dict):
                raise FeedError(f"Invalid event in {context}")
            event_id = event.get("id")
            if not isinstance(event_id, str) or not EVENT_ID_RE.fullmatch(event_id) or event_id in seen_ids:
                raise FeedError(f"Invalid or duplicate event ID in {context}")
            seen_ids.add(event_id)
            observed = parse_timestamp(event.get("detected_at"), context=context)
            if observed.strftime("%Y-%m") != month:
                raise FeedError(f"Event timestamp does not match archive month in {context}")

            # Other feeds stay out of the RSS feed until separately qualified.
            if event.get("feed") != "dinesafe":
                continue
            if event.get("kind") not in EVENT_KINDS:
                raise FeedError(f"Unapproved DineSafe event kind in {context}")
            if event.get("source_url") != SOURCE_URL:
                raise FeedError(f"Unapproved DineSafe source URL in {context}")

            establishment_id = required_text(event, "establishment_id", limit=80, event_id=event_id)
            name = required_text(event, "name", limit=300, event_id=event_id)
            neighbourhood = required_text(event, "neighbourhood", limit=150, event_id=event_id)
            status = required_text(event, "status", limit=100, event_id=event_id)
            inspection_date = event.get("inspection_date")
            if not isinstance(inspection_date, str):
                raise FeedError(f"Missing inspection date in DineSafe event {event_id}")
            try:
                parsed_date = date.fromisoformat(inspection_date)
            except ValueError as exc:
                raise FeedError(f"Invalid inspection date in DineSafe event {event_id}") from exc
            if parsed_date.isoformat() != inspection_date:
                raise FeedError(f"Invalid inspection date in DineSafe event {event_id}")

            previous_status = event.get("previous_status")
            if previous_status is not None:
                if not isinstance(previous_status, str) or not previous_status.strip() or len(previous_status) > 100:
                    raise FeedError(f"Invalid previous status in DineSafe event {event_id}")
                previous_status = " ".join(previous_status.split())
                if previous_status.casefold() in {"none", "null", "n/a", "unknown"}:
                    raise FeedError(f"Invalid previous status in DineSafe event {event_id}")
            if event["kind"] == "status_changed" and (not previous_status or previous_status == status):
                raise FeedError(f"Invalid status-change values in DineSafe event {event_id}")

            events.append({
                "id": event_id,
                "kind": event["kind"],
                "establishment_id": establishment_id,
                "name": name,
                "neighbourhood": neighbourhood,
                "inspection_date": inspection_date,
                "detected_at": observed,
                "status": status,
                "previous_status": previous_status,
                "source_url": SOURCE_URL,
            })
    return sorted(events, key=lambda event: (event["detected_at"], event["id"]), reverse=True)


def build_feed(events: list[dict], *, built_at: datetime) -> bytes:
    if built_at.tzinfo is None or built_at.utcoffset() is None:
        raise FeedError("Feed build time must include a timezone")
    root = ET.Element("rss", {"version": "2.0"})
    atom_ns = "http://www.w3.org/2005/Atom"
    ET.register_namespace("atom", atom_ns)
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "Scarb.TO observed DineSafe changes"
    ET.SubElement(channel, "link").text = SITE_URL
    ET.SubElement(channel, f"{{{atom_ns}}}link", {
        "href": FEED_URL,
        "rel": "self",
        "type": "application/rss+xml",
    })
    ET.SubElement(channel, "description").text = (
        "Source-linked DineSafe changes first observed by Scarb.TO in Scarborough. "
        "Inspection dates are source dates; first-observed dates are Scarb.TO observations. "
        "A source status may have changed since it was observed."
    )
    ET.SubElement(channel, "language").text = "en-CA"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(built_at.astimezone(timezone.utc))

    for event in events[:MAX_ITEMS]:
        item = ET.SubElement(channel, "item")
        label = EVENT_KINDS[event["kind"]]
        ET.SubElement(item, "title").text = f"{label}: {event['name']}"
        ET.SubElement(item, "link").text = event["source_url"]
        guid = ET.SubElement(item, "guid", {"isPermaLink": "false"})
        guid.text = f"urn:scarbto:dinesafe:{event['id']}"
        ET.SubElement(item, "pubDate").text = format_datetime(event["detected_at"])
        details = [f"Neighbourhood: {event['neighbourhood']}."]
        if event["previous_status"]:
            details.append(f"Previous DineSafe status: {event['previous_status']}.")
        details.extend([
            f"DineSafe status at observation: {event['status']}.",
            f"Inspection date: {event['inspection_date']}.",
            f"First observed by Scarb.TO: {event['detected_at'].isoformat()}.",
            f"DineSafe establishment ID: {event['establishment_id']}.",
            "Verify current information at the official Toronto Open Data DineSafe source.",
        ])
        ET.SubElement(item, "description").text = " ".join(details)
        ET.SubElement(item, "category").text = "DineSafe"

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_feed(history_dir: Path, output: Path, *, built_at: datetime | None = None) -> int:
    events = load_events(history_dir)
    xml = build_feed(events, built_at=built_at or datetime.now(timezone.utc))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False) as stream:
            temporary_path = Path(stream.name)
            stream.write(xml)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output)
    except OSError as exc:
        raise FeedError(f"Unable to write RSS feed: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return min(len(events), MAX_ITEMS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--history-dir", type=Path, default=root / "docs" / "data" / "history")
    parser.add_argument("--output", type=Path, default=root / "docs" / "feed.xml")
    args = parser.parse_args(argv)
    try:
        count = write_feed(args.history_dir, args.output)
    except FeedError as exc:
        print(f"RSS NOT BUILT: {exc}", file=sys.stderr)
        return 2
    print(f"RSS built with {count} recent observed DineSafe changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

