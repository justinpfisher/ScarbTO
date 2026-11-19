import copy,unittest
from tests.test_scarb_grouped_provenance import ProvenanceTests,provenance,group,response,REVIEW,v
class SealedOrderTests(unittest.TestCase):
 def setUp(self):
  f=ProvenanceTests();f.setUp();self.addCleanup(f.doCleanups);self.f=f
  p=f.p[0];f.p=[dict(copy.deepcopy(p),id='diagnostic.z'),dict(copy.deepcopy(p),id='diagnostic.a')]
  authors={p['id']:{'slots':{},'tail':'Browse sample','evidence_ids':['fixture.source']} for p in f.p};reviews={p['id']:REVIEW for p in f.p}
  a,r=group.prompts(f.p,f.models,authors);ar=response(authors);rr=response(reviews);ar.update(id='fixture-author',model=f.models['author']);rr.update(id='fixture-reviewer',model=f.models['reviewer'])
  f.env.update(packets=f.p,author_request=a,review_request=r,author_response=ar,review_response=rr)
  bindings={p['id']:v.digest(p) for p in f.p};f.pin['packet_bindings']=bindings;f.journal['packet_bindings']=bindings;f.journal['stages']=[]
  for role,req,res in [('author',a,ar),('reviewer',r,rr)]:
   _,usage=v.unpack(res);f.journal['stages'].append({'role':role,'request_sha256':v.digest(req),'response_sha256':v.digest(res),'response_id':res['id'],'model':res['model'],'usage':usage})
  f.seal.update(packet_bindings=bindings,envelope_sha256=v.digest(f.env),journal_sha256=v.digest(f.journal));f.cost_records();f.sync()
 def test_serialized_map_order_does_not_rewrite_sealed_order(self):
  f=self.f;raw=(f.root/'envelope.json').read_bytes();self.assertEqual(provenance._verify_pinned(f.root,f.pin,list(reversed(f.p)))['packet_bindings'],f.pin['packet_bindings']);self.assertEqual(raw,(f.root/'envelope.json').read_bytes())
 def test_missing_extra_duplicate_current_rejected(self):
  f=self.f
  for packets in [f.p[:1],f.p+[dict(f.p[0],id='extra')],f.p+[f.p[0]]]:
   with self.assertRaises(v.VoiceError):provenance._verify_pinned(f.root,f.pin,packets)
 def test_modified_current_fact_rejected(self):
  f=self.f;packets=copy.deepcopy(f.p);packets[0]['draft']='Changed'
  with self.assertRaises(v.VoiceError):provenance._verify_pinned(f.root,f.pin,packets)
 def test_tampered_sealed_bytes_rejected(self):
  f=self.f;(f.root/'envelope.json').write_bytes(b'{}')
  with self.assertRaises(v.VoiceError):f.verify()
 def test_reordered_or_duplicate_envelope_cannot_substitute_bound_requests(self):
  f=self.f
  for ps in [list(reversed(f.p)),[f.p[0],f.p[0]]]:
   f.env['packets']=ps;f.seal['envelope_sha256']=v.digest(f.env);f.sync()
   with self.assertRaises(v.VoiceError):f.verify()
