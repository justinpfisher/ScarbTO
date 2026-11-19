import copy,tempfile,unittest,json
from pathlib import Path,PurePosixPath
from unittest.mock import patch
from scripts import scarb_grouped_context_candidate as c
class NeighbourhoodContextTests(unittest.TestCase):
 def setUp(self):self.packets=[p for k,p in c.seam.current_canonical_requests().items() if k in c.NEIGHBOURHOOD_CONTEXTS]
 def test_exact_slots_and_destinations(self):
  contexts=c.current_contexts(self.packets);self.assertEqual(len(contexts),43)
  self.assertEqual(contexts['shell.shell-b1bb7e6e-017']['element']['attributes']['href'],'/community/?area={{CODE}}')
  self.assertEqual(contexts['shell.shell-b1bb7e6e-004']['element']['attributes']['href'],'#inspections')
  self.assertTrue(contexts['shell.shell-b1bb7e6e-000']['attribute'])
  self.assertEqual(contexts['shell.shell-b1bb7e6e-037']['semantic_class'],'source-status-limitation')
  self.assertEqual(contexts['shell.shell-b1bb7e6e-034']['semantic_class'],'source-licence-attribution')
  self.assertEqual(contexts['static.neighbourhood-intro']['locks'],next(p for p in self.packets if p['id']=='static.neighbourhood-intro')['locks'])
 def test_packet_mismatch_fails(self):
  for field,value in [('id','shell.shell-b1bb7e6e-999'),('draft','Invented'),('locks',{'NAME':'Private address'}),('evidence',[]),('kind','unknown')]:
   p=copy.deepcopy(self.packets[0]);p[field]=value
   with self.assertRaises(c.v.VoiceError):c.neighbourhood_context(p)
 def test_source_inventory_tamper_and_posix_paths(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in [*c.NEIGHBOURHOOD_SOURCE_PINS,'config/scarb-static-shells.json']:
    self.assertNotIn(chr(92),name);dest=root.joinpath(*PurePosixPath(name).parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((c.ROOT/name).read_bytes())
   with patch.object(c,'ROOT',root):self.assertEqual(len(c.neighbourhood_context(self.packets[0])['slot_range']),2)
   for name in c.NEIGHBOURHOOD_SOURCE_PINS:
    dest=root/name;raw=dest.read_bytes();dest.write_bytes(raw+b'\n')
    with patch.object(c,'ROOT',root),self.assertRaises(c.v.VoiceError):c.neighbourhood_context(self.packets[0])
    dest.write_bytes(raw)
   dest=root/'config/scarb-static-shells.json';record=json.loads(dest.read_text());record['docs/neighbourhood-page.template.html']['slots'][0]['start']+=1;dest.write_text(json.dumps(record))
   with patch.object(c,'ROOT',root),self.assertRaises(c.v.VoiceError):c.neighbourhood_context(self.packets[0])
if __name__=='__main__':unittest.main()
