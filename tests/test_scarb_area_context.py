import unittest,tempfile,json,copy,shutil
from pathlib import Path
from unittest.mock import patch
from scripts import scarb_grouped_context_candidate as c,scarb_grouped_protected_caller_candidate as w
from tests.test_scarb_grouped_protected_caller_candidate import ProtectedCallerTests

class AreaContextTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.current=c.seam.current_canonical_requests()
 def packets(self,suffixes):return [self.current['shell.shell-b04b38d4-'+s] for s in suffixes]
 def test_all_seven_unique_bindings_and_existing_nav_unchanged(self):
  packets=self.packets(list(c.AREA_CONTROLS));contexts=c.current_contexts(packets);self.assertEqual(len(contexts),7)
  for p in packets:self.assertEqual(contexts[p['id']]['behavior_sha256'],c.AREA_BEHAVIOR_SHA256)
  nav=self.packets(['007','008']);old=c.current_contexts(nav)
  self.assertEqual(set(old[nav[0]['id']]),{'path','source_sha256','anchor_html','destination','meaning'})
  self.assertEqual(old[nav[0]['id']]['destination'],'/neighbourhoods/')
 def test_223_exact_preflights_no_calls_or_debit(self):
  for ids in [['060','061'],['078','079'],['080','081','082'],['079'],['078','079','080','081'],['003','079']]:
   with self.subTest(ids=ids),tempfile.TemporaryDirectory() as d:
    state=Path(d);mp,env,t,now=ProtectedCallerTests().prepare(state);packets=self.packets(ids)
    w.emitter.save(state,'fixture-requests.json',packets)
    config=json.loads((state/'fixture-config.json').read_text());config['funding']['pilot_request_sha256']=[w.v.digest(p) for p in packets];w.emitter.save(state,'fixture-config.json',config)
    manifest=json.loads(mp.read_text());manifest.update(requests_sha256=w.sha(state/'fixture-requests.json'),config_sha256=w.sha(state/'fixture-config.json'),packet_bindings={p['id']:w.v.digest(p) for p in packets});w.emitter.save(state,mp.name,manifest)
    before=(state/'usage.json').read_bytes()
    def preflight():return w._invoke(mp,w.sha(mp),state=state,expected_state=state,env=env,transport=t,now=now,completed_at=None,preflight=True)
    if len(ids) not in (2,3) or '003' in ids:
     with self.assertRaises(w.v.VoiceError):preflight()
    else:self.assertTrue(preflight()['ready_for_protected_lookup'])
    self.assertEqual(t.calls,[]);self.assertEqual((state/'usage.json').read_bytes(),before)
 def test_offscope_stale_duplicate_dom_behavior_and_slot_mismatch(self):
  p=self.packets(['079'])
  with self.assertRaises(c.v.VoiceError):c.current_contexts(self.packets(['077']))
  changed=copy.deepcopy(p);changed[0]['draft']='different'
  with self.assertRaises(c.v.VoiceError):c.current_contexts(changed)
  for kind in ['duplicate','behavior','slot']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
    root=Path(d)
    for name in ['docs/index.html','docs/area-explorer.mjs','config/scarb-static-shells.json']:
     target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,target)
    if kind=='duplicate':
     q=root/'docs/index.html';q.write_bytes(q.read_bytes()+c.AREA_BUTTONS['area-panel-expand'].encode())
    elif kind=='behavior':
     q=root/'docs/area-explorer.mjs';q.write_bytes(q.read_bytes()+b'\n')
    else:
     q=root/'config/scarb-static-shells.json';shell=json.loads(q.read_text(encoding='utf8'));slot=next(s for s in shell['docs/index.html']['slots'] if s['id']==p[0]['id']);slot['attribute']=True;q.write_text(json.dumps(shell),encoding='utf8')
    with patch.object(c,'ROOT',root),patch.object(c.seam,'current_canonical_requests',return_value=self.current),self.assertRaises(c.v.VoiceError):c.current_contexts(p)
 def test_protocol_bounds_still_hold(self):
  models={'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'}
  with self.assertRaises(c.v.VoiceError):c.context_prompts(self.packets(['078','079','080','081']),models,{})
  p=self.packets(['078','079']);contexts=c.current_contexts(p);contexts.pop(p[0]['id'])
  with self.assertRaises(c.v.VoiceError):c.context_prompts(p,models,contexts)
