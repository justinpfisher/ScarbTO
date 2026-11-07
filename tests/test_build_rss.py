import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_rss import FEED_URL, LICENCE_URL, SOURCE_URL, FeedError, build_feed, load_events, write_feed


def make_event(event_id="0" * 20, *, month="2026-11", detected_at="2026-11-02T10:00:00+00:00", kind="status_changed", feed="dinesafe", **overrides):
    event = {
        "id": event_id,
        "feed": feed,
        "kind": kind,
        "establishment_id": "12345",
        "name": "Cafe & <Kitchen>",
        "address": "MUST NOT APPEAR IN RSS",
        "neighbourhood": "West Rouge",
        "inspection_date": "2026-10-31",
        "detected_at": detected_at,
        "status": "Pass",
        "previous_status": "Conditional" if kind == "status_changed" else None,
        "latitude": 43.8,
        "longitude": -79.2,
        "source_url": SOURCE_URL,
    }
    event.update(overrides)
    return event


def write_archive(directory: Path, month: str, events: list[dict]) -> Path:
    path = directory / f"{month}.json"
    path.write_text(json.dumps({"schema_version": 1, "month": month, "events": events}), encoding="utf-8")
    return path


class BuildRssTests(unittest.TestCase):
    def test_builds_stable_source_linked_feed_without_address_or_coordinates(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp) / "history"
            history.mkdir()
            write_archive(history, "2026-11", [
                make_event("0" * 20, detected_at="2026-11-01T10:00:00+00:00"),
                make_event("1" * 20, detected_at="2026-11-02T10:00:00+00:00", name="Second Place"),
            ])
            events = load_events(history)
            xml = build_feed(events, built_at=datetime(2026, 11, 3, tzinfo=timezone.utc)).decode("utf-8")
            root = ET.fromstring(xml)
            channel = root.find("channel")
            items = channel.findall("item")
            self.assertEqual(root.tag, "rss")
            self.assertEqual(channel.findtext("lastBuildDate"), "Tue, 03 Nov 2026 00:00:00 +0000")
            self.assertIn("Contains information licensed under the Open Government Licence – Toronto.", channel.findtext("description"))
            self.assertIn(LICENCE_URL, channel.findtext("description"))
            self_link = channel.find("{http://www.w3.org/2005/Atom}link")
            self.assertEqual(self_link.attrib["href"], FEED_URL)
            self.assertEqual(self_link.attrib["rel"], "self")
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0].findtext("guid"), "urn:scarbto:dinesafe:" + "1" * 20)
            self.assertEqual(items[0].findtext("pubDate"), "Mon, 02 Nov 2026 10:00:00 +0000")
            self.assertEqual(items[0].findtext("link"), SOURCE_URL)
            self.assertIn("First observed by Scarb.TO: 2026-11-02T10:00:00+00:00", items[0].findtext("description"))
            self.assertIn("Cafe &amp; &lt;Kitchen&gt;", xml)
            self.assertNotIn("MUST NOT APPEAR", xml)
            self.assertNotIn("43.8", xml)
            self.assertNotIn("-79.2", xml)
            self.assertEqual(FEED_URL, "https://scarb.to/feed.xml")

    def test_omits_non_dinesafe_feeds(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            write_archive(history, "2026-11", [
                make_event("0" * 20, feed="police", kind="aggregate"),
            ])
            self.assertEqual(load_events(history), [])

    def test_rejects_duplicate_ids_across_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            write_archive(history, "2026-11", [make_event("0" * 20)])
            write_archive(history, "2026-12", [make_event("0" * 20, detected_at="2026-12-03T10:00:00+00:00")])
            with self.assertRaises(FeedError):
                load_events(history)

    def test_rejects_event_in_wrong_month(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            write_archive(history, "2026-12", [make_event("1" * 20, detected_at="2026-11-03T10:00:00+00:00")])
            with self.assertRaises(FeedError):
                load_events(history)

    def test_rejects_unapproved_source_or_malformed_event(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            write_archive(history, "2026-11", [make_event("0" * 20, source_url="https://example.invalid/record")])
            with self.assertRaises(FeedError):
                load_events(history)

    def test_rejects_missing_feed_name(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            event = make_event("0" * 20)
            del event["feed"]
            write_archive(history, "2026-11", [event])
            with self.assertRaises(FeedError):
                load_events(history)

    def test_rejects_boolean_schema_version(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            (history / "2026-11.json").write_text(
                json.dumps({"schema_version": True, "month": "2026-11", "events": []}),
                encoding="utf-8",
            )
            with self.assertRaises(FeedError):
                load_events(history)

    def test_rejects_xml_illegal_source_text(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            write_archive(history, "2026-11", [make_event("0" * 20, name="Cafe\x01Kitchen")])
            with self.assertRaises(FeedError):
                load_events(history)

    def test_rejects_noncanonical_inspection_date(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            write_archive(history, "2026-11", [make_event("0" * 20, inspection_date="20261031")])
            with self.assertRaises(FeedError):
                load_events(history)

    def test_validation_failure_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            history = root / "history"
            history.mkdir()
            write_archive(history, "2026-11", [make_event("0" * 20, source_url="https://example.invalid/")])
            output = root / "feed.xml"
            output.write_text("last good", encoding="utf-8")
            with self.assertRaises(FeedError):
                write_feed(history, output)
            self.assertEqual(output.read_text(encoding="utf-8"), "last good")

    def test_rejects_missing_history(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FeedError):
                load_events(Path(temp) / "missing")


if __name__ == "__main__":
    unittest.main()

