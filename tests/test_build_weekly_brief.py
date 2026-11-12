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


def event(event_id, detected_at, *, name="Cafe <Kitchen>", status="Pass", kind="status_changed", neighbourhood="West Rouge"):
    return {
        "id": event_id * 20,
        "feed": "dinesafe",
        "kind": kind,
        "establishment_id": "entity-123",
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
        self.assertIn("neighbourhood named in the City record", page)
        self.assertIn("Open Government Licence", page)
        self.assertIn("Inspection date: <time datetime=\"2026-11-06\">Friday, November 6, 2026</time>", page)
        self.assertIn('datetime="2026-11-09T01:30:00+00:00">Sunday, November 8, 2026</time>', page)
        self.assertIn("Exact recording time", page)
        self.assertIn("not the inspection time", page)
        self.assertIn("Explore the week's patterns", page)
        manifest = json.loads((self.output / "editions.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["editions"][0]["event_count"], 2)

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
