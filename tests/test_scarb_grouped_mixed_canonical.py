import json,re,tempfile,unittest,copy
from pathlib import Path
from scripts import scarb_grouped_projection_seam as seam
from scripts import scarb_grouped_fixture_envelope as group
from scripts.scarb_accepted_copy import accepted_resolver
v=seam.v;f=group.f
MODELS={'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'}
REVIEW={'approve':True,'meaning_preserved':True,'limitations_preserved':True,'voice_pass':True,'issues':[]}
def output(p):
 slots={};pos=0
 for rank,m in enumerate(re.finditer(r'\{\{LOCK:([^}]+)\}\}',p['draft'])):
  slots[m[1]]={'rank':rank,'before':p['draft'][pos:m.start()]};pos=m.end()
 return {'slots':slots,'tail':p['draft'][pos:],'evidence_ids':[x['id'] for x in p['evidence']]}
class CanonicalMixedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.current=seam.current_canonical_requests();cls.group_ids=['shell.shell-b04b38d4-007','shell.shell-b04b38d4-008']
  packets=[cls.current[i] for i in cls.group_ids]
  envelope=group.make_fixture(packets,MODELS,{p['id']:output(p) for p in packets},{p['id']:REVIEW for p in packets},group.FixtureJournal())
  cls.grouped={'envelope':envelope,'projections':{p['id']:group.project_fixture(envelope,p['id'],packets,MODELS) for p in packets}}
 def bundle(self,full=False):
  ids=[i for i in self.current if i not in self.group_ids] if full else ['shell.shell-b04b38d4-039','shell.shell-b04b38d4-040'];solo={}
  for i in ids:
   p=self.current[i];r=f.fixture_accept(p,output(p),REVIEW,{'author_model':MODELS['author'],'reviewer_model':MODELS['reviewer']});r['packet_sha256']=v.digest(p);r['sha256']=v.digest(r);solo[i]=r
  return {'origin':'test-fixture-mixed-catalogue','solo_v2':solo,'grouped':[copy.deepcopy(self.grouped)]}
 def compile(self,bundle):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'mixed-fixture.json';path.write_text(json.dumps(bundle),encoding='utf-8');return seam.compile_mixed_fixture_file(path,MODELS)
 def test_complete_mixed_fixture_matches_regenerated_manifest_but_not_production(self):
  result=self.compile(self.bundle(full=True));self.assertEqual(len(result['entries']),len(self.current));self.assertEqual(len(self.current),736)
  with self.assertRaises(ValueError):accepted_resolver(result,{i:v.digest(p) for i,p in self.current.items()})
 def test_four_items_cannot_supply_own_smaller_manifest(self):
  with self.assertRaisesRegex(v.VoiceError,'full canonical'):self.compile(self.bundle())
 def test_solo_tamper_checked_before_completeness(self):
  b=self.bundle();b['solo_v2']['shell.shell-b04b38d4-039']['text']='altered'
  with self.assertRaisesRegex(v.VoiceError,'receipt changed'):self.compile(b)
 def test_grouped_stale_packet_checked_before_completeness(self):
  b=self.bundle();b['grouped'][0]['envelope']['packets'][0]['draft']='changed'
  with self.assertRaisesRegex(v.VoiceError,'current packet mismatch'):self.compile(b)
if __name__=='__main__':unittest.main()
