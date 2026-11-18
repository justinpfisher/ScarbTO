import unittest,json,tempfile,subprocess,shutil
from pathlib import Path
from scripts import scarb_grouped_context_candidate as c
class FindingContextTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.current=c.seam.current_canonical_requests();cls.packets=[p for i,p in cls.current.items() if i.startswith('static.finding-explanation-')]
 def test_all90_effective_sources_and_protected_overrides(self):
  contexts=c.current_contexts(self.packets);self.assertEqual(len(contexts),90)
  for p in self.packets:
   ctx=contexts[p['id']];self.assertEqual(ctx['locks'],p['locks']);self.assertEqual(ctx['official_wording'],p['evidence'][1]['fact']);self.assertEqual(p['kind'],'safety')
  self.assertIn('This does not establish that contamination occurred.',contexts['static.finding-explanation-376035dc95fc05a1']['effective_translation'])
  self.assertEqual(contexts['static.finding-explanation-7e0c1202c0f59cfd']['locks'],{'VALUE_0':'4','VALUE_1':'60'})
  models={'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'}
  for n in range(0,90,3):
   ps=self.packets[n:n+3];body=c.context_prompts(ps,models,{p['id']:contexts[p['id']] for p in ps});self.assertLessEqual(len(c.v.encoded(body)),48000)
 def test_source_disagreement_and_unknown_fallback_rejected(self):
  files=subprocess.check_output(['git','ls-files'],cwd=c.ROOT,text=True).splitlines()
  for kind in ['official','qualifier','unknown']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
    root=Path(d)
    for name in files+['scripts/scarb_finding_contexts.mjs']:
     q=root/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/name,q)
    if kind=='official':
     q=root/'config/scarb-finding-source-drafts.json';x=json.loads(q.read_text(encoding='utf8'));x[next(iter(x))]='changed source';q.write_text(json.dumps(x),encoding='utf8')
    else:
     q=root/'docs/scarb-voice.mjs';s=q.read_text(encoding='utf8')
     if kind=='qualifier':s=s.replace('This does not establish that contamination occurred.','')
     else:s=s.replace("translations.get(facts.wording.toLocaleLowerCase('en-CA')) || null","translations.get(facts.wording.toLocaleLowerCase('en-CA')) || 'invented'")
     q.write_text(s,encoding='utf8')
    p=subprocess.run(['node',str(root/'scripts/scarb_finding_contexts.mjs')],capture_output=True)
    self.assertNotEqual(p.returncode,0)
