"""Synthetic byte/reader qualification only, never admitted production evidence."""
import copy,json,tempfile,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import scarb_grouped_context_candidate as c
from scripts.scarb_accepted_copy import accepted_resolver

class MixedReleaseBridgeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.current=c.seam.current_canonical_requests();cls.expected={i:c.v.digest(p) for i,p in cls.current.items()}
  cls.group_ids=list(c.ANCHORS)
 def draft(self):
  return {'version':'scarb-mixed-production-draft-1','entries':{i:{'text':p['draft'],'packet_sha256':self.expected[i],'receipt_sha256':'a'*64,'origin':'scarb-grouped-projection-2' if i in self.group_ids else 'openai-api-reviewed'} for i,p in self.current.items()}}
 def compiled(self):
  # Mock only private admission in this synthetic serializer test. The actual
  # production registry remains empty and the real compiler refuses this bundle.
  with patch.object(c,'compile_admitted_mixed_draft',return_value=self.draft()):return c.compile_mixed_catalogue({}, {})
 def js(self,artifact,expected):
  code="import {createScarbAiResolver} from './docs/scarb-ai-copy.mjs';let s='';for await(const c of process.stdin)s+=c;const x=JSON.parse(s);try{const r=createScarbAiResolver(x.a,x.e);console.log(JSON.stringify(Object.fromEntries(Object.keys(x.e).map(k=>[k,r(k)]))));}catch(e){process.exitCode=2;}"
  p=subprocess.run(['node','--input-type=module','-e',code],cwd=c.ROOT,input=json.dumps({'a':artifact,'e':expected}),capture_output=True,text=True,encoding='utf8');return p
 def test_full_synthetic_metadata_and_reader_parity(self):
  a=self.compiled();resolve=accepted_resolver(a,self.expected);js=self.js(a,self.expected)
  self.assertEqual(js.returncode,0,js.stderr);self.assertEqual(json.loads(js.stdout),{i:resolve(i) for i in self.expected})
  for i in self.group_ids:self.assertEqual(a['entries'][i]['provenance']['packet_id'],i)
  self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)
  with self.assertRaises(c.v.VoiceError):c.compile_mixed_catalogue({'solo_v1':{},'solo_v2':{},'grouped':[]},{})
 def test_incomplete_and_tampered_synthetic_inputs_fail_both_readers(self):
  for kind in ['missing','short-manifest','packet','receipt','provenance','cross-item','fixture-origin','old-version']:
   a=self.compiled();e=dict(self.expected);i=self.group_ids[0]
   if kind=='missing':a['entries'].pop(i)
   elif kind=='short-manifest':a['entries'].pop(i);e.pop(i)
   elif kind=='packet':a['entries'][i]['packet_sha256']='b'*64
   elif kind=='receipt':a['entries'][i]['receipt_sha256']='b'*64
   elif kind=='provenance':a['entries'][i]['provenance']['extra']=True
   elif kind=='cross-item':a['entries'][i]['provenance']['packet_id']=self.group_ids[1]
   elif kind=='fixture-origin':a['entries'][i]['origin']='test-fixture-grouped-projection'
   else:a['version']='scarb-ai-voice-1'
   with self.subTest(kind=kind):
    with self.assertRaises(ValueError):accepted_resolver(a,e)
    self.assertEqual(self.js(a,e).returncode,2)
 def test_recompile_verifier_and_original_solo_compatibility(self):
  a=self.compiled()
  with tempfile.TemporaryDirectory() as d,patch.object(c,'compile_admitted_mixed_draft',return_value=self.draft()):
   path=Path(d)/'synthetic-only.json';path.write_text(json.dumps(a),encoding='utf8');self.assertTrue(c.verify_mixed_catalogue({}, {},path))
   a['entries'][self.group_ids[0]]['text']='tampered';path.write_text(json.dumps(a),encoding='utf8')
   with self.assertRaises(c.v.VoiceError):c.verify_mixed_catalogue({}, {},path)
  e={'old':'1'*64};a={'version':'scarb-ai-voice-1','entries':{'old':{'text':'unchanged','origin':'openai-api-reviewed','packet_sha256':'1'*64,'receipt_sha256':'2'*64}}}
  self.assertEqual(accepted_resolver(a,e)('old'),'unchanged');self.assertEqual(self.js(a,e).returncode,0)
 def test_serializer_cannot_shorten_current_manifest(self):
  d=self.draft();d['entries'].pop(self.group_ids[0])
  with patch.object(c,'compile_admitted_mixed_draft',return_value=d),self.assertRaises(c.v.VoiceError):c.compile_mixed_catalogue({}, {})

 def test_actual_private_staging_and_publication_comparison_seam(self):
  from scripts import stage_scarb_ai_inputs as stage
  packets=list(self.current.values());bundle={'solo_v1':{},'solo_v2':{},'grouped':[]}
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);candidate=state/'candidate.json';candidate.write_text(json.dumps(self.compiled()),encoding='utf8')
   # Real registry-empty admission must refuse even plausible complete metadata.
   with self.assertRaises(c.v.VoiceError):stage.stage_inputs(packets,{},state,candidate,state/'refused',authoring_version='v3',mixed_bundle=bundle)
   self.assertFalse((state/'refused').exists())
   with patch.object(c,'compile_admitted_mixed_draft',return_value=self.draft()):
    att=stage.stage_inputs(packets,{},state,candidate,state/'synthetic-stage',authoring_version='v3',mixed_bundle=bundle)
    self.assertEqual(att['authoring_version'],'v3')
    generated=stage.generator_inputs(packets,{},state,candidate,authoring_version='v3',mixed_bundle=bundle)
    publication=state/'synthetic-publication';publication.mkdir()
    mapping={'accepted-copy.json':'scarb-copy-inputs.json','accepted-copy.mjs':'scarb-copy-inputs.mjs','event-inputs.json':'scarb-event-inputs.json','event-inputs.mjs':'scarb-event-inputs.mjs','current-request-manifest.json':'scarb-copy-manifest.json','current-request-manifest.mjs':'scarb-copy-manifest.mjs','event-source.json':'scarb-event-source.json'}
    (publication/'docs').mkdir()
    for name,target in mapping.items():(publication/'docs'/target).write_bytes(generated[name])
    stage.compare_publication(packets,{},state,candidate,publication,authoring_version='v3',mixed_bundle=bundle)
    (publication/'docs/scarb-copy-inputs.json').write_text('{}',encoding='utf8')
    with self.assertRaises(c.v.VoiceError):stage.compare_publication(packets,{},state,candidate,publication,authoring_version='v3',mixed_bundle=bundle)
    with self.assertRaises(c.v.VoiceError):stage.stage_inputs(packets[:-1],{},state,candidate,state/'incomplete',authoring_version='v3',mixed_bundle=bundle)
    a=json.loads(candidate.read_text(encoding='utf8'));a['entries'][self.group_ids[0]]['text']='forged';candidate.write_text(json.dumps(a),encoding='utf8')
    with self.assertRaises(c.v.VoiceError):stage.stage_inputs(packets,{},state,candidate,state/'tampered',authoring_version='v3',mixed_bundle=bundle)
    self.assertFalse((state/'incomplete').exists());self.assertFalse((state/'tampered').exists())
   self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)

 def test_external_private_registry_binding_and_restoration(self):
  import hashlib
  from scripts import stage_scarb_ai_inputs as stage
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);path=state/'synthetic-registry.json'
   pin={k:'a'*64 for k in ['funding_sha256','ledger_before_sha256','manifest_sha256','membership_before_sha256','prices_sha256','runner_sha256','solo_state_sha256','source_context_sha256']}
   pin.update(cost_version=2,expected_purpose='production-grouped-review',membership_version=1,month_cap_nusd=1,packet_bindings={self.group_ids[0]:self.expected[self.group_ids[0]]},requested_models={},reservation_nusd=1,returned_models={},solo_state_root=str(state))
   value={'version':'scarb-private-grouped-registry-1','runs':{'a'*64:pin}}
   def save(x):
    path.write_text(json.dumps(x),encoding='utf8');return hashlib.sha256(path.read_bytes()).hexdigest()
   approved=save(value)
   with patch.object(c.provenance,'verify_grouped_provenance',return_value={}),stage.private_grouped_registry(state,path,approved):
    self.assertEqual(set(c.provenance.TRUSTED_GROUPED_RUNS),{'a'*64})
    # Pin binding alone is not provenance proof or catalogue acceptance.
    with self.assertRaises(c.v.VoiceError):c.compile_mixed_catalogue({'solo_v1':{},'solo_v2':{},'grouped':[]},{})
   self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)
   for kind in ['missing-pin','wrong-pin','tamper','multiple','fixture','extra-field']:
    changed=copy.deepcopy(value);digest=approved
    if kind=='missing-pin':digest=None
    elif kind=='wrong-pin':digest='b'*64
    elif kind=='tamper':changed['version']='tampered'
    elif kind=='multiple':changed['runs']['b'*64]=copy.deepcopy(pin)
    elif kind=='fixture':changed['runs']['a'*64]['expected_purpose']='synthetic-grouped-run'
    else:changed['runs']['a'*64]['unexpected']=True
    actual=save(changed)
    if kind in ['multiple','fixture','extra-field']:digest=actual
    with self.subTest(kind=kind),self.assertRaises(c.v.VoiceError):
     with stage.private_grouped_registry(state,path,digest):self.fail('untrusted grant')
    self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)
   self.assertEqual(set(p.name for p in state.iterdir()),{'synthetic-registry.json'})

 def test_exact_multiple_registry_roster_verifies_all_and_restores(self):
  import hashlib
  from scripts import stage_scarb_ai_inputs as stage
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);path=state/'synthetic-roster.json';runs={}
   for n,identity in enumerate(list(self.current)[:3],1):
    h=str(n)*64
    pin={k:'a'*64 for k in ['funding_sha256','ledger_before_sha256','membership_before_sha256','prices_sha256','runner_sha256','solo_state_sha256','source_context_sha256']}
    pin.update(manifest_sha256=h,cost_version=2,expected_purpose='production-grouped-review',membership_version=1,month_cap_nusd=1,packet_bindings={identity:self.expected[identity]},requested_models={},reservation_nusd=1,returned_models={},solo_state_root=str(state));runs[h]=pin
   value={'version':'scarb-private-grouped-registry-1','runs':runs}
   def save(v):
    path.write_text(json.dumps(v),encoding='utf8');return hashlib.sha256(path.read_bytes()).hexdigest()
   approved=save(value)
   with patch.object(c.provenance,'verify_grouped_provenance',return_value={}) as verify:
    with stage.private_grouped_registry(state,path,approved):self.assertEqual(len(c.provenance.TRUSTED_GROUPED_RUNS),3)
    self.assertEqual(verify.call_count,3)
    for call,pin in zip(verify.call_args_list,runs.values()):self.assertEqual(call.args[0],state.resolve()/'grouped-runs'/c.v.digest(pin['packet_bindings']))
   self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)
   for kind in ['duplicate-member','fixture','unverified','extra','duplicate-json']:
    v=copy.deepcopy(value);keys=list(v['runs'])
    if kind=='duplicate-member':v['runs'][keys[1]]['packet_bindings']=v['runs'][keys[0]]['packet_bindings']
    elif kind=='fixture':v['runs'][keys[1]]['expected_purpose']='synthetic-grouped-run'
    elif kind=='extra':v['runs']['4'*64]=v['runs'][keys[0]]
    digest=save(v)
    if kind=='extra':digest=approved
    if kind=='duplicate-json':
     path.write_text('{"version":"scarb-private-grouped-registry-1","runs":{},"runs":'+json.dumps(runs)+'}',encoding='utf8');digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with self.subTest(kind=kind),patch.object(c.provenance,'verify_grouped_provenance',side_effect=c.v.VoiceError('unverified run')) as verify,self.assertRaises(c.v.VoiceError):
     with stage.private_grouped_registry(state,path,digest):self.fail('bad roster admitted')
    self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)
