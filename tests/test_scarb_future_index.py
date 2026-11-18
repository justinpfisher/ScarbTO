import copy,json,unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from scripts.build_weekly_brief import _render_index
from scripts.check_scarb_brief_index import verify_generated_index
from scripts.scarb_voice import copy as source_copy
class FutureIndexTests(unittest.TestCase):
 def setUp(self):self.manifest=json.loads(Path('docs/briefs/editions.json').read_text())
 def test_future_generation_uses_shared_accepted_keys_without_changing_manifest(self):
  original=copy.deepcopy(self.manifest)
  def accepted(key):return 'Accepted future index title' if key=='index-title' else source_copy(key)
  with patch('scripts.build_weekly_brief.voice_copy',side_effect=accepted),patch('scripts.build_weekly_brief.current_copy',side_effect=lambda key,draft:'Accepted heading' if key=='static.briefs-title' else draft):
   markup=_render_index(self.manifest,date(2026,11,9),date(2026,11,15),False).decode()
   self.assertIn('Accepted future index title',markup);self.assertIn('Accepted heading',markup)
   self.assertTrue(verify_generated_index(markup,self.manifest))
   with self.assertRaises(ValueError):verify_generated_index(markup.replace('revision 4','revision 999'),self.manifest)
  self.assertEqual(self.manifest,original)
 def test_no_new_week_or_availability_invention(self):
  markup=_render_index(self.manifest,date(2026,11,9),date(2026,11,15),False).decode()
  self.assertTrue(verify_generated_index(markup,self.manifest))
  with self.assertRaises(ValueError):verify_generated_index(markup.replace('data-scarb-has-current="false"','data-scarb-has-current="true"'),self.manifest)
  with self.assertRaises(ValueError):verify_generated_index(markup.replace('data-scarb-period-end="2026-11-15"','data-scarb-period-end="2026-11-16"'),self.manifest)
 def test_preserved_legacy_index_not_mistaken_for_fresh_generation(self):
  with self.assertRaises(ValueError):verify_generated_index(Path('docs/briefs/index.html').read_text(),self.manifest)


class RetainedCatalogueLifecycleTests(unittest.TestCase):
 def test_previous_accepted_index_survives_new_catalogue_without_revoice(self):
  # Resolver-only synthetic fixtures, not private receipt or API qualification.
  from scripts import scarb_accepted_copy as accepted
  from scripts.check_scarb_brief_index import verify_retained_generated_index
  drafts=json.loads(Path('config/scarb-python-copy-drafts.json').read_text(encoding='utf-8'))
  texts={'python.'+k:v for k,v in drafts.items()}
  texts.update({'static.briefs-title':'Earlier accepted heading','static.briefs-intro':'Earlier accepted introduction.'})
  texts['python.index-title']='Earlier accepted index title'
  expected={k:'a'*64 for k in texts}
  def catalogue(values):return {'version':'scarb-ai-voice-1','entries':{k:{'text':v,'packet_sha256':'a'*64,'receipt_sha256':'b'*64,'origin':'openai-api-reviewed'} for k,v in values.items()}}
  old=catalogue(texts);new=catalogue({**texts,'python.index-title':'New accepted title','static.briefs-title':'New accepted heading'})
  manifest=json.loads(Path('docs/briefs/editions.json').read_text())
  with patch.object(accepted,'_CURRENT',accepted.accepted_resolver(old,expected)),patch.object(accepted,'_LOADED',True):
   markup=_render_index(manifest,date(2026,11,9),date(2026,11,15),False).decode()
  new_resolver=accepted.accepted_resolver(new,expected)
  with patch.object(accepted,'_CURRENT',new_resolver),patch.object(accepted,'_LOADED',True):
   with self.assertRaises(ValueError):verify_generated_index(markup,manifest)
   self.assertTrue(verify_retained_generated_index(markup,manifest,old,expected))
   self.assertIs(accepted._CURRENT,new_resolver)
   for changed in [markup.replace('Earlier accepted heading','Unregistered hand edit'),markup.replace('revision 4','revision 999')]:
    with self.assertRaises(ValueError):verify_retained_generated_index(changed,manifest,old,expected)
   with self.assertRaises(ValueError):verify_retained_generated_index(markup,manifest,None,expected)
