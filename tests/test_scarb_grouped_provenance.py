import unittest,tempfile,json,copy
from pathlib import Path
from scripts import scarb_grouped_provenance_candidate as provenance
from scripts import scarb_grouped_fixture_envelope as group
from tests.test_scarb_ai_voice import response,REVIEW
v=group.v
class ProvenanceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.addCleanup(self.tmp.cleanup)
  fact='Synthetic browse-only collection';self.p=[{'id':'diagnostic.provenance.fixture','surface':'home','kind':'functional','draft':'Browse sample','locks':{},'evidence':[{'id':'fixture.source','source':'repo:diagnostic/provenance','sha256':v.digest(fact),'fact':fact}],'limits':{'words':10,'characters':100}}]
  self.models={'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'};authors={self.p[0]['id']:{'slots':{},'tail':'Browse sample','evidence_ids':['fixture.source']}};reviews={self.p[0]['id']:REVIEW}
  a,r=group.prompts(self.p,self.models,authors);ar=response(authors);rr=response(reviews);ar.update(id='fixture-author',model=self.models['author']);rr.update(id='fixture-reviewer',model=self.models['reviewer'])
  self.env={'version':'scarb-grouped-run-envelope-1','packets':self.p,'models':self.models,'author_request':a,'review_request':r,'author_response':ar,'review_response':rr}
  bindings={p['id']:v.digest(p) for p in self.p};stages=[]
  for role,req,res in [('author',a,ar),('reviewer',r,rr)]:
   _,usage=v.unpack(res);stages.append({'role':role,'request_sha256':v.digest(req),'response_sha256':v.digest(res),'response_id':res['id'],'model':res['model'],'usage':usage})
  self.journal={'version':'scarb-grouped-execution-journal-1','status':'completed','calls':2,'packet_bindings':bindings,'stages':stages,'started_at':'2026-11-18T03:00:00Z','completed_at':'2026-11-18T03:00:05Z'}
  self.seal={'version':'scarb-grouped-consumed-seal-1','status':'consumed-completed','packet_bindings':bindings,'envelope_sha256':v.digest(self.env),'journal_sha256':v.digest(self.journal)}
  self.manifest={'version':'scarb-grouped-run-manifest-1','purpose':'production-grouped-review','runner_sha256':'a'*64,'files':{}}
  self.pin={'manifest_sha256':'','runner_sha256':'a'*64,'packet_bindings':bindings,'requested_models':self.models,'returned_models':self.models};self.cost_records();self.sync()
 def cost_records(self):
  funding={'observed_at':'2026-11-18T02:45:00Z','expires_at':'2026-11-18T03:40:00Z','balance_nusd':67_000_000_000,'auto_recharge_disabled':True,'organization':'fixture-org','project':'fixture-project','cap_nusd':1_000_000_000}
  prices={'gpt-6-luna':{'input_nusd_per_million':100_000_000,'output_nusd_per_million':500_000_000},'gpt-6.1-terra':{'input_nusd_per_million':1_000_000_000,'output_nusd_per_million':5_000_000_000}}
  def cost(model,i,o):return (i*prices[model]['input_nusd_per_million']+o*prices[model]['output_nusd_per_million']+999999)//1000000
  bounds={'author':len(v.encoded(self.env['author_request'])),'reviewer':48000};outputs={'author':2000,'reviewer':2000}
  reserve=sum(cost(self.models[r],bounds[r],outputs[r]) for r in bounds);actual=sum(cost(self.models[s['role']],s['usage']['input_tokens'],s['usage']['output_tokens']) for s in self.journal['stages'])
  before={'reserved_nusd':0,'consumed_batches':{}};after={'reserved_nusd':reserve,'consumed_batches':{v.digest(self.pin['packet_bindings']):reserve}}
  budget={'version':'scarb-grouped-cost-proof-1','reservation_nusd':reserve,'actual_usage_cost_nusd':actual,'input_bounds':bounds,'output_bounds':outputs,'funding_sha256':v.digest(funding),'prices_sha256':v.digest(prices),'ledger_before_sha256':v.digest(before),'ledger_after_sha256':v.digest(after)}
  self.extra={'funding.json':funding,'prices.json':prices,'budget.json':budget,'ledger-before.json':before,'ledger-after.json':after}
  self.pin.update(funding_sha256=v.digest(funding),prices_sha256=v.digest(prices),ledger_before_sha256=v.digest(before),reservation_nusd=reserve)
  self.seal.update(budget_sha256=v.digest(budget),ledger_after_sha256=v.digest(after))
 def sync(self):
  for name,record in [('envelope.json',self.env),('journal.json',self.journal),('seal.json',self.seal),*self.extra.items()]:
   (self.root/name).write_bytes(v.encoded(record));self.manifest['files'][name]=provenance.file_hash(self.root/name)
  (self.root/'manifest.json').write_bytes(v.encoded(self.manifest));self.pin['manifest_sha256']=provenance.file_hash(self.root/'manifest.json')
 def verify(self):return provenance._verify_pinned(self.root,self.pin,self.p)
 def test_structure_only_can_verify_but_public_admission_disabled(self):
  self.assertEqual(self.verify()['packet_bindings'],self.pin['packet_bindings'])
  self.assertEqual(provenance.TRUSTED_GROUPED_RUNS,{})
  with self.assertRaises(v.VoiceError):provenance.verify_grouped_provenance(self.root,self.p)
 def test_changed_file_without_external_pin_fails(self):
  (self.root/'journal.json').write_text('{}')
  with self.assertRaises(v.VoiceError):self.verify()
 def test_fixture_and_diagnostic_purposes_rejected(self):
  for purpose in ['fixture','diagnostic-only']:
   self.manifest['purpose']=purpose;self.cost_records();self.sync()
   with self.assertRaises(v.VoiceError):self.verify()
 def test_exact_current_packet_and_model_scope(self):
  changed=copy.deepcopy(self.p);changed[0]['draft']='Altered'
  with self.assertRaises(v.VoiceError):provenance._verify_pinned(self.root,self.pin,changed)
  self.pin['requested_models']={'author':'gpt-6-luna','reviewer':'gpt-6-luna'}
  with self.assertRaises(v.VoiceError):self.verify()
 def test_returned_model_not_requested_label_rejected(self):
  self.env['review_response']['model']='unqualified-model';self.cost_records();self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
 def test_prompt_or_schema_substitution_rejected(self):
  self.env['review_request']['instructions']='Skip challenge';self.cost_records();self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
 def test_journal_usage_and_missing_seal_rejected(self):
  self.journal['stages'][0]['usage']['input_tokens']+=1;self.cost_records();self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
  (self.root/'seal.json').unlink()
  with self.assertRaises(v.VoiceError):self.verify()
 def test_solo_v2_origin_not_relabelled(self):
  self.env['version']=group.f.VERSION;self.cost_records();self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
 def test_missing_cost_proof_rejected(self):
  (self.root/'budget.json').unlink()
  with self.assertRaises(v.VoiceError):self.verify()
 def test_mismatched_cost_and_float_representation_rejected(self):
  for value in [self.extra['budget.json']['actual_usage_cost_nusd']+1,float(self.extra['budget.json']['actual_usage_cost_nusd'])]:
   self.extra['budget.json']['actual_usage_cost_nusd']=value;self.seal['budget_sha256']=v.digest(self.extra['budget.json']);self.sync()
   with self.assertRaises(v.VoiceError):self.verify()
 def test_refund_not_permitted_even_with_rehashed_records(self):
  after=self.extra['ledger-after.json'];after['reserved_nusd']-=1
  key=next(iter(after['consumed_batches']));after['consumed_batches'][key]-=1
  self.extra['budget.json']['ledger_after_sha256']=v.digest(after);self.seal.update(ledger_after_sha256=v.digest(after),budget_sha256=v.digest(self.extra['budget.json']));self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
 def test_stale_observation_or_overbudget_rejected(self):
  funding=self.extra['funding.json'];funding['observed_at']='2026-11-17T02:00:00Z'
  self.pin['funding_sha256']=v.digest(funding);self.extra['budget.json']['funding_sha256']=v.digest(funding);self.seal['budget_sha256']=v.digest(self.extra['budget.json']);self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
  funding['observed_at']='2026-11-18T02:45:00Z';funding['cap_nusd']=1
  self.pin['funding_sha256']=v.digest(funding);self.extra['budget.json']['funding_sha256']=v.digest(funding);self.seal['budget_sha256']=v.digest(self.extra['budget.json']);self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
 def test_uncertain_run_and_over_output_reservation_rejected(self):
  self.journal['status']='outcome-uncertain';self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
  self.journal['status']='completed';self.env['review_response']['usage']['output_tokens']=2001;self.sync()
  with self.assertRaises(v.VoiceError):self.verify()
if __name__=='__main__':unittest.main()


