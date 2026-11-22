"""Offline synthetic custody fixtures, never real AI or publication evidence."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import scarb_ai_voice as voice
from scripts.scarb_accepted_copy import accepted_resolver
from scripts.stage_scarb_ai_inputs import generator_inputs, stage_inputs
from tests.test_scarb_ai_voice import CONFIG, OFFICIAL, NOW, PACKET, FakeTransport, ENV


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.config = {**copy.deepcopy(CONFIG), "enabled": False, "month_cap_usd": 0}
        self.packet = copy.deepcopy(OFFICIAL)
        voice.generate(self.packet, self.config, self.state, now=NOW, env={})
        self.candidate = self.state / "candidate.json"
        self.candidate.write_bytes(voice.encoded(voice.compile_catalogue([self.packet], self.config, self.state)))

    def test_exact_receipts_bind_browser_and_python_inputs_without_provider(self):
        with patch.object(voice, "api_request", side_effect=AssertionError("No network allowed")):
            files = generator_inputs([self.packet], self.config, self.state, self.candidate)
        public = json.loads(files["accepted-copy.json"])
        module = files["accepted-copy.mjs"].decode().split("export default ", 1)[1][:-2]
        self.assertEqual(json.loads(module), public)
        expected = {self.packet["id"]: voice.digest(self.packet)}
        self.assertNotIn("expected", public)
        self.assertEqual(accepted_resolver(public, expected)(self.packet["id"]), "Conditional Pass")
        receipt = json.loads(files["private-input-attestation.json"])
        self.assertEqual(receipt["authoring_request_manifest"], expected)
        for name, digest in receipt["files"].items():
            self.assertEqual(hashlib.sha256(files[name]).hexdigest(), digest)
        for private in ("funding", "OPENAI_API_KEY", "usage", "org-fixture", "proj-fixture"):
            self.assertNotIn(private, files["accepted-copy.json"].decode())

    def test_static_materialization_uses_private_verified_receipt_and_attested_bytes(self):
        from scripts.scarb_static_materialize import discover
        source='<p>Conditional Pass</p>'
        shells={'docs/fixture.html':{'source':source,'slots':[{**discover(source)[0],'id':self.packet['id']}]}}
        files=generator_inputs([self.packet],self.config,self.state,self.candidate,shells=shells)
        self.assertEqual(files['docs/fixture.html'],source.encode())
        attestation=json.loads(files['private-input-attestation.json'])
        self.assertEqual(attestation['files']['docs/fixture.html'],hashlib.sha256(source.encode()).hexdigest())
        shells['docs/briefs/2026-11-02/index.html']=shells.pop('docs/fixture.html')
        with self.assertRaises(voice.VoiceError):generator_inputs([self.packet],self.config,self.state,self.candidate,shells=shells)

    def test_dry_run_byte_comparison_holds_tampered_output_without_install(self):
        from scripts.stage_scarb_ai_inputs import compare_publication
        files=generator_inputs([self.packet],self.config,self.state,self.candidate)
        publication=self.state/'synthetic-output';(publication/'docs').mkdir(parents=True)
        mapping={'accepted-copy.json':'scarb-copy-inputs.json','accepted-copy.mjs':'scarb-copy-inputs.mjs',
          'event-inputs.json':'scarb-event-inputs.json','event-inputs.mjs':'scarb-event-inputs.mjs',
          'current-request-manifest.json':'scarb-copy-manifest.json','current-request-manifest.mjs':'scarb-copy-manifest.mjs','event-source.json':'scarb-event-source.json'}
        for source,target in mapping.items():(publication/'docs'/target).write_bytes(files[source])
        compare_publication([self.packet],self.config,self.state,self.candidate,publication)
        target=publication/'docs/scarb-copy-inputs.json';target.write_bytes(target.read_bytes()+b' ')
        with self.assertRaises(voice.VoiceError):compare_publication([self.packet],self.config,self.state,self.candidate,publication)

    def test_event_enabled_stage_keeps_catalogue_json_not_release_bytes(self):
        # Mock only acceptance for this formatting regression. This is never
        # evidence of a real AI receipt or permission to publish a fixture.
        root=Path(__file__).resolve().parents[1]
        pointer=json.loads((root/'docs/community-data/latest.json').read_text())
        raw=(root/'docs/community-data/releases'/(pointer['release_id']+'.json')).read_bytes().replace(b'\r\n',b'\n')
        release=json.loads(raw);event=release['events'][0]
        fields=('id','feed','establishment_id','name','kind','status','previous_status','inspection_date','detected_at','source_url')
        facts={k:event[k] for k in fields if k in event}
        packet={'id':'event.'+voice.digest(event['id']),'evidence':[{'fact':voice.encoded(facts).decode()}]}
        accepted={'version':voice.VERSION,'entries':{packet['id']:{'receipt_sha256':'a'*64,'text':'Formatting fixture'}}}
        self.candidate.write_bytes(voice.encoded(accepted))
        with patch('scripts.stage_scarb_ai_inputs.verify_catalogue'),patch('scripts.stage_scarb_ai_inputs.compile_catalogue',return_value=accepted):
            files=generator_inputs([packet],self.config,self.state,self.candidate,event_source={'release_id':pointer['release_id'],'sha256':hashlib.sha256(raw).hexdigest()})
        module=json.loads(files['accepted-copy.mjs'].decode().split('export default ',1)[1][:-2])
        self.assertEqual(json.loads(files['accepted-copy.json']),module)
        self.assertEqual(module,accepted)
        self.assertNotEqual(files['accepted-copy.json'],raw)
        attestation=json.loads(files['private-input-attestation.json'])
        self.assertEqual(attestation['files']['accepted-copy.json'],hashlib.sha256(files['accepted-copy.json']).hexdigest())

    def test_tampered_catalogue_does_not_gain_authority_from_self_reported_hash(self):
        changed = json.loads(self.candidate.read_text())
        changed["entries"][self.packet["id"]]["text"] = "Safe now"
        self.candidate.write_text(json.dumps(changed))
        with self.assertRaises(voice.VoiceError):
            generator_inputs([self.packet], self.config, self.state, self.candidate)

    def test_missing_private_receipt_and_changed_current_request_hold(self):
        with self.assertRaises(voice.VoiceError):
            generator_inputs([{**self.packet, "id": "official.changed"}], self.config, self.state, self.candidate)
        receipt = self.state / "accepted" / (voice.cache_key(self.packet, self.config) + ".json")
        receipt.rename(self.state / "saved-fixture-receipt.json")
        with self.assertRaises(voice.VoiceError):
            generator_inputs([self.packet], self.config, self.state, self.candidate)

    def test_mock_writer_output_never_becomes_publishable_input(self):
        voice.generate(PACKET, CONFIG, self.state, transport=FakeTransport(), env=ENV, now=NOW)
        with self.assertRaises(voice.VoiceError):
            generator_inputs([PACKET], CONFIG, self.state, self.candidate)

    def test_python_producer_substitutes_only_current_accepted_copy(self):
        from scripts.scarb_voice import compose_copy, COPY
        original = COPY["rss-inspection"]
        self.assertEqual(compose_copy("rss-inspection", {"DATE": "November 10, 2026"},
                                     lambda key, draft: "Fixture checked date: {{DATE}}."),
                         "Fixture checked date: November 10, 2026.")
        self.assertEqual(COPY["rss-inspection"], original)
        with self.assertRaisesRegex(ValueError, "placeholders"):
            compose_copy("rss-inspection", {"DATE": "November 10, 2026"}, lambda key, draft: "Unbound date")

    def test_stage_only_new_private_destination_not_public_install(self):
        output = self.state / "staged"
        stage_inputs([self.packet], self.config, self.state, self.candidate, output)
        self.assertTrue((output / "accepted-copy.mjs").is_file())
        with self.assertRaises(voice.VoiceError):
            stage_inputs([self.packet], self.config, self.state, self.candidate, output)
        with self.assertRaises(voice.VoiceError):
            stage_inputs([self.packet], self.config, self.state, self.candidate, self.state.parent / "public-output")

    def test_python_consumer_holds_unaccepted_missing_or_stale_copy(self):
        public = json.loads(generator_inputs([self.packet], self.config, self.state, self.candidate)["accepted-copy.json"])
        expected = {self.packet["id"]: voice.digest(self.packet)}
        resolve = accepted_resolver(public, expected)
        with self.assertRaises(ValueError):
            resolve("missing")
        for change in ({"origin": "test-fixture"}, {"packet_sha256": "a" * 64}, {"text": ""}):
            changed = copy.deepcopy(public)
            changed["entries"][self.packet["id"]].update(change)
            with self.assertRaises(ValueError):
                accepted_resolver(changed, expected)


if __name__ == "__main__":
    unittest.main()
