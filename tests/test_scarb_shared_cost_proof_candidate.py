import unittest,tempfile,json,copy
from pathlib import Path
from scripts import scarb_shared_cost_proof_candidate as a,scarb_packet_consumption_candidate as c
class SharedCostTests(unittest.TestCase):
 def setUp(self):
  self.before={'months':{'2026-10':.1,'2026-11':.663943},'paid_pilot_usd':.663943};self.bindings={'A':a.v.digest('A')}
 def test_actual_usage_shape_decimal_round_up_and_proof(self):
  after,charge=a.debit(self.before,'2026-11',14393001,1000000000,1000000000)
  self.assertEqual(charge,14394000);self.assertEqual(after['months']['2026-10'],.1)
  ma={self.bindings['A']:a.v.digest(self.bindings)}
  proof=a.proof(self.before,after,'2026-11',14393001,123,1000000000,1000000000,self.bindings,{},ma)
  self.assertTrue(a.validate_proof(proof,self.before,after,{},ma));self.assertEqual(proof['version'],'scarb-shared-cost-proof-2')
  for mutate in ['refund','other_month','member']:
   changed=copy.deepcopy(after);members=ma
   if mutate=='refund':changed['paid_pilot_usd']=self.before['paid_pilot_usd']
   elif mutate=='other_month':changed['months']['2026-10']=0
   else:members={}
   with self.assertRaises(a.v.VoiceError):a.validate_proof(proof,self.before,changed,{},members)
 def test_bad_numbers_caps(self):
  for x in [float('nan'),float('inf'),True,-1,.0000000001,'1']:
   with self.assertRaises(a.v.VoiceError):a.amount(x)
  with self.assertRaises(a.v.VoiceError):a.debit(self.before,'2026-11',1,663943000,663943000)
 def test_actual_debit_claim_and_crash_gap_no_replay(self):
  for point in [None,'before_debit','after_debit','after_membership']:
   with self.subTest(point=point),tempfile.TemporaryDirectory() as d:
    root=Path(d);(root/'SYNTHETIC_GROUPED_ACCOUNTING_ONLY').touch();a.v.atomic_json(root/'usage.json',self.before)
    if point:
     with self.assertRaises(RuntimeError):a.fixture_debit(root,root,self.bindings,14393001,'2026-11',1000000000,1000000000,crash_at=point)
    else:a.fixture_debit(root,root,self.bindings,14393001,'2026-11',1000000000,1000000000)
    usage=json.loads((root/'usage.json').read_text());self.assertEqual(usage,self.before if point=='before_debit' else a.debit(self.before,'2026-11',14393001,1000000000,1000000000)[0])
    with a.v.exclusive(root):
     with self.assertRaises(a.v.VoiceError):c.assert_unconsumed(root,self.bindings,expected_root=root)
    with self.assertRaises(a.v.VoiceError):a.fixture_debit(root,root,self.bindings,14393001,'2026-11',1000000000,1000000000)
    self.assertEqual(json.loads((root/'usage.json').read_text()),usage)
if __name__=='__main__':unittest.main()

class VerifierSharedCostTests(unittest.TestCase):
 def test_contextual_verifier_consumes_actual_shared_ledger_proof(self):
  from tests.test_scarb_grouped_context_candidate import ContextProvenanceTests
  fixture=ContextProvenanceTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
  old=fixture.extra['budget.json'];before={'months':{'2026-11':.663943},'paid_pilot_usd':.663943}
  reserve=fixture.pin['reservation_nusd'];after,_=a.debit(before,'2026-11',reserve,1000000000,1000000000)
  ma={h:a.v.digest(fixture.pin['packet_bindings']) for h in fixture.pin['packet_bindings'].values()}
  budget=a.proof(before,after,'2026-11',reserve,old['actual_usage_cost_nusd'],1000000000,1000000000,fixture.pin['packet_bindings'],{},ma)
  budget.update({k:old[k] for k in ['funding_sha256','prices_sha256','input_bounds','output_bounds']})
  fixture.extra.update({'ledger-before.json':before,'ledger-after.json':after,'membership-before.json':{},'membership-after.json':ma,'budget.json':budget})
  fixture.pin.update(cost_version=2,month_cap_nusd=1000000000,membership_before_sha256=a.v.digest({}),ledger_before_sha256=a.v.digest(before))
  fixture.seal.update(budget_sha256=a.v.digest(budget),ledger_after_sha256=a.v.digest(after),packet_membership_sha256=a.v.digest(ma));fixture.sync()
  verified=fixture.verify();self.assertEqual(verified['cost_proof']['debited_nusd'],budget['debited_nusd'])
  fixture.extra['ledger-after.json']['paid_pilot_usd']=.663943;fixture.sync()
  with self.assertRaises(a.v.VoiceError):fixture.verify()
