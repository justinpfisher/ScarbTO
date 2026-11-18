import hashlib
import unittest
from datetime import date

from scripts import build_weekly_brief as brief


PAYLOAD = {
    "period_start": "2026-11-09",
    "period_end": "2026-11-15",
    "events": [{
        "id": "event-1",
        "kind": "status_changed",
        "establishment_id": "123",
        "name": "Fixture Cafe",
        "neighbourhood": "West Rouge",
        "inspection_date": "2026-11-10",
        "detected_at": "2026-11-12T15:00:00+00:00",
        "status": "Pass",
        "previous_status": "Conditional",
    }],
}
RECORD = {
    "id": "dinesafe-weekly-2026-11-09",
    "revision": 1,
    "generated_at": "2026-11-16T00:00:00+00:00",
    "revised_at": None,
    "correction_explanation": None,
}


class BrandWeeklyRenderTests(unittest.TestCase):
    def test_unversioned_archived_render_remains_byte_identical(self):
        page = brief._render_edition(PAYLOAD, RECORD)
        self.assertEqual(
            hashlib.sha256(page).hexdigest(),
            "4e723a86f779970ee119856269b5175c9a87d168648c0b70ad73a4f993fc24f4",
        )
        self.assertNotIn(b"/assets/brand/", page)

    def test_new_render_version_uses_connected_brand_and_mobile_mark(self):
        page = brief._render_edition(PAYLOAD, {**RECORD, "render_version": 2}).decode("utf-8")
        self.assertIn('src="/assets/brand/scarbto-connected.svg"', page)
        self.assertIn('srcset="/assets/brand/scarbto-mark.svg"', page)
        self.assertIn('aria-label="Scarb.TO home"', page)
        self.assertIn('alt=""', page)
        self.assertIn("Scarborough. I looked into it.", page)
        self.assertIn("#0A3D2A", page)
        self.assertIn("#F8F5EA", page)

    def test_linked_mosaic_is_distinct_from_existing_mosaic(self):
        mosaic = brief._render_edition(PAYLOAD, {**RECORD, "render_version": 2})
        linked = brief._render_edition(PAYLOAD, {**RECORD, "render_version": 3})
        self.assertIn(b"scarbto-connected.svg", mosaic)
        self.assertIn(b"scarbto-connected.svg", linked)
        self.assertNotIn(b"#establishment/123", mosaic)
        self.assertIn(b"#establishment/123", linked)
        self.assertNotIn(b'href="/west-rouge/"', mosaic)
        self.assertIn(b'href="/west-rouge/"', linked)
        for version in (1, 2, 3):
            revised = brief._correction_record(
                {**RECORD, "render_version": version},
                {"revision": 2, "explanation": "Dated correction."},
                generated_at="2026-11-17T00:00:00+00:00",
                content_hash="a" * 64,
                event_count=1,
            )
            self.assertEqual(revised["render_version"], version)

    def test_correction_preserves_brand_render_version(self):
        revised = brief._correction_record(
            {**RECORD, "render_version": 2},
            {"revision": 2, "explanation": "Clarified the source wording."},
            generated_at="2026-11-17T00:00:00+00:00",
            content_hash="a" * 64,
            event_count=1,
        )
        self.assertEqual(revised["render_version"], 2)

    def test_voice_render_is_future_only_and_preserves_source_facts(self):
        old = brief._render_edition(PAYLOAD, {**RECORD, "render_version": 3})
        current = brief._render_edition(PAYLOAD, {**RECORD, "render_version": 4}).decode("utf-8")
        self.assertNotEqual(old, current.encode("utf-8"))
        for text in ('Fixture Cafe', 'DineSafe result when added: Pass.', 'Previous status: Conditional.', '2026-11-10', '2026-11-12T15:00:00+00:00', '#establishment/123', 'href="/west-rouge/"', 'AI-assisted', 'class="brand-name">Scarb.TO'):
            self.assertIn(text, current)
        self.assertEqual(brief._render_edition(PAYLOAD, {**RECORD, "render_version": 3}), old)

    def test_unknown_render_version_fails_closed(self):
        with self.assertRaisesRegex(brief.BriefError, "Unsupported weekly-brief render version"):
            brief._render_edition(PAYLOAD, {**RECORD, "render_version": 5})
        edition = {
            **RECORD,
            "period_start": "2026-11-09",
            "period_end": "2026-11-15",
            "path": "briefs/2026-11-09/",
            "content_sha256": "a" * 64,
            "html_sha256": "b" * 64,
            "render_version": 5,
        }
        with self.assertRaisesRegex(brief.BriefError, "Unsupported weekly-brief render version"):
            brief._validate_manifest({"editions": [edition]})

    def test_weekly_index_uses_current_brand_assets(self):
        page = brief._render_index(
            {"editions": []},
            date(2026, 11, 9),
            date(2026, 11, 15),
            False,
        ).decode("utf-8")
        self.assertIn('src="/assets/brand/scarbto-connected.svg"', page)
        self.assertIn('srcset="/assets/brand/scarbto-mark.svg"', page)
        self.assertIn("Scarborough. I looked into it.", page)


if __name__ == "__main__":
    unittest.main()
