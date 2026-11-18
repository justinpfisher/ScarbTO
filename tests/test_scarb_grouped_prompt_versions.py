import copy,json,tempfile,unittest
from pathlib import Path
from scripts import scarb_grouped_runner_candidate as r
from tests.test_scarb_grouped_runner_candidate import RunnerTests,MODELS

class PromptVersionTests(RunnerTests):
 def test_clarified_run_is_bound_and_legacy_substitution_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);funding,prices,t=self.inputs(state)
   out=r.run_fixture(state,self.packets,MODELS,funding,prices,transport=t,started_at='2026-11-18T03:01:00Z',completed_at='2026-11-18T03:01:05Z',prompt_version=r.c.contract.CITATION_PROMPT)
   root=Path(out['root']);env=r.load(root/'envelope.json')
   self.assertEqual(env['version'],'scarb-grouped-run-envelope-3')
   self.assertEqual(r.recover_fixture(state,self.packets)['status'],'completed')
   pin=dict(out['pin']);pin['prompt_version']=r.c.contract.LEGACY_PROMPT
   with self.assertRaisesRegex(r.v.VoiceError,'Prompt version'):r.verifier._verify_pinned(root,pin,self.packets)
   pin.pop('prompt_version')
   with self.assertRaisesRegex(r.v.VoiceError,'Prompt version'):r.verifier._verify_pinned(root,pin,self.packets)
   legacy=r.c.context_prompts(self.packets,MODELS,r.c.current_contexts(self.packets))
   self.assertNotEqual(legacy,env['author_request'])
   self.assertEqual(env['packets'],self.packets)
 def test_legacy_run_rejects_version_tag(self):
  with tempfile.TemporaryDirectory() as d:
   out,_=self.run_case(Path(d));pin=dict(out['pin'],prompt_version=r.c.contract.CITATION_PROMPT)
   with self.assertRaisesRegex(r.v.VoiceError,'Legacy prompt'):r.verifier._verify_pinned(out['root'],pin,self.packets)
 def test_unknown_version_before_any_state_change(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);funding,prices,t=self.inputs(state);before={p.name:p.read_bytes() for p in state.iterdir()}
   with self.assertRaisesRegex(r.v.VoiceError,'Unknown grouped prompt'):r.run_fixture(state,self.packets,MODELS,funding,prices,transport=t,started_at='2026-11-18T03:01:00Z',completed_at='2026-11-18T03:01:05Z',prompt_version='unknown')
   self.assertEqual(before,{p.name:p.read_bytes() for p in state.iterdir()});self.assertEqual(t.calls,[])
 def test_numeric_guard_unchanged(self):
  packet=self.packets[0];a={'slots':{},'tail':'Section 22','evidence_ids':[e['id'] for e in packet['evidence']]}
  with self.assertRaises(r.v.FactValidationFailure):r.f.assemble(packet,a)
  self.assertIn('Numeric citations',r.c.contract.author_instruction(r.c.contract.CITATION_PROMPT))
  self.assertEqual(r.c.contract.author_instruction(r.c.contract.LEGACY_PROMPT),r.c.contract.AUTHOR)

from tests.test_scarb_grouped_protected_caller_candidate import ProtectedCallerTests
class WrapperVersionTests(unittest.TestCase):
 def test_explicit_wrapper_version_and_invalid_versions(self):
  helper=ProtectedCallerTests()
  for version,tag,passes in [('scarb-grouped-wrapper-fixture-2',r.c.contract.CITATION_PROMPT,True),('scarb-grouped-wrapper-fixture-2','unknown',False),('scarb-grouped-wrapper-fixture-1',r.c.contract.CITATION_PROMPT,False),('scarb-grouped-wrapper-fixture-9',r.c.contract.CITATION_PROMPT,False)]:
   with self.subTest(version=version,tag=tag),tempfile.TemporaryDirectory() as d:
    state=Path(d);prepared=helper.prepare(state);mp=prepared[0];m=r.load(mp);m.update(version=version,prompt_version=tag);r.save(state,mp.name,m)
    if passes:self.assertEqual(helper.invoke(state,prepared)['calls'],2)
    else:
     with self.assertRaises(r.v.VoiceError):helper.invoke(state,prepared)
     self.assertEqual(prepared[2].calls,[]);self.assertFalse((state/'grouped-runs').exists())
