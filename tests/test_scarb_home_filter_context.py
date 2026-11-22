import copy,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import scarb_grouped_context_candidate as context,scarb_grouped_protected_caller_candidate as wrapper
from tests import test_scarb_grouped_protected_caller_candidate as fixture

class HomeFilterContextTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.current=context.seam.current_canonical_requests()
  cls.packets=[cls.current[i] for i in context.HOME_FILTER_SLOTS]

 def test_bind_distinct_landmark_and_disclosure_roles_without_rewording(self):
  bound=context.current_contexts(self.packets)
  self.assertEqual([bound[p['id']]['slot_role'] for p in self.packets],['region-name','initial-disclosure-label'])
  self.assertEqual([p['draft'] for p in self.packets],['Map filters','Filters'])
  changed=copy.deepcopy(self.packets);changed[0]['draft']='Different'
  with self.assertRaises(context.v.VoiceError):context.current_contexts(changed)
  with self.assertRaises(context.v.VoiceError):context.current_contexts([self.current['shell.shell-b04b38d4-054']])

 def test_changed_behavior_and_canonical_slot_fail_closed(self):
  for change in ('behavior','canonical_slot'):
   with self.subTest(change=change),tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    for name in ('docs/index.html','docs/app.mjs','docs/styles.css','config/scarb-static-shells.json'):
     target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
     shutil.copyfile(context.ROOT/name,target)
    if change=='behavior':
     target=root/'docs/app.mjs';target.write_bytes(target.read_bytes()+b"\n")
    else:
     target=root/'config/scarb-static-shells.json'; data=json.loads(target.read_bytes())
     next(s for s in data['docs/index.html']['slots'] if s['id']==self.packets[0]['id'])['attribute']=False
     target.write_text(json.dumps(data),encoding='utf8')
    with patch.object(context,'ROOT',root),patch.object(context.seam,'current_canonical_requests',return_value=self.current),self.assertRaises(context.v.VoiceError):
     context.current_contexts(self.packets)

 def test_exact_current_citation_pair_preflight_respects_original_group_bound(self):
  with tempfile.TemporaryDirectory() as temp:
   state=Path(temp);mp,env,transport,now=fixture.ProtectedCallerTests().prepare(state)
   cp=state/'fixture-config.json';rp=state/'fixture-requests.json'
   wrapper.emitter.save(state,rp.name,self.packets)
   config=json.loads(cp.read_bytes());bind={p['id']:wrapper.v.digest(p) for p in self.packets}
   config['funding']['pilot_request_sha256']=list(bind.values())
   wrapper.emitter.save(state,cp.name,config)
   man=json.loads(mp.read_bytes());man.update(version='scarb-grouped-wrapper-fixture-2',prompt_version=context.contract.CITATION_PROMPT,
       config_sha256=wrapper.sha(cp),requests_sha256=wrapper.sha(rp),packet_bindings=bind)
   wrapper.emitter.save(state,mp.name,man); original=(state/'usage.json').read_bytes()
   answer=wrapper._invoke(mp,wrapper.sha(mp),state=state,expected_state=state,env=env,transport=transport,now=now,
       completed_at=None,preflight=True)
   self.assertTrue(answer['ready_for_protected_lookup']);self.assertEqual(transport.calls,[])
   self.assertEqual((state/'usage.json').read_bytes(),original)
