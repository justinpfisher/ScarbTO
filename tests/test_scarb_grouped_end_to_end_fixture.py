"""Synthetic integration driver: test-only trust and solo fixture adapter.
No production registry enrollment, transport, credentials or publishable output.
"""
import unittest,json,tempfile
from pathlib import Path
from unittest.mock import patch
from tests.test_scarb_grouped_context_candidate import ContextProvenanceTests
from tests.test_scarb_grouped_mixed_canonical import output,REVIEW,MODELS
from scripts import scarb_grouped_context_candidate as c,scarb_grouped_provenance_candidate as p
from scripts import scarb_grouped_membership_candidate as m
from scripts import scarb_ai_fact_slots as solo
from scripts.scarb_accepted_copy import accepted_resolver

class EndToEndFixtureTests(unittest.TestCase):
 def test_two_canned_responses_pinned_proof_complete_mixed_draft(self):
  fixture=ContextProvenanceTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
  root=fixture.root;fixture.pin['solo_state_root']=str(root)
  transport=solo.FixtureTransport([fixture.env['author_response'],fixture.env['review_response']])
  raw_author=transport.exchange(fixture.env['author_request']);authors,_=c.v.unpack(raw_author)
  _,review_request=c.context_prompts(fixture.p,fixture.models,fixture.env['source_context'],authors)
  raw_review=transport.exchange(review_request)
  self.assertEqual(raw_review,fixture.env['review_response']);self.assertEqual(len(transport.calls),2)
  self.assertEqual(p._verify_pinned(root,fixture.pin,fixture.p)['packet_bindings'],fixture.pin['packet_bindings'])
  current=c.seam.current_canonical_requests();grouped=set(fixture.pin['packet_bindings']);config={'author_model':MODELS['author'],'reviewer_model':MODELS['reviewer']};receipts={}
  for identity,packet in current.items():
   if identity in grouped:continue
   r=solo.fixture_accept(packet,output(packet),REVIEW,config);r['packet_sha256']=c.v.digest(packet);r['sha256']=c.v.digest(r);receipts[identity]=r
  bundle={'solo_v1':{},'solo_v2':receipts,'grouped':[str(root)]}
  # Deliberately scoped adapters: preserve fixture origins, never relabel them.
  original=solo.receipt_check
  with patch.object(p,'TRUSTED_GROUPED_RUNS',{fixture.pin['manifest_sha256']:fixture.pin}),patch.object(solo,'receipt_check',lambda r,p,cfg:original(r,p,cfg,fixture=True)):
   draft=c.compile_admitted_mixed_draft(bundle,config)
   self.assertEqual(set(draft['entries']),set(current));self.assertEqual(len(draft['entries']),736)
   self.assertEqual(draft['version'],'scarb-mixed-production-draft-1')
   with self.assertRaises(ValueError):accepted_resolver(draft,{i:c.v.digest(x) for i,x in current.items()})
   removed=receipts.pop(next(iter(receipts)))
   with self.assertRaisesRegex(c.v.VoiceError,'736'):c.compile_admitted_mixed_draft(bundle,config)
  self.assertEqual(dict(p.TRUSTED_GROUPED_RUNS),{})
  with self.assertRaises(c.v.VoiceError):p.verify_grouped_provenance(root,fixture.p)

 def test_consumed_interruption_reopen_and_reverse(self):
  from scripts import scarb_packet_consumption_candidate as consumed
  zero={'reserved_nusd':0,'consumed_batches':{},'packet_membership':{}}
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ab={'A':c.v.digest('A'),'B':c.v.digest('B')}
   with c.v.exclusive(root):after=m.reserve_in_state(root,root,zero,ab,1)
   # Reopen without any author/reviewer result: reservation still blocks solo.
   with c.v.exclusive(root):
    with self.assertRaises(c.v.VoiceError):consumed.assert_unconsumed(root,{'B':ab['B']},expected_root=root)
    with self.assertRaises(c.v.VoiceError):m.reserve_in_state(root,root,after,{'B':ab['B'],'C':c.v.digest('C')},1)
    (root/'held').mkdir();(root/'held/solo.json').write_bytes(c.v.encoded({'packet_sha256':c.v.digest('D')}))
    with self.assertRaises(c.v.VoiceError):m.reserve_in_state(root,root,after,{'D':c.v.digest('D')},1)
    self.assertEqual(m.reserve_in_state(root,root,after,{'E':c.v.digest('E')},1)['reserved_nusd'],2)
if __name__=='__main__':unittest.main()
