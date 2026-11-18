import unittest,tempfile,json,copy
from pathlib import Path
from unittest.mock import patch
from scripts import scarb_grouped_runner_candidate as r,scarb_grouped_context_candidate as c,scarb_grouped_provenance_candidate as p
from tests.test_scarb_grouped_mixed_canonical import output,REVIEW,MODELS
from tests.test_scarb_ai_voice import response
class RunnerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.current=c.seam.current_canonical_requests();cls.packets=[cls.current[i] for i in c.ANCHORS]
 def inputs(self,state):
  (state/'SYNTHETIC_GROUPED_ACCOUNTING_ONLY').touch();r.save(state,'usage.json',{'months':{'2026-11':.663943},'paid_pilot_usd':.663943})
  funding={'observed_at':'2026-11-18T03:00:00Z','expires_at':'2026-11-18T04:00:00Z','balance_nusd':67000000000,'auto_recharge_disabled':True,'organization':'synthetic-org','project':'synthetic-project','cap_nusd':1000000000}
  prices={'gpt-6-luna':{'input_nusd_per_million':100000000,'output_nusd_per_million':500000000},'gpt-6.1-terra':{'input_nusd_per_million':1000000000,'output_nusd_per_million':5000000000}}
  ar=response({x['id']:output(x) for x in self.packets});ar.update(id='synthetic-author',model=MODELS['author'])
  rr=response({x['id']:REVIEW for x in self.packets});rr.update(id='synthetic-reviewer',model=MODELS['reviewer'])
  return funding,prices,r.f.FixtureTransport([ar,rr])
 def run_case(self,state,crash=None):
  funding,prices,t=self.inputs(state)
  return r.run_fixture(state,self.packets,MODELS,funding,prices,transport=t,started_at='2026-11-18T03:01:00Z',completed_at='2026-11-18T03:01:05Z',crash_at=crash),t
 def test_completed_sequence_emits_verifiable_records(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);result,t=self.run_case(state)
   self.assertEqual(result['calls'],2);self.assertEqual(len(t.calls),2)
   self.assertEqual(r.recover_fixture(state,self.packets),{'status':'completed','calls':2,'validated_stages':2,'replay_allowed':False})
   self.assertEqual(r.load(state/'usage.json'),r.load(Path(result['root'])/'ledger-after.json'))
   with self.assertRaises(r.v.VoiceError):p.verify_grouped_provenance(result['root'],self.packets)
 def test_interrupt_after_reserve_or_each_response_reopens_no_retry(self):
  for point,calls in [('after_reserve',0),('after_author_response',1),('after_reviewer_response',2)]:
   with self.subTest(point=point),tempfile.TemporaryDirectory() as d:
    state=Path(d);funding,prices,t=self.inputs(state)
    kwargs=dict(transport=t,started_at='2026-11-18T03:01:00Z',completed_at='2026-11-18T03:01:05Z')
    with self.assertRaises(RuntimeError):r.run_fixture(state,self.packets,MODELS,funding,prices,crash_at=point,**kwargs)
    outcome=r.recover_fixture(state,self.packets);self.assertEqual(outcome['status'],'held-uncertain');self.assertEqual(outcome['calls'],calls);self.assertEqual(len(t.calls),calls)
    usage=(state/'usage.json').read_bytes()
    with self.assertRaises(r.v.VoiceError):r.run_fixture(state,self.packets,MODELS,funding,prices,**kwargs)
    self.assertEqual((state/'usage.json').read_bytes(),usage);self.assertEqual(len(t.calls),calls)
 def test_emitted_record_feeds_complete_mixed_fixture_not_production(self):
  with tempfile.TemporaryDirectory() as d:
   result,_=self.run_case(Path(d));config={'author_model':MODELS['author'],'reviewer_model':MODELS['reviewer']};solo={}
   for identity,packet in self.current.items():
    if identity in c.ANCHORS:continue
    receipt=r.f.fixture_accept(packet,output(packet),REVIEW,config);receipt['packet_sha256']=r.v.digest(packet);receipt['sha256']=r.v.digest(receipt);solo[identity]=receipt
   original=r.f.receipt_check
   with patch.object(p,'TRUSTED_GROUPED_RUNS',{result['pin']['manifest_sha256']:result['pin']}),patch.object(p,'verify_grouped_provenance',lambda root,packets:p._verify_pinned(root,result['pin'],packets)),patch.object(r.f,'receipt_check',lambda receipt,packet,cfg:original(receipt,packet,cfg,fixture=True)):
    draft=c.compile_admitted_mixed_draft({'solo_v1':{},'solo_v2':solo,'grouped':[result['root']]},config)
    self.assertEqual(len(draft['entries']),736);self.assertEqual(draft['version'],'scarb-mixed-production-draft-1')
   self.assertFalse(p.TRUSTED_GROUPED_RUNS)
if __name__=='__main__':unittest.main()

class ReviewIsolationTests(RunnerTests):
 def test_all_sibling_observations_stable_order_no_acceptance_or_replay(self):
  ids=[x['id'] for x in self.packets]
  for scenario in ['malformed-adverse','favorable-adverse','malformed-favorable']:
   seen=[]
   for reverse in [False,True]:
    with self.subTest(scenario=scenario,reverse=reverse),tempfile.TemporaryDirectory() as d:
     state=Path(d);funding,prices,_=self.inputs(state)
     packets=list(reversed(self.packets)) if reverse else self.packets
     reviews={identity:copy.deepcopy(REVIEW) for identity in ids}
     if scenario.startswith('malformed'):reviews[ids[0]]={'approve':'malformed'}
     if scenario.endswith('adverse'):reviews[ids[1]]['approve']=False
     ar=response({x['id']:output(x) for x in reversed(packets)});ar.update(id='synthetic-author',model=MODELS['author'])
     rr=response({x['id']:reviews[x['id']] for x in reversed(packets)});rr.update(id='synthetic-reviewer',model=MODELS['reviewer'])
     transport=r.f.FixtureTransport([ar,rr]);kwargs=dict(transport=transport,started_at='2026-11-18T03:01:00Z',completed_at='2026-11-18T03:01:05Z')
     with self.assertRaises(r.v.VoiceError):r.run_fixture(state,packets,MODELS,funding,prices,**kwargs)
     root=state/'grouped-runs'/r.v.digest({x['id']:r.v.digest(x) for x in packets})
     diagnostic=r.load(root/'review-diagnostics.json');seen.append(diagnostic['items'])
     self.assertEqual(set(diagnostic['items']),set(ids));self.assertFalse(diagnostic['acceptance_granted'])
     self.assertFalse((root/'fixture-pin.json').exists());self.assertFalse((root/'manifest.json').exists())
     self.assertEqual(r.recover_fixture(state,packets)['status'],'held-adverse' if scenario.endswith('adverse') else 'held-uncertain')
     self.assertEqual(len(transport.calls),2)
     before=(state/'usage.json').read_bytes()
     with self.assertRaises(r.v.VoiceError):r.run_fixture(state,packets,MODELS,funding,prices,**kwargs)
     self.assertEqual(len(transport.calls),2);self.assertEqual((state/'usage.json').read_bytes(),before)
   self.assertEqual(seen[0],seen[1])
