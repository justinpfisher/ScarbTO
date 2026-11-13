import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.build_rss import SOURCE_URL
from scripts.build_weekly_brief import BriefError, build_weekly_brief, complete_week
from scripts import build_weekly_brief as brief_module


def event(event_id, detected_at, *, name="Cafe <Kitchen>", status="Pass", kind="status_changed", neighbourhood="West Rouge", establishment_id="entity-123"):
    return {
        "id": event_id * 20,
        "feed": "dinesafe",
        "kind": kind,
        "establishment_id": establishment_id,
        "name": name,
        "address": "PRIVATE ADDRESS MUST NOT BE RENDERED",
        "neighbourhood": neighbourhood,
        "inspection_date": "2026-11-06",
        "detected_at": detected_at,
        "status": status,
        "previous_status": "Conditional" if kind == "status_changed" else None,
        "latitude": 43.8,
        "longitude": -79.2,
        "source_url": SOURCE_URL,
    }


def write_archive(history: Path, events: list[dict]) -> None:
    write_month(history, "2026-11", events)


def write_month(history: Path, month: str, events: list[dict]) -> None:
    history.mkdir(parents=True, exist_ok=True)
    archive = {"schema_version": 1, "month": month, "events": events}
    (history / f"{month}.json").write_text(json.dumps(archive), encoding="utf-8")


class WeeklyBriefTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.history = self.root / "history"
        self.output = self.root / "docs" / "briefs"
        self.corrections = self.root / "corrections.json"
        self.as_of = datetime(2026, 11, 9, 15, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def test_selects_last_complete_monday_sunday_in_toronto_time(self):
        start, end = complete_week(self.as_of)
        self.assertEqual(start.isoformat(), "2026-11-02")
        self.assertEqual(end.isoformat(), "2026-11-08")

        # Sunday UTC can still be Sunday local; Monday UTC may be Sunday local.
        start, end = complete_week(datetime(2026, 11, 9, 1, 30, tzinfo=timezone.utc))
        self.assertEqual((start.isoformat(), end.isoformat()), ("2026-10-26", "2026-11-01"))

    def test_builds_only_events_first_observed_in_completed_toronto_week(self):
        write_archive(self.history, [
            event("a", "2026-11-03T10:00:00+00:00", kind="first_seen"),
            event("b", "2026-11-09T01:30:00+00:00", name="Sunday UTC, Sunday Toronto"),
            event("c", "2026-11-09T05:00:00+00:00", name="Monday Toronto, excluded"),
        ])
        count = build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        self.assertEqual(count, 2)
        edition = self.output / "2026-11-02" / "index.html"
        page = edition.read_text(encoding="utf-8")
        self.assertIn("2026-11-02", page)
        self.assertIn("Cafe &lt;Kitchen&gt;", page)
        self.assertIn("Sunday UTC, Sunday Toronto", page)
        self.assertNotIn("Monday Toronto, excluded", page)
        self.assertNotIn("PRIVATE ADDRESS", page)
        self.assertNotIn("latitude", page)
        self.assertNotIn("longitude", page)
        self.assertIn("neighbourhood matched by Scarb.TO", page)
        self.assertIn("not labels supplied by DineSafe", page)
        self.assertIn("Inaccurate source coordinates can put a place in the wrong neighbourhood", page)
        self.assertNotIn("neighbourhood names in the City records", page)
        self.assertIn("Open Government Licence", page)
        self.assertIn("Inspection date: <time datetime=\"2026-11-06\">Friday, November 6, 2026</time>", page)
        self.assertIn('datetime="2026-11-09T01:30:00+00:00">Sunday, November 8, 2026</time>', page)
        self.assertIn("Exact recording time", page)
        self.assertIn("not the inspection time", page)
        self.assertIn("Explore the week's patterns", page)
        manifest = json.loads((self.output / "editions.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["editions"][0]["event_count"], 2)

    def test_subject_links_encode_ids_escape_names_and_use_canonical_area_routes(self):
        write_archive(self.history, [
            event(
                "a",
                "2026-11-03T10:00:00+00:00",
                name="Cafe <Kitchen> & Tea",
                establishment_id="entity /<one>",
            )
        ])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        page = (self.output / "2026-11-02" / "index.html").read_text(encoding="utf-8")

        self.assertIn(
            'href="https://www.toronto.ca/community-people/health-wellness-care/'
            'health-programs-advice/food-safety/dinesafe/#establishment/entity%20%2F%3Cone%3E"',
            page,
        )
        self.assertIn('href="/west-rouge/">West Rouge</a>', page)
        self.assertIn("Cafe &lt;Kitchen&gt; &amp; Tea", page)
        self.assertNotIn("entity /<one>", page)
        self.assertIn("may contain newer information than the inspection date shown here", page)
        self.assertIn(SOURCE_URL, page)

    def test_missing_subject_id_renders_name_without_a_misleading_record_link(self):
        payload = {
            "period_start": "2026-11-02",
            "period_end": "2026-11-08",
            "events": [{
                "id": "a" * 20,
                "kind": "first_seen",
                "name": "Cafe <Kitchen>",
                "neighbourhood": "West Rouge",
                "inspection_date": "2026-11-06",
                "detected_at": "2026-11-07T10:00:00+00:00",
                "status": "Pass",
                "previous_status": None,
            }],
        }
        record = {
            "id": "dinesafe-weekly-2026-11-02",
            "render_version": 2,
            "revision": 1,
            "generated_at": self.as_of.isoformat(),
            "revised_at": None,
            "correction_explanation": None,
        }
        page = brief_module._render_edition(payload, record).decode("utf-8")

        self.assertIn("<strong>Cafe &lt;Kitchen&gt;: Added to Scarb.TO</strong>", page)
        self.assertNotIn("#establishment/", page)
        self.assertIn('href="/west-rouge/">West Rouge</a>', page)

    def test_new_week_does_not_rewrite_an_archived_brief_or_its_hash(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        old_path = self.output / "2026-11-02" / "index.html"
        old_bytes = old_path.read_bytes()
        before = json.loads((self.output / "editions.json").read_text(encoding="utf-8"))["editions"]
        old_record = next(item for item in before if item["period_start"] == "2026-11-02")

        write_archive(self.history, [
            event("a", "2026-11-03T10:00:00+00:00"),
            event("b", "2026-11-10T10:00:00+00:00", name="New week cafe", establishment_id="entity-456"),
        ])
        build_weekly_brief(
            self.history,
            self.output,
            self.corrections,
            as_of=datetime(2026, 11, 16, 15, tzinfo=timezone.utc),
        )
        after = json.loads((self.output / "editions.json").read_text(encoding="utf-8"))["editions"]
        archived = next(item for item in after if item["period_start"] == "2026-11-02")

        self.assertEqual(old_path.read_bytes(), old_bytes)
        self.assertEqual(archived["html_sha256"], old_record["html_sha256"])
        self.assertEqual(archived["revision"], old_record["revision"])

    def test_future_links_preserve_retained_revision_four_and_legacy_bytes(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        render = brief_module._render_edition

        def render_legacy(payload, record):
            legacy_record = dict(record)
            legacy_record.pop("render_version", None)
            return render(payload, legacy_record)

        with patch.object(brief_module, "_render_edition", side_effect=render_legacy):
            build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)

        manifest_path = self.output / "editions.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        archived = manifest["editions"][0]
        archived.pop("render_version")
        archived.update({
            "revision": 4,
            "revised_at": "2026-11-12T22:12:21.649297+00:00",
            "correction_explanation": (
                "Corrected the neighbourhood attribution: Scarb.TO matches source "
                "coordinates to City neighbourhood boundaries; DineSafe does not "
                "supply these neighbourhood labels. Source coordinate errors can "
                "affect the match. The archived records, reporting period and "
                "original preparation time are unchanged."
            ),
        })
        old_page = self.output / "2026-11-02" / "index.html"
        start, end = complete_week(self.as_of)
        events = brief_module.load_events(self.history)
        payload = brief_module._content_payload(start, end, brief_module._week_events(events, start, end))
        legacy_page_bytes = brief_module._render_edition(payload, archived)
        old_page.write_bytes(legacy_page_bytes)
        archived["html_sha256"] = brief_module._sha256(legacy_page_bytes)
        manifest_path.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        (self.output / "index.html").write_bytes(brief_module._render_index(manifest, start, end, True))
        correction_v4 = {
            "schema_version": 1,
            "corrections": {
                archived["id"]: {
                    "revision": 4,
                    "explanation": archived["correction_explanation"],
                }
            },
        }
        self.corrections.write_text(json.dumps(correction_v4), encoding="utf-8")
        legacy_manifest_bytes = manifest_path.read_bytes()
        legacy_index_bytes = (self.output / "index.html").read_bytes()
        legacy_page_bytes = old_page.read_bytes()
        source_archive = self.history / "2026-11.json"
        original_source_bytes = source_archive.read_bytes()
        original_source_fact = json.loads(original_source_bytes)["events"][0]
        original_content_hash = archived["content_sha256"]
        original_html_hash = archived["html_sha256"]
        original_generated_at = archived["generated_at"]
        original_period = (archived["period_start"], archived["period_end"])
        original_event_count = archived["event_count"]

        # A same-period rerun keeps the historical bytes and the retained
        # revision-4 correction exactly as published.
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        self.assertEqual(manifest_path.read_bytes(), legacy_manifest_bytes)
        self.assertEqual((self.output / "index.html").read_bytes(), legacy_index_bytes)
        self.assertEqual(old_page.read_bytes(), legacy_page_bytes)
        self.assertEqual(source_archive.read_bytes(), original_source_bytes)

        write_archive(self.history, [
            event("a", "2026-11-03T10:00:00+00:00"),
            event("b", "2026-11-10T10:00:00+00:00", name="New week cafe", establishment_id="entity-456"),
        ])
        rollover_source_bytes = source_archive.read_bytes()
        next_week = datetime(2026, 11, 16, 15, tzinfo=timezone.utc)
        build_weekly_brief(self.history, self.output, self.corrections, as_of=next_week)
        revised_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rolled_old = next(item for item in revised_manifest["editions"] if item["id"] == archived["id"])
        new_record = next(item for item in revised_manifest["editions"] if item["period_start"] == "2026-11-09")
        new_page_path = self.output / "2026-11-09" / "index.html"
        new_page = new_page_path.read_bytes()
        rolled_manifest_bytes = manifest_path.read_bytes()
        rolled_index_bytes = (self.output / "index.html").read_bytes()
        rolled_old_page = old_page.read_bytes()
        self.assertNotIn("render_version", rolled_old)
        self.assertEqual(new_record["render_version"], 2)
        self.assertEqual(rolled_old["revision"], 4)
        self.assertEqual(rolled_old["generated_at"], original_generated_at)
        self.assertEqual(rolled_old["content_sha256"], original_content_hash)
        self.assertEqual(rolled_old["html_sha256"], original_html_hash)
        self.assertEqual((rolled_old["period_start"], rolled_old["period_end"]), original_period)
        self.assertEqual(rolled_old["event_count"], original_event_count)
        self.assertEqual(old_page.read_bytes(), legacy_page_bytes)
        self.assertEqual(source_archive.read_bytes(), rollover_source_bytes)
        rolled_source_fact = next(
            item for item in json.loads(rollover_source_bytes)["events"] if item["id"] == original_source_fact["id"]
        )
        self.assertEqual(rolled_source_fact, original_source_fact)
        self.assertIn(b"#establishment/entity-456", new_page)
        self.assertIn(b'href="/west-rouge/"', new_page)
        self.assertIn(b"may contain newer information than the inspection date shown here", new_page)

        # Both the legacy edition and the new linked edition remain idempotent.
        build_weekly_brief(self.history, self.output, self.corrections, as_of=next_week)
        self.assertEqual(manifest_path.read_bytes(), rolled_manifest_bytes)
        self.assertEqual((self.output / "index.html").read_bytes(), rolled_index_bytes)
        self.assertEqual(old_page.read_bytes(), rolled_old_page)
        self.assertEqual(new_page_path.read_bytes(), new_page)

        # A real source correction still requires exactly the next revision.
        write_archive(self.history, [
            event("a", "2026-11-03T10:00:00+00:00", status="Closed"),
            event("b", "2026-11-10T10:00:00+00:00", name="New week cafe", establishment_id="entity-456"),
        ])
        corrected_source_bytes = source_archive.read_bytes()
        self.assertNotEqual(corrected_source_bytes, original_source_bytes)
        with self.assertRaisesRegex(BriefError, "Correction revision must increment"):
            build_weekly_brief(self.history, self.output, self.corrections, as_of=next_week)
        self.assertEqual(manifest_path.read_bytes(), rolled_manifest_bytes)
        self.assertEqual((self.output / "index.html").read_bytes(), rolled_index_bytes)
        self.assertEqual(old_page.read_bytes(), rolled_old_page)
        self.assertEqual(new_page_path.read_bytes(), new_page)

        correction_v5 = {
            "schema_version": 1,
            "corrections": {
                archived["id"]: {
                    "revision": 5,
                    "explanation": "Corrected the historic DineSafe status after verifying the preserved source record.",
                }
            },
        }
        self.corrections.write_text(json.dumps(correction_v5), encoding="utf-8")
        build_weekly_brief(self.history, self.output, self.corrections, as_of=next_week)
        corrected_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        revised = next(item for item in corrected_manifest["editions"] if item["id"] == archived["id"])
        self.assertEqual(revised["revision"], 5)
        self.assertNotIn("render_version", revised)
        self.assertEqual((revised["period_start"], revised["period_end"]), original_period)
        self.assertEqual(revised["generated_at"], original_generated_at)
        self.assertNotEqual(revised["content_sha256"], original_content_hash)
        self.assertEqual(revised["event_count"], original_event_count)
        corrected_page = old_page.read_bytes()
        self.assertIn(b"Closed", corrected_page)
        self.assertNotIn(b"#establishment/", corrected_page)
        corrected_manifest_bytes = manifest_path.read_bytes()

        build_weekly_brief(self.history, self.output, self.corrections, as_of=next_week)
        self.assertEqual(manifest_path.read_bytes(), corrected_manifest_bytes)
        self.assertEqual(old_page.read_bytes(), corrected_page)
        self.assertEqual(new_page_path.read_bytes(), new_page)

    def test_unknown_or_malformed_render_versions_fail_manifest_validation(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        manifest = json.loads((self.output / "editions.json").read_text(encoding="utf-8"))
        for version in (0, 3, True, "2", None):
            with self.subTest(version=version):
                candidate = json.loads(json.dumps(manifest))
                candidate["editions"][0]["render_version"] = version
                with self.assertRaisesRegex(BriefError, "Invalid weekly-brief render version"):
                    brief_module._validate_manifest(candidate)

    def test_quiet_week_creates_no_edition_or_fake_item(self):
        write_archive(self.history, [event("a", "2026-11-01T10:00:00+00:00")])
        count = build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        self.assertEqual(count, 0)
        manifest = json.loads((self.output / "editions.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["editions"], [])
        self.assertFalse((self.output / "2026-11-02" / "index.html").exists())
        self.assertIn("I have no DineSafe updates to share", (self.output / "index.html").read_text(encoding="utf-8"))

    def test_rebuild_preserves_original_publication_time_and_page_hash(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        manifest_path = self.output / "editions.json"
        first = json.loads(manifest_path.read_text(encoding="utf-8"))["editions"][0]
        page_before = (self.output / "2026-11-02" / "index.html").read_bytes()
        later = datetime(2026, 11, 12, 15, tzinfo=timezone.utc)
        build_weekly_brief(self.history, self.output, self.corrections, as_of=later)
        second = json.loads(manifest_path.read_text(encoding="utf-8"))["editions"][0]
        self.assertEqual(first["generated_at"], second["generated_at"])
        self.assertEqual(first["html_sha256"], second["html_sha256"])
        self.assertEqual(page_before, (self.output / "2026-11-02" / "index.html").read_bytes())

    def test_changed_committed_history_requires_explained_revision(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00", status="Closed")])
        with self.assertRaisesRegex(BriefError, "explained correction is required"):
            build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)

        correction = {
            "schema_version": 1,
            "corrections": {
                "dinesafe-weekly-2026-11-02": {
                    "revision": 2,
                    "explanation": "Corrected the source event status after validating the archived record.",
                }
            },
        }
        self.corrections.write_text(json.dumps(correction), encoding="utf-8")
        revised_at = datetime(2026, 11, 12, 15, tzinfo=timezone.utc)
        build_weekly_brief(self.history, self.output, self.corrections, as_of=revised_at)
        manifest = json.loads((self.output / "editions.json").read_text(encoding="utf-8"))["editions"][0]
        page = (self.output / "2026-11-02" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(manifest["revision"], 2)
        self.assertEqual(manifest["render_version"], 2)
        self.assertEqual(manifest["generated_at"], self.as_of.isoformat())
        self.assertIn("Correction, revision 2", page)
        self.assertIn("Corrected the source event status", page)

    def test_empty_corrected_edition_rebuild_preserves_revision(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        manifest_path = self.output / "editions.json"
        original = json.loads(manifest_path.read_text(encoding="utf-8"))["editions"][0]

        write_archive(self.history, [])
        correction = {
            "schema_version": 1,
            "corrections": {
                "dinesafe-weekly-2026-11-02": {
                    "revision": 2,
                    "explanation": "Removed the observation after validating the corrected source archive.",
                }
            },
        }
        self.corrections.write_text(json.dumps(correction), encoding="utf-8")
        revised_at = datetime(2026, 11, 12, 15, tzinfo=timezone.utc)
        self.assertEqual(build_weekly_brief(self.history, self.output, self.corrections, as_of=revised_at), 0)
        revised = json.loads(manifest_path.read_text(encoding="utf-8"))["editions"][0]
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["event_count"], 0)
        self.assertEqual(revised["generated_at"], original["generated_at"])

        # The correction is already applied; subsequent refreshes must be idempotent.
        self.assertEqual(build_weekly_brief(self.history, self.output, self.corrections, as_of=revised_at), 0)
        repeated = json.loads(manifest_path.read_text(encoding="utf-8"))["editions"][0]
        self.assertEqual(repeated["revision"], 2)
        self.assertEqual(repeated["html_sha256"], revised["html_sha256"])

    def test_tampered_published_page_fails_closed(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        page = self.output / "2026-11-02" / "index.html"
        page.write_text(page.read_text(encoding="utf-8") + "<!-- edit -->", encoding="utf-8")
        with self.assertRaisesRegex(BriefError, "differs from its registry hash"):
            build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)

    def test_older_edition_is_verified_without_a_correction_entry(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
                build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
                page = self.output / "2026-11-02" / "index.html"
                original = page.read_bytes()
                manifest_path = self.output / "editions.json"
                manifest = manifest_path.read_bytes()
                if missing:
                    page.unlink()
                else:
                    page.write_bytes(original + b"<!-- changed archived status -->")
                later = datetime(2026, 11, 16, 15, tzinfo=timezone.utc)
                with self.assertRaisesRegex(BriefError, "differs from its registry hash"):
                    build_weekly_brief(self.history, self.output, self.corrections, as_of=later)
                self.assertEqual(manifest_path.read_bytes(), manifest)
                self.assertFalse((self.output / "2026-11-09" / "index.html").exists())
                page.write_bytes(original)
    def test_old_edition_can_be_corrected_with_explanation_and_original_date_retained(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        manifest_path = self.output / "editions.json"
        original = json.loads(manifest_path.read_text(encoding="utf-8"))["editions"][0]
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00", status="Closed")])
        write_month(self.history, "2026-12", [event("b", "2026-12-02T10:00:00+00:00", kind="new_inspection")])
        correction = {
            "schema_version": 1,
            "corrections": {
                "dinesafe-weekly-2026-11-02": {
                    "revision": 2,
                    "explanation": "Corrected the archived event after validating the source record.",
                }
            },
        }
        self.corrections.write_text(json.dumps(correction), encoding="utf-8")
        december = datetime(2026, 12, 7, 15, tzinfo=timezone.utc)
        self.assertEqual(build_weekly_brief(self.history, self.output, self.corrections, as_of=december), 1)
        editions = json.loads(manifest_path.read_text(encoding="utf-8"))["editions"]
        updated = next(item for item in editions if item["id"] == original["id"])
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["generated_at"], original["generated_at"])
        old_page = (self.output / "2026-11-02" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Corrected the archived event", old_page)
        # The applied correction entry remains in the control file and is idempotent.
        self.assertEqual(build_weekly_brief(self.history, self.output, self.corrections, as_of=december), 1)

    def test_as_of_must_be_timezone_aware(self):
        with self.assertRaisesRegex(BriefError, "must include a timezone"):
            complete_week(datetime(2026, 11, 9))

    def test_copy_only_revision_current_and_older_preserves_evidence_and_is_idempotent(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        manifest_path = self.output / "editions.json"
        page_path = self.output / "2026-11-02" / "index.html"
        original_manifest = manifest_path.read_bytes()
        original_page = page_path.read_bytes()
        original = json.loads(original_manifest)["editions"][0]
        render = brief_module._render_edition
        def reworded(payload, record):
            return render(payload, record).replace(b"Explore the updates</h2>", b"This week's updates</h2>")
        with patch.object(brief_module, "_render_edition", side_effect=reworded):
            with self.assertRaisesRegex(BriefError, "explained correction is required"):
                build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
            self.assertEqual(page_path.read_bytes(), original_page)
            self.assertEqual(manifest_path.read_bytes(), original_manifest)
            # An older edition without an explicit correction remains byte-for-byte archived.
            later = datetime(2026, 11, 16, 15, tzinfo=timezone.utc)
            build_weekly_brief(self.history, self.output, self.corrections, as_of=later)
            self.assertEqual(page_path.read_bytes(), original_page)
            for reference_time in (self.as_of, later):
                with self.subTest(reference_time=reference_time):
                    manifest_path.write_bytes(original_manifest)
                    page_path.write_bytes(original_page)
                    self.corrections.write_text(json.dumps({"schema_version": 1, "corrections": {
                        original["id"]: {"revision": 2, "explanation": "Clarified the wording; source results are unchanged."}
                    }}), encoding="utf-8")
                    build_weekly_brief(self.history, self.output, self.corrections, as_of=reference_time)
                    revised = json.loads(manifest_path.read_bytes())["editions"][0]
                    self.assertEqual(revised["revision"], 2)
                    for field in ("id", "period_start", "period_end", "generated_at", "event_count", "content_sha256"):
                        self.assertEqual(revised[field], original[field], field)
                    self.assertNotEqual(revised["html_sha256"], original["html_sha256"])
                    revised_page = page_path.read_bytes()
                    self.assertIn(b'event-aaaaaaaaaaaaaaaaaaaa', revised_page)
                    self.assertIn(b'2026-11-06', revised_page)
                    self.assertIn(b'Correction, revision 2', revised_page)
                    build_weekly_brief(self.history, self.output, self.corrections, as_of=reference_time)
                    self.assertEqual(page_path.read_bytes(), revised_page)
                    self.assertEqual(json.loads(manifest_path.read_bytes())["editions"][0], revised)

    def test_copy_change_cannot_reuse_applied_revision_or_omit_explanation(self):
        write_archive(self.history, [event("a", "2026-11-03T10:00:00+00:00")])
        build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
        page_path = self.output / "2026-11-02" / "index.html"
        original = page_path.read_bytes()
        render = brief_module._render_edition
        with patch.object(brief_module, "_render_edition", side_effect=lambda payload, record: render(payload, record) + b"<!-- editorial revision -->"):
            for correction in ({"revision": 1, "explanation": "Reused revision"}, {"revision": 2, "explanation": " "}):
                self.corrections.write_text(json.dumps({"schema_version": 1, "corrections": {
                    "dinesafe-weekly-2026-11-02": correction
                }}), encoding="utf-8")
                with self.assertRaises(BriefError):
                    build_weekly_brief(self.history, self.output, self.corrections, as_of=self.as_of)
                self.assertEqual(page_path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
