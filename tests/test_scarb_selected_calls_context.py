import unittest,json,subprocess,tempfile,shutil
from pathlib import Path
from scripts import scarb_grouped_context_candidate as c
class SelectedCallsContextTests(unittest.TestCase):
 def test_exact20_renderer_policy_and_bounds(self):
  current=c.seam.current_canonical_requests();ps=[p for i,p in current.items() if i.startswith('static.selected-calls-')];contexts=c.current_contexts(ps)
  self.assertEqual(len(contexts),20)
  for p in ps:
   x=contexts[p['id']];self.assertEqual(x['locks'],p['locks']);self.assertEqual(x['policy']['divisions'],['D41','D42','D43']);self.assertEqual(x['source_evidence_sha256'],p['evidence'][0]['sha256'])
  self.assertEqual(contexts['static.selected-calls-08']['usage'],'cached counts expired')
  self.assertEqual(contexts['static.selected-calls-06']['usage'],'source data is stale')
  for j in range(0,20,3):
   batch=ps[j:j+3];body=c.context_prompts(batch,{'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'},{p['id']:contexts[p['id']] for p in batch});self.assertLessEqual(len(c.v.encoded(body)),48000)
 def test_changed_behavior_draft_or_reason_refuses(self):
  files=subprocess.check_output(['git','ls-files'],cwd=c.ROOT,text=True).splitlines()+['scripts/scarb_selected_calls_contexts.mjs']
  for kind in ['policy','copy','reason']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
    root=Path(d)
    for name in files:
     dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,dest)
    q=root/('docs/scarb-voice.mjs' if kind=='copy' else 'docs/selected-calls.mjs');s=q.read_text(encoding='utf-8')
    old,new={'policy': ('maxLocalAgeMs: 10 * 60_000', 'maxLocalAgeMs: 20 * 60_000'), 'copy': ('more than 30 minutes old', 'more than 31 minutes old'), 'reason': ('"cached counts expired": staticCopy(\'selected-calls-08\')', '"cached counts expired": staticCopy(\'selected-calls-06\')')}[kind]
    self.assertIn(old,s);q.write_text(s.replace(old,new),encoding='utf-8');result=subprocess.run(['node',str(root/'scripts/scarb_selected_calls_contexts.mjs')],capture_output=True);self.assertNotEqual(result.returncode,0)
