import copy,hashlib,unittest
from unittest.mock import patch
from scripts import scarb_group21_source_compatibility as h,scarb_grouped_context_candidate as c
class Finding22CompatibilityTests(unittest.TestCase):
 def setUp(self):
  manifest='04eabc865f01c39746bf2de0c2abb955fe63a0052e0763db56ccda3cd55f5bb2'
  self.packets=c.seam.current_canonical_requests()
  bindings=h.FINDING22_PINS[manifest]
  self.current=c.current_contexts([self.packets[identity] for identity in bindings])
  self.prior=self.sealed_context(self.current,after_finding22=False)
  self.pin={'manifest_sha256':manifest,'packet_bindings':bindings,
            'source_context_sha256':c.v.digest(self.prior)}
 @staticmethod
 def sealed_context(current,*,after_finding22):
  expected={path:digests[int(after_finding22)] for path,digests in h.FINDING22_TRANSITIONS.items()}
  config='config/scarb-finding-source-drafts.json'
  expected[config]=h.COMMUNITY15_DIRECTORY_SOURCE_PAIRS[config][1]
  return {identity:{**item,'source_sha256':expected.copy()} for identity,item in current.items()}
 def test_exact_two_file_reconstruction_and_current_context(self):
  voice=(h.ROOT/'docs/scarb-voice.mjs').read_bytes()
  _,sources=h._pre_directory_source_context(self.current,voice)
  restored=h._finding22_sources(self.pin,current_sources=sources)
  for p,(before,_) in h.FINDING22_TRANSITIONS.items():self.assertEqual(hashlib.sha256(restored[p]).hexdigest(),before)
  self.assertEqual(h.historical_context(self.pin,self.current,self.prior),self.prior)
 def test_unlisted_held_changed_bindings_extra_and_semantic_tamper(self):
  for kind in ['unlisted','held','binding','extra','meaning','digest','recorded','seal']:
   pin=copy.deepcopy(self.pin);current=copy.deepcopy(self.current);prior=copy.deepcopy(self.prior);i=next(iter(current))
   if kind=='unlisted':pin['manifest_sha256']='a'*64
   elif kind=='held':pin['manifest_sha256']='904644a48ac1e29ca0a59061ba8fc8b309276f6f70aaf84cb090cb9e89c68834'
   elif kind=='binding':pin['packet_bindings'][i]='b'*64
   elif kind=='extra':current['extra']=current[i]
   elif kind=='meaning':current[i]['meaning']='changed'
   elif kind=='digest':current[i]['source_sha256']['docs/scarb-voice.mjs']='c'*64
   elif kind=='recorded':prior[i]['official_wording']='changed'
   else:pin['source_context_sha256']='d'*64
   with self.subTest(kind=kind),self.assertRaises(c.v.VoiceError):h.historical_context(pin,current,prior)
 def test_file_tamper_fails_even_with_claimed_context(self):
  original=h.Path.read_bytes
  for path in h.COMMUNITY15_DIRECTORY_SOURCE_PAIRS:
   def read(p):
    raw=original(p);return raw+b' ' if p.as_posix().endswith(path) else raw
   with self.subTest(path=path),patch.object(h.Path,'read_bytes',read),self.assertRaises(c.v.VoiceError):h.historical_context(self.pin,self.current,self.prior)
 def test_corrected_packet_meaning_and_map(self):
  ps=c.seam.current_canonical_requests()
  for suffix,(_,new) in zip(['0cccdf046fd4e2e1','1af905522aa2a33f'],h.FINDING22_EDITS):
   p=ps['static.finding-explanation-'+suffix];self.assertEqual(p['draft'],new.decode());self.assertEqual(p['evidence'][0]['fact'],new.decode());ctx=c.current_contexts([p])[p['id']];self.assertEqual(ctx['effective_translation'],new.decode());self.assertNotIn(p['id'],{i for b in h.FINDING22_PINS.values() for i in b})


 def test_directory_only_scope_preserves_later_finding_context(self):
  manifest='1dedada1d982947087e31386d3c8de8544f7ec45c0abf17b9c8f369141b74c76'
  keys=('static.finding-explanation-e515079639b0b2ad','static.finding-explanation-f47febd1613c1fbb',
        'static.finding-explanation-ffc9683a1081a818')
  self.assertNotIn(manifest,h.FINDING22_PINS)
  current=c.current_contexts([self.packets[key] for key in keys])
  recorded=self.sealed_context(current,after_finding22=True)
  pin={'manifest_sha256':manifest,'packet_bindings':{key:c.v.digest(self.packets[key]) for key in keys},
       'source_context_sha256':c.v.digest(recorded)}
  self.assertEqual(h.historical_context(pin,current,recorded),recorded)
  wrong=self.sealed_context(current,after_finding22=False)
  with self.assertRaisesRegex(c.v.VoiceError,'sealed context differs'):
   h.historical_context({**pin,'source_context_sha256':c.v.digest(wrong)},current,wrong)

 def test_current_packet_drift_is_rejected_by_reviewed_scope(self):
  changed=copy.deepcopy(self.packets)
  identity=next(iter(self.pin['packet_bindings']))
  changed[identity]['draft']+=' changed'
  with patch.object(c.seam,'current_canonical_requests',return_value=changed):
   with self.assertRaisesRegex(c.v.VoiceError,'canonical packet changed'):
    h.historical_context(self.pin,self.current,self.prior)
