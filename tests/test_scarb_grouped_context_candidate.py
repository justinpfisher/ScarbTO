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
 def test_home_accessible_map_requires_positive_propositions_in_both_marker_states(self):
  ids=['static.app-16','static.app-17']; contexts=c.current_contexts([self.current[k] for k in ids])
  for k,expected in zip(ids,('shapes and letters','Marker letters')):
   a=contexts[k];self.assertEqual(a['locks'],{'VALUE_0':'DineSafe'})
   self.assertIn('DineSafe records',a['must_preserve'][0]);self.assertIn(expected,a['must_preserve'][1])
   self.assertIn('alongside colour',a['must_preserve'][1]);self.assertIn('matching list',a['must_preserve'][2])
  self.assertNotIn('shapes',contexts[ids[1]]['must_preserve'][1])
 def test_home_accessible_map_refuses_other_mode_or_drift(self):
  from unittest.mock import patch
  item=self.current['static.app-16']; read=Path.read_bytes
  with patch.object(Path,'read_bytes',lambda p:read(p)+(b' ' if p.name=='index.html' else b'')):
   with self.assertRaisesRegex(c.v.VoiceError,'accessibility source changed'):
    c.home_map_accessibility_context(item)
  with self.assertRaisesRegex(c.v.VoiceError,'factual lock changed'):
   c.home_map_accessibility_context(dict(item,locks={}))
  with self.assertRaisesRegex(c.v.VoiceError,'Unsupported homepage map accessibility state'):
   c.home_map_accessibility_context(self.current['static.app-15'])
 def test_home_selected_calls_binds_five_distinct_runtime_outputs(self):
  ids=['static.app-'+k for k in ('02','03','dynamic-02','dynamic-04','dynamic-05')]
  rows=c.current_contexts([self.current[k] for k in ids])
  self.assertEqual(set(rows),set(ids));self.assertEqual(len({r['consumer'] for r in rows.values()}),5)
  for k,meaning in zip(ids,('Loading selected TPS','Toronto Police Service','TPS changed','Sum of the selected','actual division')):
   self.assertEqual(rows[k]['locks'],self.current[k]['locks'])
   self.assertIn(meaning,' '.join(rows[k]['must_preserve']))
  self.assertIn('Older counts are removed.', rows[ids[2]]['must_preserve'])
  self.assertEqual(c.current_contexts(self.packets),self.contexts)
 def test_home_selected_calls_rejects_source_drift_and_unrelated_runtime(self):
  from unittest.mock import patch
  item=self.current['static.app-02']; read=Path.read_bytes
  with patch.object(Path,'read_bytes',lambda p:read(p)+(b' ' if p.name=='selected-calls.mjs' else b'')):
   with self.assertRaisesRegex(c.v.VoiceError,'selected-calls producer changed'):
    c.home_selected_calls_context(item)
  with self.assertRaisesRegex(c.v.VoiceError,'packet or locks changed'):
   c.home_selected_calls_context(dict(item,locks={}))
  with self.assertRaisesRegex(c.v.VoiceError,'Unsupported homepage selected-calls runtime state'):
   c.home_selected_calls_context(self.current['static.app-04'])
 def test_home_dinesafe_list_preserves_nine_consumer_specific_propositions(self):
  expected=('26','28','30','32','43','46','dynamic-08','dynamic-09','dynamic-12')
  ids=['static.app-'+i for i in expected]
  a=c.current_contexts([self.current[k] for k in ids])
  self.assertEqual(set(a),set(ids));self.assertEqual(a[ids[0]]['occurrences'],2)
  self.assertIn('inspection date may be earlier',' '.join(a[ids[2]]['must_preserve']))
  self.assertIn('In first person, report what Scarb found',a[ids[2]]['must_preserve'][0])
  self.assertIn('comparing the records day to day brings changes into view',a[ids[2]]['must_preserve'][0])
  self.assertIn('pick a familiar name and follow its inspection trail with Scarb',a[ids[3]]['must_preserve'][0])
  self.assertIn('detected the event',' '.join(a[ids[4]]['must_preserve']))
  self.assertIn('previous recorded status',' '.join(a[ids[7]]['must_preserve']))
  self.assertIn('does not fetch',' '.join(a[ids[8]]['must_preserve']))
  for k in ids:self.assertEqual(a[k]['locks'],self.current[k]['locks'])
 def test_home_dinesafe_list_refuses_drift_and_other_mode(self):
  from unittest.mock import patch
  item=self.current['static.app-43']; read=Path.read_bytes
  with patch.object(Path,'read_bytes',lambda p:read(p)+(b' ' if p.name=='app.mjs' else b'')):
   with self.assertRaisesRegex(c.v.VoiceError,'DineSafe list source changed'):c.home_dinesafe_list_context(item)
  with self.assertRaisesRegex(c.v.VoiceError,'packet or locks changed'):
   c.home_dinesafe_list_context(dict(item,locks={}))
  with self.assertRaisesRegex(c.v.VoiceError,'Unsupported homepage DineSafe list consumer'):
   c.home_dinesafe_list_context(self.current['static.app-39'])
 def test_neighbourhood_runtime_keeps_all_eight_exact_roles_and_lock_values(self):
  ids=[f'static.neighbourhood-page-dynamic-{i:02}' for i in range(1,9)]
  a=c.current_contexts([self.current[k] for k in ids])
  self.assertEqual(set(a),set(ids))
  for k in ids:self.assertEqual(a[k]['locks'],self.current[k]['locks'])
  self.assertEqual([a[k]['consumer'] for k in ids],['renderWards']+['renderRecords']*3+['loadPage']*4)
  for idx,anchor in ((0,'electoral assignment'),(1,'City inspection date'),(3,'total matched DineSafe'),(5,'City record for anything newer'),(6,'not live results'),(7,'timezone is unspecified')):
   self.assertIn(anchor,' '.join(a[ids[idx]]['must_preserve']))
 def test_neighbourhood_runtime_rejects_drift_and_nonruntime_packet(self):
  from unittest.mock import patch
  k='static.neighbourhood-page-dynamic-08'; item=self.current[k];read=Path.read_bytes
  with patch.object(Path,'read_bytes',lambda p:read(p)+(b' ' if p.name=='neighbourhood-page.mjs' else b'')):
   with self.assertRaisesRegex(c.v.VoiceError,'Neighbourhood runtime source changed'):c.neighbourhood_runtime_context(item)
  with self.assertRaisesRegex(c.v.VoiceError,'packet or locks changed'):
   c.neighbourhood_runtime_context(dict(item,locks={}))
  with self.assertRaisesRegex(c.v.VoiceError,'Unsupported neighbourhood runtime consumer'):
   c.neighbourhood_runtime_context(self.current['static.neighbourhood-page-03'])
 def test_weekly_html_context_is_route_bound_and_retains_limitations(self):
  keys=('counts','geography','source-limit','source-note','source-invitation','source-name','preparation','correction','updated')
  ids=['python.weekly-'+k for k in keys]
  a=c.current_contexts([self.current[k] for k in ids])
  self.assertEqual(set(a),set(ids))
  for k in ids:
   self.assertEqual(a[k]['locks'],self.current[k]['locks'])
   self.assertIn('archived editions and RSS identities are unchanged',a[k]['meaning'])
  self.assertIn('/C/',a[ids[0]]['consumer'])
  self.assertIn('/V/',a[ids[1]]['consumer'])
  self.assertIn('newly added does not mean a new business',' '.join(a[ids[1]]['must_preserve']))
  self.assertIn('not publication',' '.join(a[ids[6]]['must_preserve']))
  self.assertIn('revision is above one',' '.join(a[ids[7]]['must_preserve']))
 def test_weekly_html_context_accepts_only_the_two_exact_byte_representations(self):
  import hashlib
  from unittest.mock import patch
  item=self.current['python.weekly-counts']; actual=Path.read_bytes
  for offset in (0,1):
   files={}
   for path,allowed in c.WEEKLY_HTML_PINS.items():
    raw=actual(c.ROOT/path).replace(b'\r\n',b'\n')
    if offset:raw=raw.replace(b'\n',b'\r\n')
    self.assertEqual(hashlib.sha256(raw).hexdigest(),allowed[offset])
    files[c.ROOT/path]=raw
   with patch.object(Path,'read_bytes',lambda p:files[p] if p in files else actual(p)):
    a=c.weekly_html_context(item)
    self.assertEqual(a['source_sha256'],{k:v[offset] for k,v in c.WEEKLY_HTML_PINS.items()})
    for path in files:
     saved=files[path];files[path]+=(b'\r\n' if offset else b'\n')+b'# unrelated content edit'
     with self.assertRaisesRegex(c.v.VoiceError,'renderer or formatter changed'):c.weekly_html_context(item)
     files[path]=saved
 def test_weekly_html_context_refuses_archive_route_source_or_packet_drift(self):
  from unittest.mock import patch
  item=self.current['python.weekly-counts']; read=Path.read_bytes
  with patch.object(Path,'read_bytes',lambda p:read(p)+(b' ' if p.name=='build_weekly_brief.py' else b'')):
   with self.assertRaisesRegex(c.v.VoiceError,'renderer or formatter changed'):c.weekly_html_context(item)
  with self.assertRaisesRegex(c.v.VoiceError,'packet or locks changed'):c.weekly_html_context(dict(item,locks={}))
  with self.assertRaisesRegex(c.v.VoiceError,'Unsupported weekly HTML producer context'):
   c.weekly_html_context(self.current['python.weekly-title'])
 def test_exact_historical_map_replay_accepts_only_audited_representations_and_scope(self):
  import hashlib
  from unittest.mock import patch
  packets=[self.current[k] for k in ('static.app-16','static.app-17')]
  binding={x['id']:c.v.digest(x) for x in packets}
  pin={'manifest_sha256':p.HISTORICAL_MAP_MANIFEST,'source_context_sha256':p.HISTORICAL_MAP_CONTEXT,'packet_bindings':binding}
  lf={k:(c.ROOT/k).read_bytes().replace(b'\r\n',b'\n') for k in p.HISTORICAL_MAP_LF}
  crlf={k:x.replace(b'\n',b'\r\n') for k,x in lf.items()}
  first,lf_pins=p._historical_map_context(pin,packets,lf)
  second,crlf_pins=p._historical_map_context(pin,packets,crlf)
  self.assertEqual(first,second)
  self.assertEqual(c.v.digest(first),p.HISTORICAL_MAP_CONTEXT)
  self.assertEqual(lf_pins,p.HISTORICAL_MAP_LF)
  self.assertEqual(crlf_pins,c.HOME_MAP_PINS)
  for source in (lf,crlf):
   for k,raw in source.items():
    bad=raw.replace(b'data',b'dAta',1)
    self.assertNotEqual(hashlib.sha256(raw).hexdigest(),hashlib.sha256(bad).hexdigest())
    with self.assertRaisesRegex(c.v.VoiceError,'Unknown historical map source bytes'):
     p._historical_map_context(pin,packets,{**source,k:bad})
  with self.assertRaisesRegex(c.v.VoiceError,'provenance scope'):
   p._historical_map_context(dict(pin,manifest_sha256='0'*64),packets,lf)
  with self.assertRaisesRegex(c.v.VoiceError,'provenance scope'):
   p._historical_map_context(pin,[self.current['static.app-15'],packets[1]],lf)
  read=Path.read_bytes
  with patch.object(Path,'read_bytes',lambda path:lf[path.relative_to(c.ROOT).as_posix()] if path.is_relative_to(c.ROOT) and path.relative_to(c.ROOT).as_posix() in lf else read(path)):
   with self.assertRaisesRegex(c.v.VoiceError,'accessibility source changed'):
    c.home_map_accessibility_context(packets[0])
  self.assertFalse(p.TRUSTED_GROUPED_RUNS)
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
