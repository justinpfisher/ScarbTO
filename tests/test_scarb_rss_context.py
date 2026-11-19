import unittest,copy,tempfile,shutil
from pathlib import Path
from scripts import scarb_grouped_context_candidate as c,scarb_rss_contexts as r,scarb_voice as voice
class RSSContextTests(unittest.TestCase):
 def test_six_exact_templates_and_rendered_optional_fields(self):
  cur=c.seam.current_canonical_requests();ps=[cur['python.'+k] for k in r.EXPECTED];ctx=c.current_contexts(ps);self.assertEqual(len(ctx),6)
  event={'neighbourhood':'Synthetic matched area','previous_status':None,'source_url':'https://open.toronto.ca/dataset/dinesafe/','status':'Pass'}
  text=voice.rss_description(event,inspection_date='Monday, January 1, 2024',observed_date='Tuesday, January 2, 2024')
  self.assertNotIn(voice.compose_copy('rss-previous',{'STATUS':'Closed'}),text)
  event['previous_status']='Closed';changed=voice.rss_description(event,inspection_date='Monday, January 1, 2024',observed_date='Tuesday, January 2, 2024')
  self.assertIn(voice.compose_copy('rss-previous',{'STATUS':'Closed'}),changed)
  for key in ('coordinate-limits','safety'):self.assertIn(voice.copy(key),changed)
  for p in ps:self.assertEqual(ctx[p['id']]['locks'],p['locks'])
  for j in (0,3):
   b=ps[j:j+3];self.assertLessEqual(len(c.v.encoded(c.context_prompts(b,{'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'},{p['id']:ctx[p['id']] for p in b}))),48000)
 def test_source_policy_draft_and_multiplicity_fail_closed(self):
  cur=c.seam.current_canonical_requests();p=cur['python.rss-observed']
  for mutation in ('draft','lock','extra'):
   x=copy.deepcopy(p)
   if mutation=='draft':x['draft']+=' tomorrow'
   elif mutation=='lock':x['locks']['VALUE_1']='{{OTHER}}'
   else:x['evidence'].append(x['evidence'][0])
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):r.contexts([x])
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for f in list(r.SOURCE_PINS)+['config/scarb-python-copy-drafts.json','config/scarb-python-copy-classifications.json']:
    q=root/f;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(c.ROOT/f,q)
   q=root/'scripts/build_rss.py';q.write_text(q.read_text(encoding='utf-8').replace("ZoneInfo('America/Toronto')","ZoneInfo('UTC')"),encoding='utf-8')
   with self.assertRaises(ValueError):r.contexts([p],root)

 def test_four_channel_templates_and_actual_caller(self):
  from scripts import build_rss
  from datetime import datetime,timezone
  import xml.etree.ElementTree as ET
  cur=c.seam.current_canonical_requests();ps=[cur['python.'+k] for k in r.CHANNEL_EXPECTED];ctx=c.current_contexts(ps)
  self.assertEqual(len(ctx),4)
  channel=ET.fromstring(build_rss.build_feed([],built_at=datetime(2026,1,1,tzinfo=timezone.utc))).find('channel')
  self.assertEqual(channel.findtext('title'),voice.copy('rss-title'))
  for key in ('rss-intro','rss-limits'):self.assertIn(voice.copy(key),channel.findtext('description'))
  self.assertIn(voice.compose_copy('rss-licence-link',{'URL':build_rss.LICENCE_URL}),channel.findtext('description'))
  self.assertEqual(r.LICENCE_URL,build_rss.LICENCE_URL)
  for key in r.CHANNEL_EXPECTED:
   q=ctx['python.'+key];self.assertEqual(q['locks'],cur['python.'+key]['locks'])
   self.assertEqual(q['parameters'],{'URL':build_rss.LICENCE_URL} if key=='rss-licence-link' else {})
   self.assertEqual(q['field'],'URL' if key=='rss-licence-link' else None)
  for batch in (ps[:3],ps[3:]):
   body=c.context_prompts(batch,{'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'},{p['id']:ctx[p['id']] for p in batch},prompt_version='numeric-citation-2')
   self.assertLessEqual(len(c.v.encoded(body)),48000)
 def test_channel_contract_mutations_rejected(self):
  cur=c.seam.current_canonical_requests()
  for key in r.CHANNEL_EXPECTED:
   for kind in ('draft','class','evidence','locks'):
    p=copy.deepcopy(cur['python.'+key])
    if kind=='draft':p['draft']+=' new claim'
    elif kind=='class':p['kind']='unknown'
    elif kind=='evidence':p['evidence'][0]['source']='repo:wrong'
    else:p['locks']['VALUE_0']='changed'
    with self.subTest(key=key,kind=kind),self.assertRaises(ValueError):r.contexts([p])
  with self.assertRaises(ValueError):r.contexts([cur['python.licence']])
