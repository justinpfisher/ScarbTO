import unittest
from pathlib import Path
from scripts.check_scarb_voice_python import check_source_gateway, inspect_source, source_inventory


class VoiceSourceTests(unittest.TestCase):
    def test_current_producers_match_reviewed_contracts(self):
        self.assertGreater(check_source_gateway(), 0)

    def test_rss_weekly_and_community_reject_unregistered_copy(self):
        root = Path(__file__).resolve().parents[1]
        for filename in ("build_rss.py", "build_weekly_brief.py", "build_community_publishing.py", "scarb_voice.py"):
            source = (root / "scripts" / filename).read_text(encoding="utf-8")
            approved = source_inventory(source)
            for addition in ('\nunregistered = "Unverified claim"\n', '\nchannel.text = "Unverified claim"\n', '\npage = f"A new claim about {source_fact}"\n'):
                with self.subTest(filename=filename, addition=addition):
                    with self.assertRaisesRegex(ValueError, "Unreviewed"):
                        inspect_source(filename, source + addition, approved)

    def test_rss_label_transformation_is_part_of_producer_contract(self):
        source = (Path(__file__).resolve().parents[1] / "scripts/build_rss.py").read_text(encoding="utf-8")
        old = 'label = EVENT_KINDS[event["kind"]]'
        self.assertIn(old, source)
        changed = source.replace(old, old + "[::-1]")
        from datetime import datetime, timezone
        from xml.etree import ElementTree as ET
        from tests.test_build_rss import make_event
        event = make_event(detected_at=datetime(2026, 11, 2, tzinfo=timezone.utc))
        def title(code):
            scope = {"__file__": str(Path(__file__).resolve().parents[1] / "scripts/build_rss.py"), "__name__": "voice_mutation_fixture"}
            exec(compile(code, "voice_mutation_fixture", "exec"), scope)
            return ET.fromstring(scope["build_feed"]([event], built_at=datetime(2026, 11, 3, tzinfo=timezone.utc))).findtext("channel/item/title")
        self.assertNotEqual(title(source), title(changed))
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            inspect_source("build_rss.py", changed, source_inventory(source))

    def test_source_field_substitution_cannot_hide_inside_same_fstring(self):
        source = 'text = f"Inspection date: {event[\'inspection_date\']}"'
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            inspect_source("fixture", source.replace("inspection_date", "detected_at"), source_inventory(source))


if __name__ == "__main__":
    unittest.main()
