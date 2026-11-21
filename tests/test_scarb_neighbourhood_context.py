import copy,tempfile,unittest,json
from pathlib import Path,PurePosixPath
from unittest.mock import patch
from scripts import scarb_grouped_context_candidate as c
from scripts import scarb_group21_source_compatibility as compatibility
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
 def test_exact_lf_and_crlf_bind_the_same_current_context(self):
  packet=self.packets[0]
  expected=c.neighbourhood_context(packet)
  original=Path.read_bytes
  paths={c.ROOT/path for path in c.NEIGHBOURHOOD_SOURCE_PINS}
  for ending in (b'\n',b'\r\n'):
   def checkout_bytes(path):
    source=original(path)
    if path in paths:
     return source.replace(b'\r\n',b'\n').replace(b'\n',ending)
    return source
   with self.subTest(ending=ending),patch.object(Path,'read_bytes',checkout_bytes):
    self.assertEqual(c.neighbourhood_context(packet),expected)

 def test_reviewed_transition_rejects_extra_scope_and_drift(self):
  manifest='1ed1e0cb9e60cc27cce57766e1fe07720eb5484c3606f48a3e5c046e4ac6df59'
  ids={'shell.shell-b1bb7e6e-027','shell.shell-b1bb7e6e-032'}
  packets=[packet for packet in self.packets if packet['id'] in ids]
  current=c.current_contexts(packets)
  sealed=copy.deepcopy(current)
  for item in sealed.values():
   item['source_sha256'][c.NEIGHBOURHOOD_BUILDER]=c.NEIGHBOURHOOD_PREVIOUS_BUILDER_SHA256
  pin={'manifest_sha256':manifest,'packet_bindings':{p['id']:c.v.digest(p) for p in packets},
       'source_context_sha256':c.v.digest(sealed),'prompt_version':c.contract.CITATION_PROMPT}
  author={'fixture':'author'}
  reviewer={'fixture':'reviewer'}
  approval=compatibility.NEIGHBOURHOOD_TRANSITIONS[manifest]
  self.assertEqual(len(compatibility.NEIGHBOURHOOD_TRANSITIONS),11)
  self.assertEqual(c.v.digest(pin['packet_bindings']),approval['packets'])
  self.assertEqual(c.v.digest(current),approval['after'])
  self.assertEqual(c.v.digest(sealed),approval['before'])
  # The private prompts are checked against sealed records by the full verifier.
  # Exercise the transition here with dummy prompt digests and the real source scope.
  fixture={**approval,'author':c.v.digest(author),'reviewer':c.v.digest(reviewer)}
  replay=compatibility.reviewed_neighbourhood_context
  with patch.dict(compatibility.NEIGHBOURHOOD_TRANSITIONS,{manifest:fixture}):
   self.assertEqual(replay(pin,current,sealed,author,reviewer),sealed)
   extra=self.packets[0]
   extended={**pin,'packet_bindings':{**pin['packet_bindings'],extra['id']:c.v.digest(extra)}}
   self.assertNotIn(extra['id'],ids)
   with self.assertRaisesRegex(c.v.VoiceError,'membership'):
    replay(extended,current,sealed,author,reviewer)
   with self.assertRaisesRegex(c.v.VoiceError,'No reviewed'):
    replay({**pin,'manifest_sha256':'0'*64},current,sealed,author,reviewer)
   changed=copy.deepcopy(current)
   changed[next(iter(changed))]['meaning']='Changed'
   with self.assertRaisesRegex(c.v.VoiceError,'context differs'):
    replay(pin,changed,sealed,author,reviewer)
   with self.assertRaisesRegex(c.v.VoiceError,'context differs'):
    replay({**pin,'source_context_sha256':'0'*64},current,sealed,author,reviewer)
   for rejected in [(author,author),(reviewer,reviewer)]:
    with self.subTest(prompts=rejected),self.assertRaisesRegex(c.v.VoiceError,'prompts differ'):
     replay(pin,current,sealed,*rejected)
   original=Path.read_bytes
   def changed_builder(path):
    source=original(path)
    return source+b'\n' if path==c.ROOT/c.NEIGHBOURHOOD_BUILDER else source
   with patch.object(Path,'read_bytes',changed_builder),self.assertRaisesRegex(c.v.VoiceError,'source changed'):
    replay(pin,current,sealed,author,reviewer)

if __name__=='__main__':unittest.main()
