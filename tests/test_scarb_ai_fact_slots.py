import copy,json,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from scripts import scarb_ai_voice as v,scarb_ai_fact_slots as f
from tests.test_scarb_ai_voice import CONFIG,REVIEW,NOW,response,ENV
P={'id':'fixture.fact-slots-distinct','surface':'source-note','kind':'safety','draft':'{{LOCK:SOURCE}} recorded {{LOCK:RESULT}}. {{LOCK:CAUTION}}','locks':{'SOURCE':'Fixture source','RESULT':'Pass','CAUTION':'A dated record is not a guarantee of current conditions.'},'evidence':[{'id':'synthetic-only','source':'repo:fixture','sha256':'a'*64,'fact':'Synthetic status and caution, no live record.'}],'limits':{'words':100,'characters':1000}}
def output():return {'slots':{'SOURCE':{'rank':0,'before':''},'RESULT':{'rank':1,'before':' recorded '},'CAUTION':{'rank':2,'before':'. '}},'tail':'','evidence_ids':['synthetic-only']}
class FactSlotsTests(unittest.TestCase):
 def test_exact_schema_required_keys_and_v1_cache_unchanged(self):
  before=v.cache_key(P,CONFIG);s=f.schema(P)
  self.assertEqual(set(s['properties']['slots']['required']),set(P['locks']))
  self.assertFalse(s['additionalProperties']);self.assertNotEqual(f.cache_key(P,CONFIG),before)
  self.assertEqual(v.cache_key(P,CONFIG),before)
 def test_flexible_prose_same_protected_values_and_full_review(self):
  a=output();b=output();b['slots']['SOURCE']['before']='In the ';b['slots']['RESULT']['before']=' record, the result is '
  self.assertNotEqual(f.assemble(P,a),f.assemble(P,b))
  for x in [a,b]:
   witness=f.fixture_accept(P,x,REVIEW,CONFIG);self.assertEqual(witness['origin'],'test-fixture')
   self.assertEqual(sorted(v.TOKEN.findall(witness['writer']['body'])),sorted(P['locks']))
   request=f.review_request(P,x,CONFIG);data=json.loads(request['input'][0]['content'][0]['text'])
   self.assertEqual(data['candidate'],witness['writer']);self.assertEqual(data['materialised_text'],witness['text'])
 def test_missing_unknown_duplicate_rank_type_and_prose_injection_rejected(self):
  for mutation in ['missing','unknown','duplicate','negative','bool','token','digit','url','markup','evidence','oversize']:
   x=output()
   if mutation=='missing':del x['slots']['CAUTION']
   elif mutation=='unknown':x['slots']['OTHER']={'rank':3,'before':''}
   elif mutation=='duplicate':x['slots']['CAUTION']['rank']=0
   elif mutation=='negative':x['slots']['CAUTION']['rank']=-1
   elif mutation=='bool':x['slots']['CAUTION']['rank']=True
   elif mutation=='evidence':x['evidence_ids']=[]
   else:x['tail']={'token':'{{LOCK:SOURCE}}','digit':' 123','url':' https://example.invalid','markup':' <b>','oversize':'x'*24001}[mutation]
   with self.subTest(mutation=mutation),self.assertRaises(v.VoiceError):f.assemble(P,x)
 def test_separate_rejection_and_expanded_limits_remain_required(self):
  with self.assertRaises(v.VoiceError):f.fixture_accept(P,output(),{**REVIEW,'approve':False},CONFIG)
  draft=v.text_check(P,{'body':P['draft'],'evidence_ids':['synthetic-only']})
  for limits in [{'words':len(draft.split()),'characters':1000},{'words':100,'characters':len(draft)}]:
   packet={**P,'limits':limits};v.packet_check(packet)
   candidate=output();candidate['tail']=' Additional harmless connective prose.'
   with self.assertRaises(v.VoiceError):f.assemble(packet,candidate)
 def test_order_can_change_without_duplicate_facts(self):
  x=output();x['slots']['CAUTION']={'rank':0,'before':''};x['slots']['SOURCE']={'rank':1,'before':' '};x['slots']['RESULT']={'rank':2,'before':' recorded '};x['tail']='.'
  self.assertTrue(f.assemble(P,x)['body'].startswith('{{LOCK:CAUTION}}'))

 def test_no_fact_and_boundary_whitespace(self):
  packet={**P,'draft':'Open details','locks':{}}
  self.assertEqual(f.assemble(packet,{'slots':{},'tail':'View details','evidence_ids':['synthetic-only']})['body'],'View details')
  packet={**P,'draft':'{{LOCK:LAYOUT_PREFIX}}Details{{LOCK:LAYOUT_SUFFIX}}','locks':{'LAYOUT_PREFIX':'\n','LAYOUT_SUFFIX':' '}}
  result={'slots':{'LAYOUT_PREFIX':{'rank':0,'before':''},'LAYOUT_SUFFIX':{'rank':1,'before':'View details'}},'tail':'','evidence_ids':['synthetic-only']}
  self.assertEqual(v.text_check(packet,f.assemble(packet,result)),'\nView details ')
  result['tail']='wrong'
  with self.assertRaises(v.VoiceError):f.assemble(packet,result)
 def test_fixture_dispatch_receipt_cache_and_v1_hold(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);transport=f.FixtureTransport([response(output()),response(REVIEW)])
   receipt=f.generate_fixture(P,CONFIG,state,transport=transport,now=NOW)
   self.assertEqual(len(transport.calls),2);self.assertEqual(f.fixture_receipt_check(receipt,P,CONFIG),receipt['text'])
   cached=f.FixtureTransport([]);self.assertEqual(f.generate_fixture(P,CONFIG,state,transport=cached,now=NOW),receipt);self.assertEqual(cached.calls,[])
   bad=copy.deepcopy(receipt);bad['slot_output']['tail']=' changed';bad['sha256']=v.digest({k:x for k,x in bad.items() if k!='sha256'})
   with self.assertRaises(v.VoiceError):f.fixture_receipt_check(bad,P,CONFIG)
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);old=state/'held'/(v.cache_key(P,CONFIG)+'.json');v.atomic_json(old,{'status':'held'});before=old.read_bytes()
   with self.assertRaises(v.VoiceError):f.generate_fixture(P,CONFIG,state,transport=f.FixtureTransport([]),now=NOW)
   self.assertEqual(old.read_bytes(),before);self.assertFalse((state/'usage.json').exists())
 def test_rejection_hold_budget_and_funding_no_retry(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);transport=f.FixtureTransport([response(output()),response({**REVIEW,'approve':False})])
   with self.assertRaises(v.VoiceError):f.generate_fixture(P,CONFIG,state,transport=transport,now=NOW)
   ledger=(state/'usage.json').read_bytes();self.assertEqual(len(transport.calls),2)
   with self.assertRaises(v.VoiceError):f.generate_fixture(P,CONFIG,state,transport=f.FixtureTransport([]),now=NOW)
   self.assertEqual((state/'usage.json').read_bytes(),ledger)
  for cfg in [{**CONFIG,'enabled':False},{**CONFIG,'month_cap_usd':0.001}]:
   with tempfile.TemporaryDirectory() as d:
    transport=f.FixtureTransport([])
    with self.assertRaises(v.VoiceError):f.generate_fixture(P,cfg,Path(d),transport=transport,now=NOW)
    self.assertEqual(transport.calls,[])

 def test_production_route_default_off_and_mocked_private_bridge(self):
  from scripts.stage_scarb_ai_inputs import generator_inputs
  with tempfile.TemporaryDirectory() as d,patch.object(v,'api_request') as api,patch('scripts.scarb_packet_consumption_candidate.protected_root',lambda:Path(d)):
   state=Path(d)
   with self.assertRaises(v.VoiceError):f.generate(P,CONFIG,state,env=ENV,now=NOW)
   with self.assertRaises(v.VoiceError):f.generate(P,CONFIG,state,enable_v2=True,env=ENV,now=NOW)
   api.assert_not_called();api.side_effect=[response(output()),response(REVIEW)]
   receipt=f.generate(P,CONFIG,state,enable_v2=True,approved_packet_sha256=[v.digest(P)],env=ENV,now=NOW)
   self.assertEqual(api.call_count,2);self.assertEqual(f.receipt_check(receipt,P,CONFIG),receipt['text'])
   public=f.compile_catalogue([P],CONFIG,state);candidate=state/'candidate.json';v.atomic_json(candidate,public)
   files=generator_inputs([P],CONFIG,state,candidate,authoring_version='v2')
   self.assertEqual(json.loads(files['accepted-copy.json']),public)
   self.assertEqual(json.loads(files['private-input-attestation.json'])['authoring_version'],'v2')
   altered=copy.deepcopy(public);altered['entries'][P['id']]['text']+=' tampered';v.atomic_json(candidate,altered)
   with self.assertRaises(v.VoiceError):generator_inputs([P],CONFIG,state,candidate,authoring_version='v2')
 def test_live_mock_failure_holds_and_fixture_cannot_compile(self):
  with tempfile.TemporaryDirectory() as d,patch.object(v,'api_request',return_value=response({'invalid':True})) as api,patch('scripts.scarb_packet_consumption_candidate.protected_root',lambda:Path(d)):
   state=Path(d)
   for _ in range(2):
    with self.assertRaises(v.VoiceError):f.generate(P,CONFIG,state,enable_v2=True,approved_packet_sha256=[v.digest(P)],env=ENV,now=NOW)
   self.assertEqual(api.call_count,1)
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);r=f.generate_fixture(P,CONFIG,state,transport=f.FixtureTransport([response(output()),response(REVIEW)]),now=NOW)
   v.atomic_json(state/'accepted-v2'/(r['key']+'.json'),r)
   with self.assertRaises(v.VoiceError):f.compile_catalogue([P],CONFIG,state)

 def test_finite_transport_and_validation_journals(self):
  for replies,stage,received,count,usage_count in [
   ([TimeoutError('FAKE_SECRET')],'author-request',False,1,0),
   ([response({'bad':'FAKE_SECRET'})],'author-validation',True,1,1),
   ([response(output()),response({**REVIEW,'approve':False})],'review-validation',True,2,2)]:
   with self.subTest(stage=stage),tempfile.TemporaryDirectory() as d:
    state=Path(d)
    with self.assertRaises((v.VoiceError,TimeoutError)):f.generate_fixture(P,CONFIG,state,transport=f.FixtureTransport(replies),now=NOW)
    journal=json.loads(next((state/'held').glob('*.json')).read_text())
    self.assertEqual(journal['stage'],stage);self.assertEqual(journal['response_received'],received)
    self.assertEqual(journal['transport_attempts'],count);self.assertEqual(len(journal['completed_usage_stages']),usage_count)
    self.assertNotIn('FAKE_SECRET',json.dumps(journal))
    for usage in journal['completed_usage_stages']:
     self.assertEqual(set(usage),{'stage','model','input_tokens','output_tokens'})


 def test_v2_paid_eligibility_refuses_other_packets_before_transport(self):
  cfg=copy.deepcopy(CONFIG);cfg['funding']['billing_mode']='prepaid_cutoff_not_guaranteed'
  with tempfile.TemporaryDirectory() as d,patch.object(v,'api_request') as api,patch('scripts.scarb_packet_consumption_candidate.protected_root',lambda:Path(d)):
   with self.assertRaisesRegex(v.VoiceError,'separately scoped'):
    f.generate(P,cfg,Path(d),enable_v2=True,approved_packet_sha256=[v.digest(P)],env=ENV,now=NOW)
   api.assert_not_called()
  self.assertEqual(f.QUALIFICATION_PACKET_SHA256,'d17d1dc701dfaf10f04144afab0b7f2cfe2c61d549a2e9036220a9a20c10de1a')

 def test_v2_refuses_both_original_held_packet_hashes(self):
  cfg=copy.deepcopy(CONFIG);cfg['funding']['billing_mode']='prepaid_cutoff_not_guaranteed'
  for old in ['d1ee00949d7848b8046873c82dcd4490ef73f0b64b8bb2b8a204b435131c8fc0','e8f8d7fda9aa2749b15acaf4450a988b9b29882b04fabd194168bce6f5b6fd18']:
   with tempfile.TemporaryDirectory() as d,patch.object(v,'digest',return_value=old),patch.object(v,'api_request') as api:
    with self.assertRaisesRegex(v.VoiceError,'sealed prior attempt'):f.generate(P,cfg,Path(d),enable_v2=True,approved_packet_sha256=[old],env=ENV,now=NOW)
    api.assert_not_called();self.assertFalse((Path(d)/'usage.json').exists())

 def test_review_dimensions_no_issue_text_or_nonboolean_values(self):
  self.assertEqual(f.review_dimensions({**REVIEW,'voice_pass':False,'approve':False,'issues':['FAKE_SECRET']}),{'schema_valid':True,'approve':False,'meaning_preserved':True,'limitations_preserved':True,'voice_pass':False,'issues_present':True})
  for result in [{**REVIEW,'approve':1},{**REVIEW,'issues':[{'secret':'FAKE_SECRET'}]},{'body':'FAKE_SECRET'}]:
   self.assertEqual(f.review_dimensions(result),{'schema_valid':False})
  with tempfile.TemporaryDirectory() as d:
   state=Path(d)
   with self.assertRaises(v.VoiceError):f.generate_fixture(P,CONFIG,state,transport=f.FixtureTransport([response(output()),response({**REVIEW,'voice_pass':False,'approve':False,'issues':['FAKE_SECRET']})]),now=NOW)
   held=json.loads(next((state/'held').glob('*.json')).read_text())
   self.assertFalse(held['review_dimensions']['voice_pass']);self.assertNotIn('FAKE_SECRET',json.dumps(held))
 def test_all_three_actual_digests_stay_sealed_across_contract_changes(self):
  self.assertEqual(len(f.SEALED_PACKET_SHA256),3)
  for digest in f.SEALED_PACKET_SHA256:
   for change in [{'VERSION':'future-version'},{'AUTHOR':'different prompt'},{'REVIEWER':'different review prompt'}]:
    with self.subTest(digest=digest,change=change),tempfile.TemporaryDirectory() as d,patch.multiple(f,**change),patch.object(v,'digest',return_value=digest):
     transport=f.FixtureTransport([])
     with self.assertRaisesRegex(v.VoiceError,'sealed prior attempt'):f.generate_fixture(P,CONFIG,Path(d),transport=transport,now=NOW)
     self.assertEqual(transport.calls,[]);self.assertFalse((Path(d)/'usage.json').exists())
   with tempfile.TemporaryDirectory() as d,patch.object(f,'schema',return_value={'type':'object','changed':True}),patch.object(v,'digest',return_value=digest):
    transport=f.FixtureTransport([])
    with self.assertRaisesRegex(v.VoiceError,'sealed prior attempt'):f.generate_fixture(P,CONFIG,Path(d),transport=transport,now=NOW)
    self.assertEqual(transport.calls,[])
