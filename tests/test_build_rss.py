import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from scripts.build_rss import CITY_RECORD_URL_PREFIX, FEED_URL, LICENCE_URL, SOURCE_URL, FeedError, build_feed, load_events, main, write_feed, reader_date


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
            self.assertIn("with the City source so you can dig in too", channel.findtext("description"))
            self.assertIn("added dates show when I first recorded each change", channel.findtext("description"))
            self.assertIn("The City status may have changed since.", channel.findtext("description"))
            self.assertIn("A place newly added here is not necessarily a new business.", channel.findtext("description"))
            self.assertIn("AI-assisted, not first-hand reporting", channel.findtext("description"))
            self.assertIn("Contains information licensed under the Open Government Licence – Toronto.", channel.findtext("description"))
            self.assertIn(LICENCE_URL, channel.findtext("description"))
            self_link = channel.find("{http://www.w3.org/2005/Atom}link")
            self.assertEqual(self_link.attrib["href"], FEED_URL)
            self.assertEqual(self_link.attrib["rel"], "self")
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0].findtext("guid"), "urn:scarbto:dinesafe:" + "1" * 20)
            self.assertEqual(items[0].findtext("pubDate"), "Mon, 02 Nov 2026 10:00:00 +0000")
            self.assertEqual(items[0].findtext("link"), CITY_RECORD_URL_PREFIX + "12345")
            self.assertIn(SOURCE_URL, items[0].findtext("description"))
            self.assertEqual(events[0]["source_url"], SOURCE_URL)
            self.assertIn("Neighbourhood matched by Scarb.TO: West Rouge", items[0].findtext("description"))
            self.assertIn("not a neighbourhood label supplied by DineSafe", items[0].findtext("description"))
            self.assertIn("Inaccurate source coordinates", items[0].findtext("description"))
            self.assertNotIn("Neighbourhood in the City record", items[0].findtext("description"))
            self.assertIn("Added to Scarb.TO: Monday, November 2, 2026", items[0].findtext("description"))
            self.assertIn("Inspection date: Saturday, October 31, 2026", items[0].findtext("description"))
            self.assertNotIn("T10:00:00", items[0].findtext("description"))
            self.assertIn("not the inspection date", items[0].findtext("description"))
            self.assertIn("not a current safety assessment", items[0].findtext("description"))
            self.assertIn("Cafe &amp; &lt;Kitchen&gt;", xml)
            self.assertNotIn("MUST NOT APPEAR", xml)
            self.assertNotIn("43.8", xml)
            self.assertNotIn("-79.2", xml)
            self.assertEqual(FEED_URL, "https://scarb.to/feed.xml")

    def test_record_links_encode_establishment_ids_as_one_url_component(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            write_archive(history, "2026-11", [make_event(establishment_id="A/B &?#42")])
            root = ET.fromstring(build_feed(load_events(history), built_at=datetime(2026, 11, 3, tzinfo=timezone.utc)))
            item = root.find("channel/item")
            self.assertEqual(item.findtext("link"), CITY_RECORD_URL_PREFIX + "A%2FB%20%26%3F%2342")
            self.assertIn(f"City source dataset: {SOURCE_URL}.", item.findtext("description"))
            self.assertEqual(item.findtext("guid"), "urn:scarbto:dinesafe:" + "0" * 20)
            self.assertEqual(item.findtext("pubDate"), "Mon, 02 Nov 2026 10:00:00 +0000")

    def test_reader_dates_use_toronto_day_without_changing_rss_timestamp(self):
        with tempfile.TemporaryDirectory() as temp:
            history = Path(temp)
            write_archive(history, "2026-11", [make_event(detected_at="2026-11-02T01:30:00+00:00")])
            root = ET.fromstring(build_feed(load_events(history), built_at=datetime(2026, 11, 3, tzinfo=timezone.utc)))
            item = root.find("channel/item")
            self.assertIn("Added to Scarb.TO: Sunday, November 1, 2026", item.findtext("description"))
            self.assertEqual(item.findtext("pubDate"), "Mon, 02 Nov 2026 01:30:00 +0000")
            self.assertEqual(item.findtext("guid"), "urn:scarbto:dinesafe:" + "0" * 20)
        self.assertEqual(reader_date(datetime(2026, 11, 10).date()), "Tuesday, November 10, 2026")

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


class PreviousPublicationTests(unittest.TestCase):
    def test_publisher_cli_reuses_only_successful_canonical_public_copy(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            history = root / "history"
            history.mkdir()
            write_archive(history, "2026-11", [make_event()])
            original = build_feed(load_events(history), built_at=datetime(2026, 11, 3, tzinfo=timezone.utc))

            for label, code, http in [("same", 0, b"200"), ("redirect", 0, b"302"),
                                      ("too large", 63, b"200"), ("timeout", None, b"")]:
                with self.subTest(label=label):
                    output = root / f"{label}.xml"

                    def fake_curl(args, *, capture_output, timeout, check):
                        self.assertEqual(args[-1], FEED_URL)
                        self.assertEqual(args[:2], ["curl", "-q"])
                        self.assertNotIn("--location", args)
                        self.assertEqual(args[args.index("--proto") + 1], "=https")
                        self.assertEqual(args[args.index("--max-filesize") + 1], "1048576")
                        self.assertEqual(timeout, 15)
                        destination = Path(args[args.index("--output") + 1])
                        self.assertNotEqual(destination, output)
                        destination.write_bytes(original)
                        if code is None:
                            raise TimeoutExpired(args, timeout)
                        return CompletedProcess(args, code, stdout=http)

                    with patch("scripts.build_rss.subprocess.run", side_effect=fake_curl) as fetch:
                        self.assertEqual(main(["--history-dir", str(history), "--output", str(output), "--reuse-live-date"]), 0)
                        fetch.assert_called_once()
                    self.assertEqual(output.read_bytes() == original, label == "same")
                    self.assertEqual(ET.fromstring(output.read_bytes()).findtext("channel/item/guid"),
                                     ET.fromstring(original).findtext("channel/item/guid"))

    def test_separate_checkout_reuses_only_canonical_prior_date(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            history = root / "history"
            history.mkdir()
            write_archive(history, "2026-11", [make_event()])
            first = root / "published.xml"
            output = root / "fresh" / "feed.xml"
            before = datetime(2026, 11, 3, tzinfo=timezone.utc)
            now = datetime(2026, 11, 5, tzinfo=timezone.utc)
            write_feed(history, first, built_at=before)
            original = first.read_bytes()
            write_feed(history, output, built_at=now, previous_feed=first)
            self.assertEqual(output.read_bytes(), original)
            write_archive(history, "2026-11", [make_event(), make_event("1" * 20, detected_at="2026-11-04T10:00:00+00:00")])
            write_feed(history, output, built_at=now, previous_feed=first)
            before_item = ET.fromstring(original).find("channel/item")
            result = ET.fromstring(output.read_bytes())
            self.assertNotEqual(result.findtext("channel/lastBuildDate"), ET.fromstring(original).findtext("channel/lastBuildDate"))
            retained = next(item for item in result.findall("channel/item") if item.findtext("guid") == before_item.findtext("guid"))
            self.assertEqual(ET.tostring(retained), ET.tostring(before_item))
            self.assertEqual(first.read_bytes(), original)

    def test_optional_prior_input_cannot_block_or_supply_content(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            history = root / "history"
            history.mkdir()
            write_archive(history, "2026-11", [make_event()])
            prior = root / "prior.xml"
            output = root / "fresh" / "feed.xml"
            now = datetime(2026, 11, 5, tzinfo=timezone.utc)
            future = datetime(2026, 11, 6, tzinfo=timezone.utc)
            expected = build_feed(load_events(history), built_at=now)
            future_bytes = build_feed(load_events(history), built_at=future)
            prior_bytes = build_feed(load_events(history), built_at=datetime(2026, 11, 4, tzinfo=timezone.utc))
            for kind, content in [("absent", None), ("broken", b"not xml"), ("overlarge", b"x"*1_048_577),
                                  ("future", future_bytes), ("changed", prior_bytes.replace(b"DineSafe", b"DIFFERENT"))]:
                with self.subTest(kind=kind):
                    if content is not None:
                        prior.write_bytes(content)
                    write_feed(history, output, built_at=now, previous_feed=prior)
                    self.assertEqual(output.read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
