import copy,hashlib,unittest
from unittest.mock import patch
from scripts import scarb_group21_source_compatibility as h,scarb_grouped_context_candidate as c
class Finding22CompatibilityTests(unittest.TestCase):
 def setUp(self):
  self.pin={'manifest_sha256':next(iter(h.FINDING22_PINS))};self.pin['packet_bindings']=h.FINDING22_PINS[self.pin['manifest_sha256']];ps=c.seam.current_canonical_requests();self.current=c.current_contexts([ps[i] for i in self.pin['packet_bindings']]);self.prior=copy.deepcopy(self.current)
  for x in self.prior.values():
   for p,(before,after) in h.FINDING22_TRANSITIONS.items():x['source_sha256'][p]=before
 def test_exact_two_file_reconstruction_and_current_context(self):
  restored=h._finding22_sources(self.pin)
  for p,(before,_) in h.FINDING22_TRANSITIONS.items():self.assertEqual(hashlib.sha256(restored[p]).hexdigest(),before)
  self.assertEqual(h.historical_context(self.pin,self.current,self.prior),self.prior)
 def test_unlisted_held_changed_bindings_extra_and_semantic_tamper(self):
  for kind in ['unlisted','held','binding','extra','meaning','digest','recorded']:
   pin=copy.deepcopy(self.pin);current=copy.deepcopy(self.current);prior=copy.deepcopy(self.prior);i=next(iter(current))
   if kind=='unlisted':pin['manifest_sha256']='a'*64
   elif kind=='held':pin['manifest_sha256']='904644a48ac1e29ca0a59061ba8fc8b309276f6f70aaf84cb090cb9e89c68834'
   elif kind=='binding':pin['packet_bindings'][i]='b'*64
   elif kind=='extra':current['extra']=current[i]
   elif kind=='meaning':current[i]['meaning']='changed'
   elif kind=='digest':current[i]['source_sha256']['docs/scarb-voice.mjs']='c'*64
   else:prior[i]['official_wording']='changed'
   with self.subTest(kind=kind),self.assertRaises(c.v.VoiceError):h.historical_context(pin,current,prior)
 def test_file_tamper_fails_even_with_claimed_context(self):
  original=h.Path.read_bytes
  for path in h.FINDING22_TRANSITIONS:
   def read(p):
    raw=original(p);return raw+b' ' if p.as_posix().endswith(path) else raw
   with self.subTest(path=path),patch.object(h.Path,'read_bytes',read),self.assertRaises(c.v.VoiceError):h.historical_context(self.pin,self.current,self.prior)
 def test_corrected_packet_meaning_and_map(self):
  ps=c.seam.current_canonical_requests()
  for suffix,(_,new) in zip(['0cccdf046fd4e2e1','1af905522aa2a33f'],h.FINDING22_EDITS):
   p=ps['static.finding-explanation-'+suffix];self.assertEqual(p['draft'],new.decode());self.assertEqual(p['evidence'][0]['fact'],new.decode());ctx=c.current_contexts([p])[p['id']];self.assertEqual(ctx['effective_translation'],new.decode());self.assertNotIn(p['id'],{i for b in h.FINDING22_PINS.values() for i in b})
