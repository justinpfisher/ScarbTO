import copy,tempfile,unittest
from pathlib import Path,PurePosixPath
from unittest.mock import patch
from scripts import scarb_grouped_context_candidate as c
class SavedContextTests(unittest.TestCase):
 def setUp(self):self.packets=[p for k,p in c.seam.current_canonical_requests().items() if k.startswith('static.saved-')]
 def test_exact_nine_and_four_name_holes(self):
  contexts=c.current_contexts(self.packets);self.assertEqual(len(contexts),9)
  self.assertEqual(sum(bool(x['runtime_parameter']) for x in contexts.values()),4)
  for p in self.packets:self.assertEqual(contexts[p['id']]['locks'],p['locks'])
  body=c.context_prompts(self.packets[:2],{'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'},c.current_contexts(self.packets[:2]),prompt_version='numeric-citation-2')
  self.assertIn('{{NAME}}',str(body));self.assertNotIn('Satchell',str(body))
 def test_unknown_draft_lock_evidence_kind_rejected(self):
  for field,value in [('id','static.saved-unknown'),('draft','Different'),('locks',{}),('evidence',[]),('kind','safety')]:
   p=copy.deepcopy(next(p for p in self.packets if p['id']=='static.saved-added'));p[field]=value
   with self.assertRaises(c.v.VoiceError):c.saved_context(p)
   with self.assertRaises(c.v.VoiceError):c.current_contexts([p])
 def test_each_behavior_file_tamper_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in c.SAVED_SOURCE_PINS:
    dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((c.ROOT/name).read_bytes())
   for name in c.SAVED_SOURCE_PINS:
    dest=root/name;raw=dest.read_bytes();dest.write_bytes(raw+b'\n')
    with patch.object(c,'ROOT',root),self.assertRaises(c.v.VoiceError):c.saved_context(self.packets[0])
    dest.write_bytes(raw)
 def test_portable_source_paths(self):
  self.assertEqual(set(c.SAVED_SOURCE_PINS),{'docs/saved-areas.mjs','docs/area-selection.mjs'})
  for name in c.SAVED_SOURCE_PINS:self.assertEqual(PurePosixPath(name).parts,('docs',name.split('/')[1]))
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in c.SAVED_SOURCE_PINS:
    dest=root.joinpath(*PurePosixPath(name).parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((c.ROOT/name).read_bytes())
   with patch.object(c,'ROOT',root):self.assertEqual(c.saved_context(self.packets[0])['source_sha256'],c.SAVED_SOURCE_PINS)
 def test_existing_contexts_unchanged(self):
  self.assertEqual(c.current_contexts([]),{})
  p=c.seam.current_canonical_requests()['shell.shell-b04b38d4-007'];self.assertEqual(c.current_contexts([p])[p['id']]['destination'],'/neighbourhoods/')
if __name__=='__main__':unittest.main()
