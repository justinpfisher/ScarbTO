import copy,unittest
from unittest.mock import patch
from scripts import scarb_group21_source_compatibility as h
from scripts import scarb_grouped_context_candidate as c
class BoundedSourceCompatibilityTests(unittest.TestCase):
 def setUp(self):
  self.current=c.seam.current_canonical_requests();self.context=c.current_contexts([self.current[i] for i in h.BINDINGS]);self.old=copy.deepcopy(self.context)
  for item in self.old.values():
   for path,(before,after) in h.TRANSITIONS.items():item['source_sha256'][path]=before
  self.pin={'manifest_sha256':h.MANIFEST,'packet_bindings':h.BINDINGS}
 def test_exact_transition_and_unmodified_packets(self):
  self.assertEqual({i:c.v.digest(self.current[i]) for i in h.BINDINGS},h.BINDINGS)
  self.assertEqual(h.historical_context(self.pin,self.context,self.old),self.old)
  self.assertEqual(h.historical_context({},self.context,self.context),self.context)
 def test_unrelated_change_wrong_pin_membership_and_hash_fail(self):
  for kind in ['meaning','official','hash','manifest','binding','membership']:
   current=copy.deepcopy(self.context);pin=copy.deepcopy(self.pin);i=next(iter(current))
   if kind=='meaning':current[i]['meaning']='changed'
   elif kind=='official':current[i]['official_wording']='changed'
   elif kind=='hash':current[i]['source_sha256']['docs/scarb-voice.mjs']='a'*64
   elif kind=='manifest':pin['manifest_sha256']='a'*64
   elif kind=='binding':pin['packet_bindings'][i]='a'*64
   else:current.pop(i)
   with self.subTest(kind=kind),self.assertRaises(c.v.VoiceError):h.historical_context(pin,current,self.old)
 def test_actual_source_bytes_not_just_claimed_hash(self):
  original=h.Path.read_bytes
  def altered(path):return original(path)+b'\n'
  with patch.object(h.Path,'read_bytes',altered),self.assertRaises(c.v.VoiceError):h.historical_context(self.pin,self.context,self.old)
 def test_regulated_action_and_condition_retained(self):
  p=self.current['static.finding-explanation-2c28027af8513b95']
  self.assertEqual(p['draft'],'Multi-service articles that were not readily cleanable were being used.')
  self.assertEqual(p['evidence'][1]['fact'],'use multi-service articles not of readily cleanable form - sec. 8(1)(c)')
  self.assertEqual(p['locks'],{})
  self.assertNotIn('designed',p['draft'])
