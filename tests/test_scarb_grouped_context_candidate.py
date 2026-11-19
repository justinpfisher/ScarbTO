import unittest,json,tempfile
from pathlib import Path
from scripts import scarb_grouped_context_candidate as c
from scripts import scarb_grouped_provenance_candidate as p
class ContextCandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.current=c.seam.current_canonical_requests();cls.packets=[cls.current[i] for i in c.ANCHORS];cls.contexts=c.current_contexts(cls.packets)
 def test_exact_manifest_and_context_in_both_requests(self):
  self.assertEqual(len(self.current),736)
  authors={x['id']:{'slots':{},'tail':x['draft'],'evidence_ids':[e['id'] for e in x['evidence']]} for x in self.packets}
  bodies=c.context_prompts(self.packets,{'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'},self.contexts,authors)
  for body in bodies:self.assertEqual(json.loads(body['input'][0]['content'][0]['text'])['source_context'],self.contexts)
 def test_missing_context_rejected(self):
  with self.assertRaises(c.v.VoiceError):c.context_prompts(self.packets,{'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'},{})
 def test_source_packet_change_rejected(self):
  changed=[dict(self.packets[0],draft='Changed')]
  with self.assertRaises(c.v.VoiceError):c.current_contexts(changed)
 def test_home_results_list_context_preserves_distinct_runtime_states_and_locks(self):
  ids=['static.app-38','static.app-39','static.app-40']
  contexts=c.current_contexts([self.current[i] for i in ids])
  self.assertEqual(set(c.HOME_LIST_STATES),set(ids))
  self.assertEqual(set(contexts),set(ids))
  for identity,lock,meaning in zip(ids,('Scarb.TO','DineSafe','Scarborough'),('Loading before','No checked snapshot','no records match')):
   self.assertEqual(contexts[identity]['locks'],{'VALUE_0':lock})
   self.assertEqual(contexts[identity]['consumer'],'renderList/record-list')
   self.assertIn(meaning,contexts[identity]['meaning'])
  self.assertEqual(c.current_contexts(self.packets),self.contexts)
 def test_home_results_list_rejects_source_drift_packet_drift_and_unsupported_state(self):
  from unittest.mock import patch
  item=self.current['static.app-38']; read=Path.read_bytes
  with patch.object(Path,'read_bytes',lambda path:read(path)+(b' ' if path.name=='app.mjs' else b'')):
   with self.assertRaisesRegex(c.v.VoiceError,'producer or accessible region changed'):
    c.home_list_context(item)
  with self.assertRaisesRegex(c.v.VoiceError,'packet or factual lock changed'):
   c.home_list_context(dict(item,locks={}))
  with self.assertRaisesRegex(c.v.VoiceError,'Unsupported homepage results-list state'):
   c.home_list_context(self.current['static.app-41'])
 def test_missing_full_catalogue_rejected(self):
  with self.assertRaisesRegex(c.v.VoiceError,'736'):c.compile_admitted_mixed_draft({'solo_v1':{},'solo_v2':{},'grouped':[]},{})
 def test_unadmitted_run_refused(self):
  self.assertEqual(dict(p.TRUSTED_GROUPED_RUNS),{})
  with tempfile.TemporaryDirectory() as d:
   (Path(d)/'manifest.json').write_text('{}')
   with self.assertRaisesRegex(c.v.VoiceError,'No admitted'):c.compile_admitted_mixed_draft({'solo_v1':{},'solo_v2':{},'grouped':[d]}, {})
if __name__=='__main__':unittest.main()

from tests.test_scarb_grouped_provenance import ProvenanceTests
from tests.test_scarb_ai_voice import response,REVIEW
class ContextProvenanceTests(ProvenanceTests):
 def setUp(self):
  super().setUp()
  current=c.seam.current_canonical_requests();self.p=[current[i] for i in c.ANCHORS];contexts=c.current_contexts(self.p)
  authors={x['id']:{'slots':{},'tail':x['draft'],'evidence_ids':[e['id'] for e in x['evidence']]} for x in self.p}
  a,r=c.context_prompts(self.p,self.models,contexts,authors);ar=response(authors);rr=response({x['id']:REVIEW for x in self.p})
  ar.update(id='context-author',model=self.models['author']);rr.update(id='context-reviewer',model=self.models['reviewer'])
  self.env.update(version='scarb-grouped-run-envelope-2',packets=self.p,source_context=contexts,author_request=a,review_request=r,author_response=ar,review_response=rr)
  bindings={x['id']:c.v.digest(x) for x in self.p};self.pin.update(packet_bindings=bindings,source_context_sha256=c.v.digest(contexts));self.journal['packet_bindings']=bindings
  self.journal['stages']=[]
  for role,req,res in [('author',a,ar),('reviewer',r,rr)]:
   _,usage=c.v.unpack(res);self.journal['stages'].append({'role':role,'request_sha256':c.v.digest(req),'response_sha256':c.v.digest(res),'response_id':res['id'],'model':res['model'],'usage':usage})
  self.seal.update(packet_bindings=bindings,envelope_sha256=c.v.digest(self.env),journal_sha256=c.v.digest(self.journal));self.cost_records();self.sync()
 def test_missing_or_changed_bound_context(self):
  self.assertEqual(self.verify()['packet_bindings'],self.pin['packet_bindings'])
  self.env['source_context']={};self.cost_records();self.sync()
  with self.assertRaises(c.v.VoiceError):self.verify()
 def cost_records(self):
  super().cost_records()
  if self.env.get('version')!='scarb-grouped-run-envelope-2':return
  from scripts.scarb_grouped_membership_candidate import reserve
  before={'reserved_nusd':0,'consumed_batches':{},'packet_membership':{}}
  after=reserve(before,self.pin['packet_bindings'],self.pin['reservation_nusd'],{})
  self.extra.update({'ledger-before.json':before,'ledger-after.json':after,'solo-state.json':{}})
  self.pin.update(membership_version=1,solo_state_sha256=c.v.digest({}),ledger_before_sha256=c.v.digest(before))
  budget=self.extra['budget.json'];budget.update(ledger_before_sha256=c.v.digest(before),ledger_after_sha256=c.v.digest(after))
  self.seal.update(budget_sha256=c.v.digest(budget),ledger_after_sha256=c.v.digest(after),packet_membership_sha256=c.v.digest(after['packet_membership']),solo_state_sha256=c.v.digest({}))
 def test_membership_rehashed_mismatch_refused(self):
  self.extra['ledger-after.json']['packet_membership']={}
  self.extra['budget.json']['ledger_after_sha256']=c.v.digest(self.extra['ledger-after.json'])
  self.sync()
  with self.assertRaises(c.v.VoiceError):self.verify()
