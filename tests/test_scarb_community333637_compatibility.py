import unittest,hashlib,json,subprocess
from scripts import scarb_group21_source_compatibility as h
from scripts import scarb_grouped_context_candidate as c
class DiagnosticCopyTests(unittest.TestCase):
 def test_exact_three_edits_reconstruct_prior_source(self):
  raw=(h.ROOT/'docs/scarb-voice.mjs').read_bytes()
  self.assertEqual(hashlib.sha256(raw).hexdigest(),h.COMMUNITY333637_AFTER)
  for old,new in h.COMMUNITY333637_EDITS:
   self.assertEqual(raw.count(new),1);self.assertNotIn(old,raw);raw=raw.replace(new,old)
  self.assertEqual(hashlib.sha256(raw).hexdigest(),h.COMMUNITY15_AFTER)
 def test_exact_packets_and_unchanged_consumers(self):
  ps=c.seam.current_canonical_requests()
  for n,text in zip((33,36,37),[x[1].decode() for x in h.COMMUNITY333637_EDITS]):
   p=ps[f'static.community-publishing-message-{n}'];self.assertEqual(p['draft'],text);self.assertEqual(p['evidence'][0]['fact'],text);self.assertEqual(p['kind'],'safety')
   context=c.current_contexts([p])[p['id']]
   self.assertEqual(context['source_sha256'],'449de3e327eede3acf9d3a85b21c11cb6fafb5005e79e01555d021962866d859')
