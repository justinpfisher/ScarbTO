"""Synthetic transport only. No credential discovery, provider or account calls."""
import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from scripts import scarb_ai_voice as v
from tests.test_scarb_ai_voice import CONFIG, ENV, NOW, PACKET, REVIEW, FakeTransport, response, writer


def paid_config():
    config = copy.deepcopy(CONFIG)
    config.update(author_model="gpt-6-luna", reviewer_model="gpt-6.1-terra")
    config["funding"].pop("cash_fallback_disabled")
    config["funding"].update(kind="existing_paid_api_credits", auto_recharge_disabled=True,
                             postpaid_disabled=True, pilot_cap_usd=0.25)
    return config


class PaidPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)

    def generate(self, config=None, packet=None, transport=None, now=NOW, env=None):
        return v.generate(packet or copy.deepcopy(PACKET), config or paid_config(), self.state,
                          transport=transport or FakeTransport(), env=ENV if env is None else env, now=now)

    def test_paid_variant_is_explicit_and_separate_from_unchanged_promotion(self):
        self.assertEqual(v.funding_check(paid_config(), NOW, ENV)["project"], "proj-fixture")
        self.assertEqual(v.funding_check(CONFIG, NOW, ENV)["project"], "proj-fixture")
        fake = FakeTransport()
        receipt = self.generate(transport=fake)
        self.assertEqual(receipt["origin"], "test-fixture")
        self.assertEqual([call["model"] for call in fake.calls], ["gpt-6-luna", "gpt-6.1-terra"])
        self.assertEqual(len(fake.calls), 2)
        ledger = json.loads((self.state / "usage.json").read_text())
        self.assertGreater(ledger["paid_pilot_usd"], 0)
        self.assertEqual(ledger["paid_pilot_usd"], ledger["months"]["2026-11"])

    def test_payment_exposure_identity_expiry_and_missing_receipt_hold_before_calls(self):
        for change in ({"auto_recharge_disabled": False}, {"postpaid_disabled": False},
                       {"organization": "wrong-org"}, {"project": "wrong-project"},
                       {"expires_at": "2026-11-01T00:00:00Z"},
                       {"verified_at": "2027-01-01T00:00:00Z"},
                       {"remaining_usd": 0}, {"remaining_usd": float("inf")},
                       {"pilot_cap_usd": 0.26}, {"pilot_cap_usd": float("nan")},
                       {"cash_fallback_disabled": True}):
            config = paid_config()
            config["funding"].update(change)
            fake = FakeTransport()
            with self.subTest(change=change), self.assertRaises(v.VoiceError):
                self.generate(config, transport=fake)
            self.assertEqual(fake.calls, [])
        for key in ("postpaid_disabled", "auto_recharge_disabled", "pilot_cap_usd"):
            config = paid_config()
            del config["funding"][key]
            with self.assertRaises(v.VoiceError):
                self.generate(config)

    def test_no_activation_no_credentials_and_no_expensive_model_switch(self):
        for config, env in (({**paid_config(), "enabled": False}, ENV), (paid_config(), {}),
                            ({**paid_config(), "reviewer_model": "gpt-6.1-sol"}, ENV),
                            ({**paid_config(), "month_cap_usd": 5.01}, ENV)):
            fake = FakeTransport()
            with self.assertRaises(v.VoiceError):
                self.generate(config, env=env, transport=fake)
            self.assertEqual(fake.calls, [])

    def test_reservation_and_failed_attempt_consume_pilot_and_hold_exact_retry(self):
        fake = FakeTransport([response(writer(), "incomplete")])
        with self.assertRaises(v.VoiceError):
            self.generate(transport=fake)
        ledger = json.loads((self.state / "usage.json").read_text())
        self.assertAlmostEqual(ledger["paid_pilot_usd"], v.reservation_bound(PACKET, paid_config())[1], places=6)
        retry = FakeTransport([])
        with self.assertRaisesRegex(v.VoiceError, "prior attempt"):
            self.generate(transport=retry)
        self.assertEqual(retry.calls, [])

    def test_one_time_pilot_does_not_reset_with_new_month_or_new_request(self):
        (self.state / "usage.json").write_text(json.dumps({"months": {}, "paid_pilot_usd": 0.25}))
        config = paid_config()
        config["funding"]["verified_at"] = "2026-12-02T00:00:00Z"
        config["funding"]["expires_at"] = "2027-01-01T00:00:00Z"
        fake = FakeTransport([])
        with self.assertRaisesRegex(v.VoiceError, "pilot ceiling"):
            self.generate(config, packet={**PACKET, "id": "another.request"}, transport=fake,
                          now=dt.datetime(2026, 12, 3, tzinfo=dt.timezone.utc))
        self.assertEqual(fake.calls, [])

    def test_monthly_fuse_still_applies_even_with_pilot_room(self):
        (self.state / "usage.json").write_text(json.dumps({"months": {"2026-11": 5}, "paid_pilot_usd": 0}))
        fake = FakeTransport([])
        with self.assertRaisesRegex(v.VoiceError, "Monthly"):
            self.generate(transport=fake)
        self.assertEqual(fake.calls, [])

    def test_usage_overrun_closes_both_fuses(self):
        oversized = response(writer())
        oversized["usage"]["input_tokens"] = 99999
        with self.assertRaises(v.VoiceError):
            self.generate(transport=FakeTransport([oversized]))
        ledger = json.loads((self.state / "usage.json").read_text())
        self.assertEqual(ledger["paid_pilot_usd"], 0.25)
        self.assertEqual(ledger["months"]["2026-11"], 5)

    def test_accepted_cache_uses_zero_calls_and_no_extra_pilot_budget(self):
        self.generate()
        before = (self.state / "usage.json").read_bytes()
        fake = FakeTransport([])
        self.generate(transport=fake)
        self.assertEqual(fake.calls, [])
        self.assertEqual((self.state / "usage.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()


class TruthfulPrepaidPilotTests(unittest.TestCase):
    def config(self):
        config=paid_config()
        config["funding"].pop("postpaid_disabled")
        config["funding"].update(billing_mode="prepaid_cutoff_not_guaranteed",remaining_usd=10,
          organization="org-EIn1HXt0x19rnOSvte7dVrB9",project="proj_ZiSvyeNLotSbqtH2vDEKqNxx",
          verified_at=NOW.isoformat(),pilot_request_sha256=[
            "d1ee00949d7848b8046873c82dcd4490ef73f0b64b8bb2b8a204b435131c8fc0",
            "e8f8d7fda9aa2749b15acaf4450a988b9b29882b04fabd194168bce6f5b6fd18"])
        return config
    def env(self):
        return {**ENV,"OPENAI_ORG_ID":"org-EIn1HXt0x19rnOSvte7dVrB9","OPENAI_PROJECT_ID":"proj_ZiSvyeNLotSbqtH2vDEKqNxx"}
    def test_truthful_unknown_cutoff_is_separate_no_false_postpaid_attestation(self):
        config=self.config();v.check_config(config)
        self.assertEqual(v.funding_check(config,NOW,self.env())["project"],config["funding"]["project"])
        self.assertNotIn("postpaid_disabled",config["funding"])
        self.assertEqual(v.funding_check(CONFIG,NOW,ENV)["project"],"proj-fixture")
    def test_stale_small_balance_identity_recharge_or_expanded_scope_holds(self):
        for update in ({"remaining_usd":5.24},{"auto_recharge_disabled":False},{"project":"proj-other"},
                       {"verified_at":(NOW-dt.timedelta(hours=1,seconds=1)).isoformat()},
                       {"verified_at":(NOW+dt.timedelta(seconds=1)).isoformat()},
                       {"pilot_request_sha256":[]},{"postpaid_disabled":True}):
            config=self.config();config["funding"].update(update)
            with self.subTest(update=update),self.assertRaises(v.VoiceError):v.funding_check(config,NOW,self.env())
    def test_nonpilot_request_cannot_call_even_with_matching_identity(self):
        with tempfile.TemporaryDirectory() as state:
            fake=FakeTransport()
            with self.assertRaisesRegex(v.VoiceError,"two-packet"):
                v.generate(copy.deepcopy(PACKET),self.config(),Path(state),transport=fake,env=self.env(),now=NOW)
            self.assertEqual(fake.calls,[])
