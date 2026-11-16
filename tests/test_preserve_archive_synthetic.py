import json
import tempfile
import unittest
from pathlib import Path
from scripts import build_weekly_brief as brief

class PreserveArchiveSyntheticTests(unittest.TestCase):
    def test_missing_or_nonfile_index_fails_without_writes(self):
        for directory in (False, True):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as temp:
                output = Path(temp)
                page = output / "2026-11-02/index.html"
                page.parent.mkdir()
                page.write_bytes(b"fictional issued edition")
                manifest = {"schema_version": 1, "editions": [{
                    "id": "dinesafe-weekly-2026-11-02",
                    "period_start": "2026-11-02", "period_end": "2026-11-08",
                    "path": "briefs/2026-11-02/", "revision": 1,
                    "generated_at": "2026-11-09T12:00:00+00:00",
                    "revised_at": None, "correction_explanation": None,
                    "content_sha256": "a"*64,
                    "html_sha256": brief._sha256(page.read_bytes()), "event_count": 1}]}
                (output/"editions.json").write_text(json.dumps(manifest), encoding="utf-8")
                if directory: (output/"index.html").mkdir()
                before = {str(p.relative_to(output)):p.read_bytes() for p in output.rglob("*") if p.is_file()}
                with self.assertRaisesRegex(brief.BriefError, "index is missing"):
                    brief.preserve_weekly_archive(output)
                self.assertEqual(before, {str(p.relative_to(output)):p.read_bytes() for p in output.rglob("*") if p.is_file()})
                if directory: self.assertTrue((output/"index.html").is_dir())
                else: self.assertFalse((output/"index.html").exists())

    def test_empty_registry_needs_no_index_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            registry = output/"editions.json"
            registry.write_bytes(b'{"schema_version":1,"editions":[]}')
            before=registry.read_bytes()
            self.assertEqual(brief.preserve_weekly_archive(output),0)
            self.assertEqual(registry.read_bytes(),before)
            self.assertEqual(list(output.iterdir()),[registry])

if __name__ == "__main__": unittest.main()
