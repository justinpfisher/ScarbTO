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

class CanonicalFixedWordingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from scripts import scarb_fixed_wording_candidate as fixed
  from scripts.scarb_accepted_copy import fixed_wording_pins
  cls.fixed=fixed
  cls.current=c.seam.current_canonical_requests()
  cls.expected={identity:c.v.digest(packet) for identity,packet in cls.current.items()}
  cls.pins=fixed_wording_pins()
  cls.records={identity:{'version':'scarb-fixed-wording-review-1','decision':'verified-unchanged',
                        'binding':fixed.exact_binding(cls.current[identity])} for identity in cls.pins}
  all_shells=json.loads((c.ROOT/'config/scarb-static-shells.json').read_bytes())
  cls.shells={path:all_shells[path] for path in ('docs/index.html','docs/community/index.html')}
  drafts={slot['id']:slot['draft'] for record in cls.shells.values() for slot in record['slots']}
  cls.editorial={identity:{'text':drafts.get(identity,packet['draft']),'packet_sha256':cls.expected[identity],
                            'receipt_sha256':'a'*64,'origin':'openai-api-reviewed'}
                 for identity,packet in cls.current.items() if identity not in cls.pins}

 def setUp(self):
  from scripts import scarb_packet_consumption_candidate as history
  temp=tempfile.TemporaryDirectory()
  self.addCleanup(temp.cleanup)
  self.state=Path(temp.name).resolve()
  self.enterContext(patch.object(history,'protected_root',return_value=self.state))
  self.bundle={'solo_v1':{},'solo_v2':{},'grouped':[],'fixed_records':self.records}

 def compile(self,*,editorial=None,bundle=None):
  with patch.object(c,'_collect_admitted_editorial_entries',return_value=self.editorial if editorial is None else editorial):
   return c.compile_mixed_catalogue(self.bundle if bundle is None else bundle,{},state=self.state)

 def test_private_verifier_and_staging_preserve_both_fixed_shells(self):
  from scripts import stage_scarb_ai_inputs as stage
  catalogue=self.compile()
  self.assertEqual(catalogue['version'],'scarb-ai-voice-mixed-2')
  self.assertEqual(len(catalogue['entries']),736)
  self.assertEqual({key for key,value in catalogue['entries'].items()
                    if value['origin']=='scarb-fixed-wording-review-1'},set(self.pins))
  candidate=self.state/'candidate.json'
  candidate.write_bytes(c.v.encoded(catalogue))
  with patch.object(c,'_collect_admitted_editorial_entries',return_value=self.editorial):
   files=stage.generator_inputs(list(self.current.values()),{},self.state,candidate,shells=self.shells,
                                authoring_version='v3',mixed_bundle=self.bundle)
  self.assertEqual(json.loads(files['accepted-copy.json']),catalogue)
  self.assertFalse((self.state/'generation.lock').exists())
  for path,record in self.shells.items():
   self.assertEqual(files[path],record['source'].encode())
   self.assertEqual(files[path],(c.ROOT/path).read_bytes().replace(b'\r\n',b'\n'))
  read=accepted_resolver(catalogue,self.expected)
  js=MixedReleaseBridgeTests.js(self,catalogue,self.expected)
  self.assertEqual(js.returncode,0,js.stderr)
  self.assertEqual(json.loads(js.stdout),{key:read(key) for key in self.expected})

 def test_incomplete_overlap_stale_and_widened_fixed_bundle_fails(self):
  fixed_key=next(iter(self.pins))
  outside=next(iter(self.editorial))
  for case in ('incomplete','overlap','review-drift','off-scope'):
   editorial=copy.deepcopy(self.editorial)
   records=copy.deepcopy(self.records)
   if case=='incomplete':editorial.pop(outside)
   elif case=='overlap':editorial[fixed_key]=editorial[outside]
   elif case=='review-drift':records[fixed_key]['binding']['text']+=' altered'
   else:
    # Total membership still matches the full manifest, but the fixed lane changed.
    records[outside]=records.pop(fixed_key)
    editorial[fixed_key]=editorial.pop(outside)
   with self.subTest(case=case),self.assertRaises(c.v.VoiceError):
    self.compile(editorial=editorial,bundle={**self.bundle,'fixed_records':records})
  changed=copy.deepcopy(self.current)
  changed[fixed_key]['draft']+=' drift'
  with patch.object(c.seam,'current_canonical_requests',return_value=changed),self.assertRaisesRegex(c.v.VoiceError,'packet or review map'):
   self.compile()
  accepted=self.state/'accepted-v2'
  accepted.mkdir()
  (accepted/'already-consumed.json').write_bytes(c.v.encoded({'packet_sha256':self.expected[fixed_key]}))
  with self.assertRaisesRegex(c.v.VoiceError,'prior attempt'):
   self.compile()
  self.assertFalse((self.state/'generation.lock').exists())

 def test_both_readers_reject_forged_fixed_claims(self):
  catalogue=self.compile()
  identity=next(iter(self.pins))
  outside=next(iter(self.editorial))
  for issue in ('text','review','relabel','unknown','legacy-version','missing'):
   altered=copy.deepcopy(catalogue)
   entry=altered['entries'][identity]
   if issue=='text':entry['text']+=' forged'
   elif issue=='review':entry['receipt_sha256']='f'*64
   elif issue=='relabel':entry['origin']='openai-api-reviewed'
   elif issue=='unknown':altered['entries'][outside]['origin']='scarb-fixed-wording-review-1'
   elif issue=='legacy-version':altered['version']='scarb-ai-voice-mixed-1'
   else:altered['entries'].pop(identity)
   with self.subTest(issue=issue):
    with self.assertRaises(ValueError):accepted_resolver(altered,self.expected)
    self.assertEqual(MixedReleaseBridgeTests.js(self,altered,self.expected).returncode,2)


 def directory_bundle(self):
  from scripts.scarb_accepted_copy import fixed_directory_pins
  directory_pins=fixed_directory_pins()
  records={**self.records,**{
   identity:{'version':'scarb-fixed-wording-review-1','decision':'verified-unchanged',
             'binding':self.fixed.exact_binding(self.current[identity])}
   for identity in directory_pins}}
  directory=self.fixed.DIRECTORY
  shell=json.loads((c.ROOT/'config/scarb-static-shells.json').read_bytes())[directory]
  editorial={key:{**entry} for key,entry in self.editorial.items() if key not in directory_pins}
  for slot in shell['slots']:
   if slot['id'] in editorial:
    editorial[slot['id']]['text']=slot['draft']
  intro='static.directory-intro'
  editorial[intro]['text']=self.current[intro]['evidence'][0]['fact']
  return {**self.bundle,'fixed_records':records},editorial,shell,directory_pins

 def test_directory_transition_stages_exact_current_source_in_both_readers(self):
  from scripts import stage_scarb_ai_inputs as stage
  bundle,editorial,shell,pins=self.directory_bundle()
  self.assertEqual(set(pins),set(self.fixed.DIRECTORY_WORDING))
  catalogue=self.compile(editorial=editorial,bundle=bundle)
  self.assertEqual(catalogue['version'],'scarb-ai-voice-mixed-3')
  self.assertEqual(len(catalogue['entries']),736)
  self.assertEqual({key for key,value in catalogue['entries'].items()
                    if value['origin']=='scarb-fixed-wording-review-1'},set(self.pins)|set(pins))
  candidate=self.state/'candidate.json'
  candidate.write_bytes(c.v.encoded(catalogue))
  directory=self.fixed.DIRECTORY
  with patch.object(c,'_collect_admitted_editorial_entries',return_value=editorial):
   files=stage.generator_inputs(list(self.current.values()),{},self.state,candidate,shells={directory:shell},
                                authoring_version='v3',mixed_bundle=bundle)
  self.assertEqual(json.loads(files['accepted-copy.json']),catalogue)
  self.assertEqual(files[directory],(c.ROOT/directory).read_bytes().replace(b'\r\n',b'\n'))
  self.assertFalse((self.state/'generation.lock').exists())
  read=accepted_resolver(catalogue,self.expected)
  js=MixedReleaseBridgeTests.js(self,catalogue,self.expected)
  self.assertEqual(js.returncode,0,js.stderr)
  self.assertEqual(json.loads(js.stdout),{key:read(key) for key in self.expected})
  self.assertEqual(catalogue['entries']['static.directory-intro']['origin'],'openai-api-reviewed')

 def test_directory_transition_rejects_changed_evidence_overlap_and_version(self):
  bundle,editorial,_,pins=self.directory_bundle()
  identity=next(key for key in pins if key!=self.fixed.ITEM)
  outside='static.directory-intro'
  raw=(c.ROOT/self.fixed.DIRECTORY).read_bytes().replace(b'\r\n',b'\n')
  old=self.fixed._reviewed_directory_label_source(raw)
  self.assertEqual(self.fixed._reviewed_directory_label_source(raw.replace(b'\n',b'\r\n')),old)
  changed_link=raw.replace(b'/agincourt-north/',b'/changed-destination/',1)
  for name,rejected in [('historical',old),('extra-byte',raw+b'\n'),('changed-link',changed_link)]:
   with self.subTest(source=name):
    read_bytes=Path.read_bytes
    def read_rejected(path):
     return rejected if path==c.ROOT/self.fixed.DIRECTORY else read_bytes(path)
    with patch.object(Path,'read_bytes',read_rejected),self.assertRaisesRegex(c.v.VoiceError,'Current reviewed directory source differs'):
     self.compile(editorial=editorial,bundle=bundle)
  destination=c.ROOT/self.fixed.DESTINATION
  read_bytes=Path.read_bytes
  def read_changed_destination(path):
   raw=read_bytes(path)
   return raw+b'\n' if path==destination else raw
  with patch.object(Path,'read_bytes',read_changed_destination),self.assertRaisesRegex(c.v.VoiceError,'Fixed wording source changed'):
   self.compile(editorial=editorial,bundle=bundle)
  packets={**self.current,identity:{**self.current[identity],'draft':'Altered label'}}
  with patch.object(c.seam,'current_canonical_requests',return_value=packets),self.assertRaisesRegex(c.v.VoiceError,'packet or review map'):
   self.compile(editorial=editorial,bundle=bundle)
  records=copy.deepcopy(bundle['fixed_records'])
  records[identity]['binding']['text']+=' altered'
  with self.assertRaisesRegex(c.v.VoiceError,'packet or review map'):
   self.compile(editorial=editorial,bundle={**bundle,'fixed_records':records})
  for incompatible in ({**editorial,identity:editorial[outside]},
                       {key:entry for key,entry in editorial.items() if key!=outside}):
   with self.assertRaises(c.v.VoiceError):
    self.compile(editorial=incompatible,bundle=bundle)
  records={**bundle['fixed_records']}
  records[outside]=records.pop(identity)
  out_of_scope={**editorial,identity:editorial[outside]}
  del out_of_scope[outside]
  with self.assertRaisesRegex(c.v.VoiceError,'Exact current fixed wording scope required'):
   self.compile(editorial=out_of_scope,bundle={**bundle,'fixed_records':records})
  catalogue=self.compile(editorial=editorial,bundle=bundle)
  for change in ('older-version','foreign-review','changed-text','incomplete'):
   altered=copy.deepcopy(catalogue)
   if change=='older-version':altered['version']='scarb-ai-voice-mixed-2'
   elif change=='foreign-review':altered['entries'][identity]['receipt_sha256']=pins[self.fixed.ITEM]['receipt_sha256']
   elif change=='changed-text':altered['entries'][identity]['text']+=' altered'
   else:del altered['entries'][outside]
   with self.subTest(reader=change),self.assertRaises(ValueError):
    accepted_resolver(altered,self.expected)
   self.assertEqual(MixedReleaseBridgeTests.js(self,altered,self.expected).returncode,2)
  self.assertFalse((self.state/'generation.lock').exists())



 def community_layout_fixture(self):
  from scripts.scarb_accepted_copy import fixed_community_layout_pins
  bundle,editorial,_,directory=self.directory_bundle()
  layout=fixed_community_layout_pins()
  # Private review records stay outside the repository. These are rejected evidence.
  bundle['fixed_records'].update({identity:{} for identity in layout})
  editorial={key:item for key,item in editorial.items() if key not in layout}
  projection={key:{**entry,'origin':'scarb-fixed-wording-review-1'}
              for key,entry in {**self.pins,**directory,**layout}.items()}
  return bundle,editorial,layout,projection

 def test_community_layout_complete_catalogue_preserves_whitespace_and_shell(self):
  from scripts import stage_scarb_ai_inputs as stage
  bundle,editorial,layout,projection=self.community_layout_fixture()
  # Stub private authentication only for the synthetic full-catalogue wiring test.
  with patch.object(self.fixed,'verify_canonical_fixed_records',return_value=projection):
   catalogue=self.compile(editorial=editorial,bundle=bundle)
   candidate=self.state/'candidate.json'
   candidate.write_bytes(c.v.encoded(catalogue))
   path='docs/community/index.html'
   with patch.object(c,'_collect_admitted_editorial_entries',return_value=editorial):
    staged=stage.generator_inputs(list(self.current.values()),{},self.state,candidate,
                                  shells={path:self.shells[path]},authoring_version='v3',mixed_bundle=bundle)
  self.assertEqual(catalogue['version'],'scarb-ai-voice-mixed-4')
  self.assertEqual(len(catalogue['entries']),736)
  self.assertEqual(len(layout),9)
  self.assertEqual(len(projection),67)
  self.assertEqual({key for key,entry in catalogue['entries'].items()
                    if entry['origin']=='scarb-fixed-wording-review-1'},set(projection))
  self.assertEqual(staged[path],(c.ROOT/path).read_bytes().replace(b'\r\n',b'\n'))
  self.assertEqual(json.loads(staged['accepted-copy.json']),catalogue)
  resolve=accepted_resolver(catalogue,self.expected)
  js=MixedReleaseBridgeTests.js(self,catalogue,self.expected)
  self.assertEqual(js.returncode,0,js.stderr)
  self.assertEqual(json.loads(js.stdout),{key:resolve(key) for key in self.expected})
  self.assertEqual(resolve('shell.shell-861ddc17-026'),'Maximum words ')
  self.assertEqual(resolve('shell.shell-861ddc17-035'),' Grayscale')

 def test_community_layout_rejects_forged_malformed_and_overlapping_candidates(self):
  bundle,editorial,layout,projection=self.community_layout_fixture()
  identity='shell.shell-861ddc17-026'
  outside='static.community-intro'
  valid_scope=bundle['fixed_records']
  with self.assertRaisesRegex(c.v.VoiceError,'packet or review map'):
   self.compile(editorial=editorial,bundle=bundle)
  widened={**valid_scope}
  widened[outside]=widened.pop(identity)
  swapped={**editorial,identity:editorial[outside]}
  del swapped[outside]
  cases=((widened,swapped),(valid_scope,{**editorial,identity:editorial[outside]}),
         (valid_scope,{key:entry for key,entry in editorial.items() if key!=outside}),
         (list(valid_scope),editorial),({**valid_scope,identity:None},editorial))
  for evidence,edits in cases:
   with self.assertRaises(c.v.VoiceError):
    self.compile(editorial=edits,bundle={**bundle,'fixed_records':evidence})
  with patch.object(self.fixed,'verify_canonical_fixed_records',return_value=projection):
   catalogue=self.compile(editorial=editorial,bundle=bundle)
  for issue in ('whitespace','receipt','provenance','older-version','different-origin','extra-fixed','malformed'):
   altered=copy.deepcopy(catalogue)
   entry=altered['entries'][identity]
   if issue=='whitespace':entry['text']=entry['text'].strip()
   elif issue=='receipt':entry['receipt_sha256']=layout['shell.shell-861ddc17-035']['receipt_sha256']
   elif issue=='provenance':entry['provenance']={}
   elif issue=='older-version':altered['version']='scarb-ai-voice-mixed-3'
   elif issue=='different-origin':entry['origin']='openai-api-reviewed'
   elif issue=='extra-fixed':altered['entries'][outside]['origin']='scarb-fixed-wording-review-1'
   else:altered['entries'][identity]=None
   with self.subTest(issue=issue):
    with self.assertRaises(ValueError):accepted_resolver(altered,self.expected)
    self.assertEqual(MixedReleaseBridgeTests.js(self,altered,self.expected).returncode,2)
  self.assertFalse((self.state/'generation.lock').exists())



 def test_community_edition_scope_and_readers(self):
  from scripts import stage_scarb_ai_inputs as stage
  from scripts.scarb_accepted_copy import fixed_community_edition_pins
  edition=fixed_community_edition_pins()
  bundle,editorial,_,projection=self.community_layout_fixture()
  bundle['fixed_records'].update({identity:{} for identity in edition})
  editorial={identity:entry for identity,entry in editorial.items() if identity not in edition}
  projection.update({identity:{**pin,'origin':'scarb-fixed-wording-review-1'}
                     for identity,pin in edition.items()})
  self.assertEqual((len(edition),len(projection)),(10,77))
  identity='shell.shell-861ddc17-036'
  outside='static.community-intro'
  with self.assertRaisesRegex(c.v.VoiceError,'packet or review map'):
   self.compile(editorial=editorial,bundle=bundle)
  with self.assertRaisesRegex(c.v.VoiceError,'Complete disjoint'):
   self.compile(editorial={**editorial,identity:editorial[outside]},bundle=bundle)
  with self.assertRaisesRegex(c.v.VoiceError,'Complete disjoint'):
   self.compile(editorial={key:item for key,item in editorial.items() if key!=outside},bundle=bundle)
  widened={**bundle['fixed_records']}
  widened[outside]=widened.pop(identity)
  other_editorial={**editorial,identity:editorial[outside]}
  del other_editorial[outside]
  with self.assertRaisesRegex(c.v.VoiceError,'Exact current fixed wording scope'):
   self.compile(editorial=other_editorial,bundle={**bundle,'fixed_records':widened})

  # Only the private authentication return value is replaced for this full-catalogue fixture.
  with patch.object(self.fixed,'verify_canonical_fixed_records',return_value=projection):
   catalogue=self.compile(editorial=editorial,bundle=bundle)
   candidate=self.state/'candidate.json'
   candidate.write_bytes(c.v.encoded(catalogue))
   path='docs/community/index.html'
   with patch.object(c,'_collect_admitted_editorial_entries',return_value=editorial):
    staged=stage.generator_inputs(list(self.current.values()),{},self.state,candidate,
                                  shells={path:self.shells[path]},authoring_version='v3',mixed_bundle=bundle)
  self.assertEqual(catalogue['version'],'scarb-ai-voice-mixed-5')
  self.assertEqual(len(catalogue['entries']),736)
  self.assertEqual({key for key,entry in catalogue['entries'].items()
                    if entry['origin']=='scarb-fixed-wording-review-1'},set(projection))
  self.assertEqual(staged[path],(c.ROOT/path).read_bytes().replace(b'\r\n',b'\n'))
  self.assertEqual(json.loads(staged['accepted-copy.json']),catalogue)
  resolver=accepted_resolver(catalogue,self.expected)
  js=MixedReleaseBridgeTests.js(self,catalogue,self.expected)
  self.assertEqual(js.returncode,0,js.stderr)
  self.assertEqual(json.loads(js.stdout),{key:resolver(key) for key in self.expected})
  self.assertEqual(resolver('shell.shell-861ddc17-012'),'Our neighbourhood')
  self.assertTrue(resolver(identity).startswith(' '))
  for issue in ('older-version','trimmed','receipt','malformed','extra-fixed'):
   altered=copy.deepcopy(catalogue)
   entry=altered['entries'][identity]
   if issue=='older-version':altered['version']='scarb-ai-voice-mixed-4'
   elif issue=='trimmed':entry['text']=entry['text'].strip()
   elif issue=='receipt':entry['receipt_sha256']=edition['shell.shell-861ddc17-040']['receipt_sha256']
   elif issue=='malformed':altered['entries'][identity]=None
   else:altered['entries'][outside]['origin']='scarb-fixed-wording-review-1'
   with self.subTest(issue=issue):
    with self.assertRaises(ValueError):accepted_resolver(altered,self.expected)
    self.assertEqual(MixedReleaseBridgeTests.js(self,altered,self.expected).returncode,2)
  self.assertFalse((self.state/'generation.lock').exists())


class ReviewedDirectoryAppendTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.current=c.seam.current_canonical_requests()

 def setUp(self):
  from scripts import stage_scarb_ai_inputs as stage
  from scripts.scarb_grouped_membership_candidate import snapshot
  from hashlib import sha256
  self.stage=stage
  self.sha=lambda raw:sha256(raw).hexdigest()
  temporary=tempfile.TemporaryDirectory()
  self.addCleanup(temporary.cleanup)
  self.state=Path(temporary.name).resolve()
  self.roster=self.state/'fixture-roster.json'
  self.path=self.state/c.provenance.DIRECTORY_APPEND_PATH
  self.path.parent.mkdir()
  for n in range(1,9):
   (self.path.parent/f'original-{n}.json').write_bytes(c.v.encoded({'packet_sha256':f'{n:064x}'}))
  self.original=c.v.digest(snapshot(self.state))
  directory=c.provenance.DIRECTORY_APPEND_ID
  self.packet=c.v.digest(self.current[directory])
  directory_receipt={'version':c.solo.VERSION,'origin':'openai-api-reviewed','key':self.path.stem,
                     'packet_sha256':self.packet}
  self.receipt_hash=c.v.digest(directory_receipt)
  self.receipt=c.v.encoded({**directory_receipt,'sha256':self.receipt_hash})
  self.path.write_bytes(self.receipt)
  fixture_ids=[identity for identity in self.current if identity!=directory][:69]
  self.by_root={}
  runs={}
  for n,identity in enumerate(fixture_ids,1):
   manifest=f'{n:064x}'
   pin={key:'a'*64 for key in ('funding_sha256','ledger_before_sha256','membership_before_sha256',
          'prices_sha256','runner_sha256','source_context_sha256')}
   bindings={identity:c.v.digest(self.current[identity])}
   pin.update(manifest_sha256=manifest,solo_state_sha256=self.original,solo_state_root=str(self.state),
              membership_version=1,cost_version=2,expected_purpose='production-grouped-review',
              requested_models={},returned_models={},reservation_nusd=1,month_cap_nusd=1,packet_bindings=bindings)
   runs[manifest]=pin
   self.by_root[self.state/'grouped-runs'/c.v.digest(bindings)]=pin
  self.roster.write_bytes(c.v.encoded({'version':'scarb-private-grouped-registry-1','runs':runs}))
  self.roster_sha=self.sha(self.roster.read_bytes())
  self.claim_folder=self.state/'grouped-consumption'
  self.claim_folder.mkdir()
  self.claim_index=self.state/'grouped-consumption-index.json'
  self.add_claim(next(iter(runs.values()))['packet_bindings'])
  self.enterContext(patch.multiple(c.provenance,DIRECTORY_APPEND_ROSTER_SHA256=self.roster_sha,
               DIRECTORY_APPEND_ORIGINAL_SHA256=self.original,DIRECTORY_APPEND_FILE_SHA256=self.sha(self.receipt),
               DIRECTORY_APPEND_PACKET_SHA256=self.packet,DIRECTORY_APPEND_RECEIPT_SHA256=self.receipt_hash))
  self.verify=self.enterContext(patch.object(c.provenance,'verify_grouped_provenance',
              side_effect=lambda root,packets:c.provenance._verify_current_solo_state(self.by_root[root])))

 def add_claim(self,bindings):
  name=c.v.digest(bindings)+'.json'
  raw=c.v.encoded({'version':'scarb-grouped-consumption-1','bindings':bindings})
  (self.claim_folder/name).write_bytes(raw)
  claims={path.name:self.sha(path.read_bytes()) for path in self.claim_folder.iterdir()}
  self.claim_index.write_bytes(c.v.encoded({'root':str(self.state),'claims':claims}))

 def registry(self,digest=None):
  return self.stage.private_grouped_registry(self.state,self.roster,digest or self.roster_sha)

 def test_exact_append_and_unrelated_roster_keeps_equality(self):
  with self.registry():
   self.assertEqual(len(c.provenance.TRUSTED_GROUPED_RUNS),69)
  self.assertEqual(self.verify.call_count,69)
  self.assertIsNone(c.provenance._REVIEWED_DIRECTORY_APPEND_ROSTER)
  # A differently serialized roster may have valid external authorization,
  # but that authorization does not carry this exact append decision.
  self.roster.write_bytes(self.roster.read_bytes()+b'\n')
  other=self.sha(self.roster.read_bytes())
  with self.assertRaisesRegex(c.v.VoiceError,'Current solo'):
   with self.registry(other):self.fail('unreviewed roster received the append')
  self.path.unlink()
  with self.registry(other):
   self.assertEqual(len(c.provenance.TRUSTED_GROUPED_RUNS),69)

 def test_missing_altered_extra_original_or_receipt_is_refused(self):
  original=self.path.parent/'original-1.json'
  extra=self.path.parent/'extra.json'
  original_bytes=original.read_bytes()
  for defect in ('missing-append','changed-append','missing-original','changed-original','extra','relocated'):
   with self.subTest(defect=defect),self.assertRaises(c.v.VoiceError):
    try:
     if defect=='missing-append':self.path.unlink()
     elif defect=='changed-append':self.path.write_bytes(self.receipt+b' ')
     elif defect=='missing-original':original.unlink()
     elif defect=='changed-original':original.write_bytes(original_bytes+b' ')
     elif defect=='extra':extra.write_bytes(c.v.encoded({'packet_sha256':'f'*64}))
     else:self.path.rename(extra)
     with self.registry():self.fail('changed solo inventory was admitted')
    finally:
     self.path.write_bytes(self.receipt)
     original.write_bytes(original_bytes)
     extra.unlink(missing_ok=True)
   self.assertIsNone(c.provenance._REVIEWED_DIRECTORY_APPEND_ROSTER)
   self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)

 def test_current_packet_and_claim_disjointness_are_required(self):
  directory=c.provenance.DIRECTORY_APPEND_ID
  changed={**self.current,directory:{**self.current[directory],'draft':'fixture drift'}}
  with patch.object(c.seam,'current_canonical_requests',return_value=changed):
   with self.assertRaisesRegex(c.v.VoiceError,'exact current canonical packet'):
    with self.registry():self.fail('changed directory packet was admitted')
  self.add_claim({'fictional.other-id':self.packet})
  with self.assertRaisesRegex(c.v.VoiceError,'overlaps grouped claims'):
   with self.registry():self.fail('claimed packet was admitted')


