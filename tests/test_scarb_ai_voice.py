"""Offline fixtures, not evidence of a real model or live publication."""
import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import scarb_ai_voice as v

NOW = dt.datetime(2026, 11, 17, 15, tzinfo=dt.timezone.utc)
ENV = {"SCARB_AI_ENABLE": "1", "OPENAI_API_KEY": "fixture-not-a-key", "OPENAI_ORG_ID": "org-fixture", "OPENAI_PROJECT_ID": "proj-fixture"}
CONFIG = {"enabled": True, "author_model": "gpt-6.1-terra", "reviewer_model": "gpt-6.1-sol", "month_cap_usd": 5,
          "funding": {"kind": "promotional_api_credits", "organization": "org-fixture", "project": "proj-fixture",
                      "verified_at": "2026-11-17T14:00:00Z", "expires_at": "2026-12-01T00:00:00Z", "remaining_usd": 5, "cash_fallback_disabled": True}}
PACKET = {"id": "fixture.boundary", "surface": "neighbourhood", "kind": "editorial",
          "draft": "A map detail worth following: {{LOCK:PLACE}} has {{LOCK:COUNT}} records. {{LOCK:LIMIT}}",
          "locks": {"PLACE": "Fixture Neighbourhood", "COUNT": "12", "LIMIT": "Source records are not necessarily distinct businesses."},
          "evidence": [{"id": "fixture-map", "source": "repo:tests/fictional-evidence", "sha256": "a" * 64,
                        "fact": "Fictional test only: twelve source records, not necessarily distinct businesses."}],
          "limits": {"words": 100, "characters": 1000}}
OFFICIAL = {"id": "official.dinesafe-outcome", "surface": "source-note", "kind": "verbatim",
            "draft": "{{LOCK:VERBATIM}}", "locks": {"VERBATIM": "Conditional Pass"},
            "evidence": [{"id": "dinesafe-official", "source": "https://open.toronto.ca/dataset/dinesafe/",
                          "sha256": v.digest("Conditional Pass"), "fact": "Conditional Pass"}],
            "limits": {"words": 20, "characters": 200}}

REVIEW = {"approve": True, "meaning_preserved": True, "limitations_preserved": True, "voice_pass": True, "issues": []}


def writer(packet=PACKET):
    return {"body": packet["draft"], "evidence_ids": [x["id"] for x in packet["evidence"]]}


def response(value, status="completed"):
    return {"status": status, "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": json.dumps(value)}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50}}


class FakeTransport:
    def __init__(self, results=None):
        self.results = results if results is not None else [response(writer()), response(REVIEW)]
        self.calls = []

    def __call__(self, body, credentials):
        self.calls.append(body)
        return self.results.pop(0)


class AiVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)

    def generate(self, packet=None, config=None, transport=None, env=None):
        return v.generate(packet or copy.deepcopy(PACKET), config or copy.deepcopy(CONFIG), self.state,
                          transport=transport or FakeTransport(), env=ENV if env is None else env, now=NOW)

    def test_verbatim_cannot_bypass_ai_translator(self):
        # Ordinary house copy must go through the writer, even when someone
        # labels it verbatim. Official values can pass only as whole exact locks.
        with self.assertRaisesRegex(v.VoiceError, "Verbatim"):
            v.packet_check({**PACKET, "kind": "verbatim"})
        v.packet_check(OFFICIAL)
        for item in (
            {**OFFICIAL, "id": "static.home-intro"},
            {**OFFICIAL, "draft": "A lovely discovery: {{LOCK:VERBATIM}}"},
            {**OFFICIAL, "locks": {"VERBATIM": "Pass"}},
            {**OFFICIAL, "evidence": [{**OFFICIAL["evidence"][0], "source": "https://example.invalid"}]},
            {**OFFICIAL, "evidence": [{**OFFICIAL["evidence"][0], "sha256": "a"*64}]},
            {**OFFICIAL, "surface": "community"},
        ):
            with self.subTest(item=item), self.assertRaises(v.VoiceError):
                v.packet_check(item)

    def test_input_schema_and_protected_facts(self):
        v.packet_check(PACKET)
        result = v.text_check(PACKET, writer())
        self.assertIn("Fixture Neighbourhood has 12 records", result)
        for change in ("missing", "extra", "duplicate", "raw_number", "link", "html", "wrong_reference"):
            with self.subTest(change=change):
                output = writer()
                if change == "missing": output["body"] = output["body"].replace("{{LOCK:LIMIT}}", "")
                if change == "extra": output["body"] += " {{LOCK:UNSUPPORTED}}"
                if change == "duplicate": output["body"] += " {{LOCK:COUNT}}"
                if change == "raw_number": output["body"] += " This is up 20 percent."
                if change == "link": output["body"] += " https://example.invalid"
                if change == "html": output["body"] += " <script>"
                if change == "wrong_reference": output["evidence_ids"] = ["fabricated-source"]
                with self.assertRaises(v.VoiceError): v.text_check(PACKET, output)

    def test_unknown_fields_and_nested_tokens_rejected(self):
        for modification in ({"personal_address": "not allowed"}, {"surface": "unclassified"}, {"kind": "raw"}):
            with self.assertRaises(v.VoiceError): v.packet_check({**PACKET, **modification})
        p = copy.deepcopy(PACKET)
        p["locks"]["PLACE"] = "{{LOCK:COUNT}}"
        with self.assertRaises(v.VoiceError): v.packet_check(p)

    def test_limits_measured_after_expansion(self):
        p = copy.deepcopy(PACKET)
        p["locks"]["PLACE"] = "Long Name " * 40
        with self.assertRaises(v.VoiceError): v.text_check({**p, "limits": {"words": 40, "characters": 200}}, writer(p))

    def test_fixed_warnings_use_no_model(self):
        p = copy.deepcopy(OFFICIAL)
        fake = FakeTransport([])
        receipt = self.generate(p, {**CONFIG, "enabled": False}, fake)
        self.assertEqual(fake.calls, [])
        self.assertEqual(receipt["origin"], "protected-verbatim")
        self.assertEqual(v.compile_catalogue([p], CONFIG, self.state)["entries"][p["id"]]["text"], receipt["text"])

    def test_live_calls_require_explicit_activation(self):
        fake = FakeTransport()
        with self.assertRaises(v.VoiceError): self.generate(config={**CONFIG, "enabled": False}, transport=fake)
        self.assertEqual(fake.calls, [])
        with self.assertRaises(v.VoiceError): self.generate(transport=fake, env={"SCARB_AI_ENABLE": "0"})

    def test_funding_expiry_wrong_identity_and_cash_fail_closed(self):
        for change in ({"expires_at": "2026-11-01T00:00:00Z"}, {"organization": "wrong-org"}, {"cash_fallback_disabled": False}, {"remaining_usd": 0}, {"verified_at": "2027-01-01T00:00:00Z"}):
            config = copy.deepcopy(CONFIG)
            config["funding"].update(change)
            fake = FakeTransport()
            with self.subTest(change=change), self.assertRaises(v.VoiceError): self.generate(config=config, transport=fake)
            self.assertEqual(fake.calls, [])

    def test_model_and_budget_validation(self):
        for change in ({"month_cap_usd": float("nan")}, {"month_cap_usd": 26}, {"author_model": "unknown"}, {"reviewer_model": CONFIG["author_model"]}):
            with self.assertRaises(v.VoiceError): v.check_config({**CONFIG, **change})

    def test_author_and_reviewer_have_separate_context_and_models(self):
        fake = FakeTransport()
        receipt = self.generate(transport=fake)
        self.assertEqual(receipt["origin"], "test-fixture")
        self.assertEqual(len(fake.calls), 2)
        self.assertNotEqual(fake.calls[0]["model"], fake.calls[1]["model"])
        for call in fake.calls:
            self.assertFalse(call["store"])
            self.assertFalse(call["background"])
            self.assertEqual(call["tools"], [])
            self.assertTrue(call["text"]["format"]["strict"])
        self.assertNotIn("candidate", json.loads(fake.calls[0]["input"][0]["content"][0]["text"]))
        self.assertEqual(json.loads(fake.calls[1]["input"][0]["content"][0]["text"])["candidate"], writer())

    def test_exact_input_cache_avoids_another_call(self):
        first = self.generate()
        fake = FakeTransport([])
        second = self.generate(transport=fake)
        self.assertEqual(first, second)
        self.assertEqual(fake.calls, [])

    def test_new_source_or_voice_requires_new_receipt(self):
        self.generate()
        for kind in ("fact", "limit", "model", "prompt"):
            p, c = copy.deepcopy(PACKET), copy.deepcopy(CONFIG)
            if kind == "fact": p["evidence"][0]["sha256"] = "b" * 64
            if kind == "limit": p["limits"]["characters"] = 900
            if kind == "model": c["author_model"] = "gpt-6-luna"
            if kind == "prompt":
                with patch.object(v, "AUTHOR", v.AUTHOR + " Revised."):
                    with self.assertRaises(v.VoiceError): v.compile_catalogue([p], c, self.state)
                continue
            with self.assertRaises(v.VoiceError): v.compile_catalogue([p], c, self.state)

    def test_model_rejection_never_creates_accepted_output(self):
        fake = FakeTransport([response(writer()), response({**REVIEW, "meaning_preserved": False, "issues": ["Unsupported inference"]})])
        with self.assertRaises(v.VoiceError): self.generate(transport=fake)
        self.assertFalse((self.state / "accepted").exists())
        ledger = json.loads((self.state / "usage.json").read_text())
        self.assertGreater(ledger["months"]["2026-11"], 0)

    def test_failed_attempt_keeps_budget_reservation_and_no_retry(self):
        fake = FakeTransport([response(writer(), "incomplete")])
        with self.assertRaises(v.VoiceError): self.generate(transport=fake)
        self.assertEqual(len(fake.calls), 1)
        self.assertGreater(json.loads((self.state / "usage.json").read_text())["months"]["2026-11"], 0)

    def test_rejected_exact_input_is_held_without_daily_retries(self):
        first = FakeTransport([response(writer(), "incomplete")])
        with self.assertRaises(v.VoiceError): self.generate(transport=first)
        second = FakeTransport([])
        with self.assertRaisesRegex(v.VoiceError, "prior attempt"): self.generate(transport=second)
        self.assertEqual(second.calls, [])

    def test_local_budget_prevents_call(self):
        fake = FakeTransport()
        with self.assertRaises(v.VoiceError): self.generate(config={**CONFIG, "month_cap_usd": 0.001}, transport=fake)
        self.assertEqual(fake.calls, [])

    def test_usage_overrun_closes_budget_for_further_calls(self):
        oversized = response(writer())
        oversized["usage"]["input_tokens"] = 99999
        with self.assertRaises(v.VoiceError): self.generate(transport=FakeTransport([oversized]))
        self.assertEqual(json.loads((self.state / "usage.json").read_text())["months"]["2026-11"], 5)
        fake = FakeTransport()
        with self.assertRaises(v.VoiceError): self.generate(transport=fake)
        self.assertEqual(fake.calls, [])

    def test_refusal_and_missing_usage_never_publish(self):
        bad = [response(writer(), "incomplete"), {"status": "completed", "output": [{"type": "message", "role": "assistant", "content": [{"type": "refusal"}]}]}, {**response(writer()), "usage": {}}]
        for value in bad:
            with self.assertRaises(v.VoiceError): v.unpack(value)

    def test_cache_tampering_fails_instead_of_regenerating(self):
        receipt = self.generate()
        path = self.state / "accepted" / (receipt["key"] + ".json")
        receipt["text"] = "Changed"
        path.write_text(json.dumps(receipt))
        fake = FakeTransport([])
        with self.assertRaises(v.VoiceError): self.generate(transport=fake)
        self.assertEqual(fake.calls, [])

    def test_public_catalogue_requires_exact_protected_receipt_bytes(self):
        p = copy.deepcopy(OFFICIAL)
        self.generate(p, {**CONFIG, "enabled": False}, FakeTransport([]))
        catalogue = v.compile_catalogue([p], CONFIG, self.state)
        path = self.state / "candidate.json"
        path.write_text(json.dumps(catalogue), encoding="utf-8")
        self.assertTrue(v.verify_catalogue([p], CONFIG, self.state, path))
        edited = copy.deepcopy(catalogue)
        edited["entries"][p["id"]]["text"] += " A different sentence."
        path.write_text(json.dumps(edited), encoding="utf-8")
        with self.assertRaisesRegex(v.VoiceError, "differs"):
            v.verify_catalogue([p], CONFIG, self.state, path)
        path.unlink()
        with self.assertRaisesRegex(v.VoiceError, "missing"):
            v.verify_catalogue([p], CONFIG, self.state, path)

    def test_fixture_receipts_cannot_be_published_as_api_results(self):
        self.generate()
        with self.assertRaisesRegex(v.VoiceError, "Unqualified"): v.compile_catalogue([PACKET], CONFIG, self.state)

    def test_provider_errors_redact_details(self):
        with patch.object(v.urllib.request, "build_opener", side_effect=OSError("fixture-secret: raw-body")):
            with self.assertRaises(v.VoiceError) as error: v.api_request({}, {"key": "secret", "organization": "org", "project": "proj"})
        self.assertNotIn("fixture-secret", str(error.exception))
        self.assertNotIn("secret", str(error.exception))

    def test_redirect_not_followed_and_fixed_endpoint(self):
        self.assertIsNone(v.NoRedirect().redirect_request(None, None, None, None, None, None))
        self.assertEqual(v.ENDPOINT, "https://api.openai.com/v1/responses")

    def test_concurrent_generation_refuses_lock(self):
        with v.exclusive(self.state):
            with self.assertRaises(v.VoiceError): self.generate()
        self.assertFalse((self.state / "generation.lock").exists())

    def test_packet_not_mutated(self):
        original = copy.deepcopy(PACKET)
        self.generate(PACKET)
        self.assertEqual(PACKET, original)

    def test_compile_all_or_nothing_duplicate_and_missing_entries(self):
        p = copy.deepcopy(OFFICIAL)
        self.generate(p, {**CONFIG, "enabled": False}, FakeTransport([]))
        self.assertEqual(len(v.compile_catalogue([p], CONFIG, self.state)["entries"]), 1)
        with self.assertRaises(v.VoiceError): v.compile_catalogue([p, p], CONFIG, self.state)
        with self.assertRaises(v.VoiceError): v.compile_catalogue([p, {**p, "id": "missing"}], CONFIG, self.state)


if __name__ == "__main__":
    unittest.main()
