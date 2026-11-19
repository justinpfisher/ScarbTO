import unittest,subprocess,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CommunityValidationContextTests(unittest.TestCase):
 def run_source(self,source):return subprocess.run(['node','--input-type=module'],input=source,text=True,encoding='utf8',capture_output=True,cwd=ROOT/'scripts')
 def test_exact_validation_family_and_predicates(self):
  r=subprocess.run(['node',str(ROOT/'scripts/scarb_community_validation_contexts.mjs')],capture_output=True,text=True,encoding='utf8',check=True);c=json.loads(r.stdout)
  self.assertEqual(set(c),{'static.community-publishing-message-'+str(i).zfill(2) for i in range(2,38)})
  self.assertEqual(sum(v['classification']['kind']=='functional' for v in c.values()),20);self.assertEqual(sum(v['classification']['kind']=='safety' for v in c.values()),16)
  for n in (7,9):self.assertEqual(c['static.community-publishing-message-'+str(n).zfill(2)]['locks'],{'VALUE_0':'40'})
  self.assertEqual(c['static.community-publishing-message-19']['locks'],{'VALUE_0':'Scarborough'})
  for k,v in c.items():self.assertIn("staticCopy('"+k.removeprefix('static.')+"')",v['trigger_predicate']);self.assertIn('fail(',v['trigger_predicate']);self.assertTrue(v['enclosing_function'])
 def test_source_and_packet_mutations_fail_closed(self):
  source=(ROOT/'scripts/scarb_community_validation_contexts.mjs').read_text(encoding='utf8')
  bad=re.sub(r'sourceHash==="[a-f0-9]{64}"','sourceHash==="'+'0'*64+'"',source)
  self.assertNotEqual(self.run_source(bad).returncode,0)
  bad=source.replace("sha(p)===expected[identity]","sha(p)==='"+'0'*64+"'")
  self.assertNotEqual(self.run_source(bad).returncode,0)

 def test_runtime_exact_loader_and_excluded_key(self):
  from scripts import scarb_grouped_context_candidate as c
  current=c.seam.current_canonical_requests();ps=[current['static.community-publishing-message-'+str(n).zfill(2)] for n in range(2,38)]
  contexts=c.current_contexts(ps);self.assertEqual(len(contexts),36)
  for p in ps:self.assertEqual(contexts[p['id']]['locks'],p['locks'])
  with self.assertRaises(ValueError):c.current_contexts([current['static.community-publishing-message-01']])
  import copy
  bad=copy.deepcopy(ps[0]);bad['draft']+=' extra'
  with self.assertRaises(ValueError):c.current_contexts([bad])