class PrivateRegistryPromptVersionTests(unittest.TestCase):
 def fixture(self, version):
  from tests.test_scarb_grouped_publication_versions import PublicationVersionTests
  from scripts import scarb_shared_cost_proof_candidate as amounts
  import shutil
  f=PublicationVersionTests();f.setUp();self.addCleanup(f.doCleanups)
  if version==3:f.upgrade()
  old=f.extra['budget.json'];before={'months':{'2026-11':.1},'paid_pilot_usd':.1}
  reserve=f.pin['reservation_nusd'];after,_=amounts.debit(before,'2026-11',reserve,1000000000,1000000000)
  members={h:c.v.digest(f.pin['packet_bindings']) for h in f.pin['packet_bindings'].values()}
  budget=amounts.proof(before,after,'2026-11',reserve,old['actual_usage_cost_nusd'],1000000000,1000000000,f.pin['packet_bindings'],{},members)
  budget.update({k:old[k] for k in ['funding_sha256','prices_sha256','input_bounds','output_bounds']})
  f.extra.update({'ledger-before.json':before,'ledger-after.json':after,'membership-before.json':{},'membership-after.json':members,'budget.json':budget})
  f.pin.update(cost_version=2,expected_purpose='production-grouped-review',month_cap_nusd=1000000000,membership_before_sha256=c.v.digest({}),ledger_before_sha256=c.v.digest(before))
  f.seal.update(budget_sha256=c.v.digest(budget),ledger_after_sha256=c.v.digest(after),packet_membership_sha256=c.v.digest(members));f.sync()
  state=f.root/'state';target=state/'grouped-runs'/c.v.digest(f.pin['packet_bindings']);target.mkdir(parents=True)
  for p in f.root.glob('*.json'):shutil.copyfile(p,target/p.name)
  f.root=target;f.pin['solo_state_root']=str(state)
  return f,state
 def check(self,f,state,pin):
  from scripts import stage_scarb_ai_inputs as stage
  import hashlib
  path=state/'fictional-registry.json';path.write_text(json.dumps({'version':'scarb-private-grouped-registry-1','runs':{pin['manifest_sha256']:pin}}),encoding='utf8')
  with patch('scripts.scarb_grouped_membership_candidate.snapshot',return_value={}):
   with stage.private_grouped_registry(state,path,hashlib.sha256(path.read_bytes()).hexdigest()):
    self.assertEqual(set(c.provenance.TRUSTED_GROUPED_RUNS),{pin['manifest_sha256']})
  self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)
 def test_exact_legacy_and_version3_pins_with_real_provenance(self):
  for version in [2,3]:
   with self.subTest(version=version):
    f,state=self.fixture(version);self.check(f,state,f.pin)
 def test_missing_swapped_unknown_extra_versions_fail_closed(self):
  for version in [2,3]:
   f,state=self.fixture(version)
   changes=['missing','legacy','unknown','null','extra','swap'] if version==3 else ['legacy','unknown','null','extra','swap']
   for change in changes:
    pin=copy.deepcopy(f.pin)
    if change=='missing':pin.pop('prompt_version')
    elif change=='extra':pin['extra']=True
    else:pin['prompt_version']={'legacy':'legacy-1','unknown':'future-9','null':None,'swap':'numeric-citation-2' if version==2 else 'legacy-1'}[change]
    with self.subTest(version=version,change=change),self.assertRaises(c.v.VoiceError):self.check(f,state,pin)
    self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)
 def test_version3_still_checks_immutable_receipts_and_independent_qa(self):
  from tests.test_scarb_ai_voice import response,REVIEW
  for defect in ['tamper','adverse']:
   f,state=self.fixture(3)
   if defect=='tamper':(f.root/'journal.json').write_text('{}')
   else:
    rr=response({p['id']:dict(REVIEW,approve=False,meaning_preserved=False,issues=['Fictional adverse finding']) for p in f.p});rr.update(id='context-reviewer',model=f.models['reviewer'])
    f.env['review_response']=rr;_,usage=c.v.unpack(rr)
    f.journal['stages'][1].update(response_sha256=c.v.digest(rr),usage=usage)
    f.seal.update(envelope_sha256=c.v.digest(f.env),journal_sha256=c.v.digest(f.journal));f.sync()
   with self.subTest(defect=defect),self.assertRaises(c.v.VoiceError):self.check(f,state,f.pin)
   self.assertFalse(c.provenance.TRUSTED_GROUPED_RUNS)
