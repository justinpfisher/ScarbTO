import unittest,tempfile,json,hashlib,copy
from pathlib import Path
from scripts import scarb_packet_consumption_candidate as c,scarb_grouped_membership_candidate as m
from tests.test_scarb_ai_voice import PACKET,CONFIG,ENV,NOW
from tests.test_scarb_ai_fact_slots import P,CONFIG as FC
from scripts import scarb_ai_fact_slots as f
class SharedConsumptionTests(unittest.TestCase):
 def claim(self,root,bindings):
  folder=root/'grouped-consumption';folder.mkdir(exist_ok=True)
  claim={'version':'scarb-grouped-consumption-1','bindings':bindings};name=c.v.digest(bindings)+'.json';path=folder/name;path.write_bytes(c.v.encoded(claim))
  claims={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
  (root/'grouped-consumption-index.json').write_bytes(c.v.encoded({'root':str(root.resolve()),'claims':claims}))
 def test_group_then_actual_solo_both_versions_no_dispatch(self):
  for packet,version in [(PACKET,1),(P,2)]:
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);self.claim(root,{packet['id']:c.v.digest(packet)})
    calls=[]
    if version==1:
     with self.assertRaises(c.v.VoiceError):c.v.generate(packet,CONFIG,root,transport=lambda *a:calls.append(a),env=ENV,now=NOW)
     self.assertEqual(calls,[])
    else:
     t=f.FixtureTransport([])
     with self.assertRaises(c.v.VoiceError):f.generate_fixture(packet,FC,root,transport=t,now=NOW)
     self.assertEqual(t.calls,[])
 def test_reverse_solo_blocks_group_disjoint_allowed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'held').mkdir();(root/'held/a.json').write_text(json.dumps({'packet_sha256':c.v.digest('A')}))
   zero={'reserved_nusd':0,'consumed_batches':{},'packet_membership':{}}
   with c.v.exclusive(root):
    with self.assertRaises(c.v.VoiceError):m.reserve_in_state(root,root,zero,{'A':c.v.digest('A')},1)
    self.assertEqual(m.reserve_in_state(root,root,zero,{'B':c.v.digest('B')},1)['reserved_nusd'],1)
 def test_recovery_tamper_missing_wrong_root_bad_binding(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.claim(root,{'A':c.v.digest('A')})
   with c.v.exclusive(root):
    with self.assertRaises(c.v.VoiceError):c.assert_unconsumed(root,{'A':c.v.digest('A')},expected_root=root)
    with self.assertRaises(c.v.VoiceError):c.assert_unconsumed(root,{'B':c.v.digest('B')},expected_root=root/'other')
    with self.assertRaises(c.v.VoiceError):c.assert_unconsumed(root,{'B':'g'*64},expected_root=root)
    with self.assertRaises(c.v.VoiceError):c.assert_unconsumed(root,{'../B':c.v.digest('B')},expected_root=root)
    next((root/'grouped-consumption').iterdir()).write_text('{}')
    with self.assertRaises(c.v.VoiceError):c.assert_unconsumed(root,{'B':c.v.digest('B')},expected_root=root)
   with self.assertRaises(c.v.VoiceError):c.assert_unconsumed(root/'absent',{'B':c.v.digest('B')},expected_root=root/'absent')
 def test_actual_group_reservation_consumes_and_orphan_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);zero={'reserved_nusd':0,'consumed_batches':{},'packet_membership':{}}
   bindings={'A':c.v.digest('A'),'B':c.v.digest('B')}
   with c.v.exclusive(root):m.reserve_in_state(root,root,zero,bindings,1)
   with c.v.exclusive(root):
    with self.assertRaises(c.v.VoiceError):c.assert_unconsumed(root,{'B':c.v.digest('B')},expected_root=root)
    self.assertTrue(c.assert_unconsumed(root,{'C':c.v.digest('C')},expected_root=root))
    next((root/'grouped-consumption').iterdir()).unlink()
    with self.assertRaises(c.v.VoiceError):c.assert_unconsumed(root,{'B':c.v.digest('B')},expected_root=root)
if __name__=='__main__':unittest.main()
