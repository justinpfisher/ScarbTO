"""The dormant authoring adapter must reject missing or unqualified evidence."""
import unittest
from unittest.mock import patch

from scripts import scarb_ai_fact_slots as solo, scarb_ai_voice as voice
from scripts import scarb_neighbourhood_notebook as notebook

AREA = {"code": "999", "name": "Fable Crossing", "slug": "fable-crossing"}
TARGET = "docs/fable-crossing/index.html"
PAGES = {TARGET: b"fictional baseline"}


class NotebookReviewTests(unittest.TestCase):
    def setUp(self):
        fact = "Fictional exhibit"
        self.packet = {
            "id": "notebook.999", "surface": "neighbourhood", "kind": "editorial",
            "draft": "A finding in {{LOCK:AREA}}. {{LOCK:LIMIT}}",
            "locks": {"AREA": AREA["name"], "LIMIT": "This is fictional."},
            "evidence": [{"id": "exhibit", "source": "https://example.invalid/catalogue",
                          "fact": fact, "sha256": voice.digest(fact)}],
            "limits": {"words": 30, "characters": 150},
        }
        self.mock_receipt = {"origin": "test-fixture", "version": solo.VERSION, "sha256": "a" * 64}
        self.stage = {"version": notebook.STAGE_VERSION, "area": AREA, "heading": "Fable note",
                      "links": {"exhibit": "Catalogue"}, "base_sha256": notebook.release.digest(PAGES[TARGET]),
                      "output_sha256": "b" * 64, "packet_sha256": voice.digest(self.packet),
                      "receipt_sha256": self.mock_receipt["sha256"]}
        self.config = {"author_model": "fixture writer", "reviewer_model": "fixture reviewer"}

    def prepare(self, **overrides):
        values = {"stage": self.stage, "packet": self.packet, "receipt": self.mock_receipt, "config": self.config}
        return notebook.prepare_neighbourhood_notebook(PAGES, **{**values, **overrides})

    def test_production_default_requires_independent_enrollment(self):
        self.assertIs(notebook.project_neighbourhood_notebook(PAGES), PAGES)
        with self.assertRaisesRegex(voice.VoiceError, "No independently approved"):
            self.prepare()
        with self.assertRaisesRegex(voice.VoiceError, "No independently approved"):
            self.prepare(stage=None)

    def test_enrolled_scope_still_refuses_unqualified_or_mismatched_material(self):
        changed = {**self.packet, "id": "notebook.998"}
        with patch.object(notebook, "TRUSTED_STAGE_SHA256", voice.digest(self.stage)), \
             patch.object(notebook, "verify_neighbourhood_sources") as current_sources:
            with self.assertRaisesRegex(voice.VoiceError, "No independently approved"):
                self.prepare(stage={**self.stage, "heading": "Changed heading"})
            current_sources.assert_not_called()
            with self.assertRaisesRegex(voice.VoiceError, "source packet is missing"):
                self.prepare(packet=None)
            with self.assertRaisesRegex(voice.VoiceError, "area and source limitation"):
                self.prepare(packet=changed)
            with self.assertRaisesRegex(voice.VoiceError, "exact receipt differs"):
                self.prepare(receipt=None)
            with self.assertRaisesRegex(voice.VoiceError, "exact receipt differs"):
                self.prepare(receipt={**self.mock_receipt, "sha256": "c" * 64})
            with self.assertRaisesRegex(voice.VoiceError, "separate author and reviewer"):
                self.prepare(config={"author_model": "same", "reviewer_model": "same"})
            with self.assertRaisesRegex(voice.VoiceError, "Unqualified v2 receipt"):
                self.prepare()
        self.assertEqual(PAGES, {TARGET: b"fictional baseline"})
