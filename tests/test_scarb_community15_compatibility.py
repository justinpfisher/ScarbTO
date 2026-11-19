import copy,unittest
from unittest.mock import patch
from scripts import scarb_group21_source_compatibility as h
from scripts import scarb_grouped_context_candidate as c
class Community15CompatibilityTests(unittest.TestCase):
 def setUp(self):
  self.current=c.seam.current_canonical_requests()
 def case(self,m,b):
  now=c.current_contexts([self.current[i] for i in b]);old=copy.deepcopy(now)
  for x in old.values():x['source_sha256']['docs/scarb-voice.mjs']=h.COMMUNITY15_BEFORE
  return {'manifest_sha256':m,'packet_bindings':b},now,old
 def test_exact_nine_and_historical(self):
  for m,b in h.COMMUNITY15_PINS.items():
   pin,now,old=self.case(m,b);self.assertEqual(h.historical_context(pin,now,old),old);self.assertEqual(h.historical_context(pin,old,old),old)
 def test_unlisted_membership_and_context(self):
  m,b=next(iter(h.COMMUNITY15_PINS.items()));pin,now,old=self.case(m,b)
  for mutate in ('manifest','binding','context','digest'):
   pp=copy.deepcopy(pin);nn=copy.deepcopy(now);oo=copy.deepcopy(old)
   if mutate=='manifest':pp['manifest_sha256']='0'*64
   if mutate=='binding':pp['packet_bindings'][next(iter(b))]='0'*64
   if mutate=='context':nn[next(iter(b))]['effective_translation']='changed meaning'
   if mutate=='digest':oo[next(iter(b))]['source_sha256']['docs/scarb-voice.mjs']='0'*64
   with self.assertRaises(ValueError):h.historical_context(pp,nn,oo)
 def test_byte_tamper_and_packet_change(self):
  m,b=next(iter(h.COMMUNITY15_PINS.items()));pin,now,old=self.case(m,b)
  original=h.Path.read_bytes
  def altered(path):
   raw=original(path);return raw+b' ' if path.as_posix().endswith('docs/scarb-voice.mjs') else raw
  with patch.object(h.Path,'read_bytes',altered):
   with self.assertRaises(ValueError):h.historical_context(pin,now,old)
  changed=copy.deepcopy(self.current);changed[next(iter(b))]['draft']+=' changed'
  with patch('scripts.scarb_grouped_projection_seam.current_canonical_requests',return_value=changed):
   with self.assertRaises(ValueError):h.historical_context(pin,now,old)
