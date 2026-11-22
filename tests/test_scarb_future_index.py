import copy,hashlib,json,unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from scripts.build_weekly_brief import _render_index
from scripts.check_scarb_brief_index import verify_generated_index
from scripts.scarb_voice import copy as source_copy


def unissued_week(manifest):
    first_issued = min(date.fromisoformat(row['period_start']) for row in manifest['editions'])
    return first_issued - timedelta(days=7), first_issued - timedelta(days=1)


class FutureIndexTests(unittest.TestCase):
 def setUp(self):self.manifest=json.loads(Path('docs/briefs/editions.json').read_text())
 def test_future_generation_uses_shared_accepted_keys_without_changing_manifest(self):
  original=copy.deepcopy(self.manifest)
  def accepted(key):return 'Accepted future index title' if key=='index-title' else source_copy(key)
  with patch('scripts.build_weekly_brief.voice_copy',side_effect=accepted),patch('scripts.build_weekly_brief.current_copy',side_effect=lambda key,draft:'Accepted heading' if key=='static.briefs-title' else draft):
   markup=_render_index(self.manifest,*unissued_week(self.manifest),False).decode()
   self.assertIn('Accepted future index title',markup);self.assertIn('Accepted heading',markup)
   self.assertTrue(verify_generated_index(markup,self.manifest))
   with self.assertRaises(ValueError):verify_generated_index(markup.replace('revision 4','revision 999'),self.manifest)
  self.assertEqual(self.manifest,original)
 def test_no_new_week_or_availability_invention(self):
  start,end=unissued_week(self.manifest)
  markup=_render_index(self.manifest,start,end,False).decode()
  self.assertTrue(verify_generated_index(markup,self.manifest))
  with self.assertRaises(ValueError):verify_generated_index(markup.replace('data-scarb-has-current="false"','data-scarb-has-current="true"'),self.manifest)
  with self.assertRaises(ValueError):verify_generated_index(markup.replace(f'data-scarb-period-end="{end}"',f'data-scarb-period-end="{end+timedelta(days=1)}"'),self.manifest)
 def test_preserved_legacy_index_not_mistaken_for_fresh_generation(self):
  with self.assertRaises(ValueError):verify_generated_index(Path('docs/briefs/index.html').read_text(),self.manifest)


class RetainedCatalogueLifecycleTests(unittest.TestCase):
 def test_legacy_retained_index_accepts_only_exact_windows_checkout_forms(self):
  from scripts import check_scarb_brief_index as check
  index=b'<main>\n<a href="/briefs/2026-11-09/">Issued edition</a>\n</main>\n'
  registry=b'{\n  "schema_version": 1,\n  "editions": []\n}\n'
  windows=lambda raw:raw.replace(b'\n',b'\r\n')
  with patch.object(check.sys,'platform','win32'):
   for canonical in (index,registry):
    self.assertEqual(check._retained_git_bytes(canonical,canonical),canonical)
    self.assertEqual(check._retained_git_bytes(windows(canonical),canonical),canonical)
    with self.assertRaisesRegex(ValueError,'checkout differs'):
     check._retained_git_bytes(canonical.replace(b'\n',b'\r\n',1),canonical)
   with self.assertRaisesRegex(ValueError,'checkout differs'):
    check._retained_git_bytes(windows(index.replace(b'/2026-11-09/',b'/2026-11-16/')),index)
  with patch.object(check.sys,'platform','linux'):
   for canonical in (index,registry):
    self.assertEqual(check._retained_git_bytes(canonical,canonical),canonical)
    with self.assertRaisesRegex(ValueError,'checkout differs'):
     check._retained_git_bytes(windows(canonical),canonical)
  with patch.object(check,'_PRE_GATEWAY_SHA256',hashlib.sha256(index).hexdigest()):
   revision=check._PRE_GATEWAY_INDEX
   self.assertTrue(check.verify_pre_gateway_index(revision,index,registry,registry))
   with self.assertRaises(ValueError):
    check.verify_pre_gateway_index(revision,windows(index),registry,registry)
   with self.assertRaises(ValueError):
    check.verify_pre_gateway_index(revision,index,windows(registry),registry)
   with self.assertRaises(ValueError):
    check.verify_pre_gateway_index('0'*40,index,registry,registry)

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
   markup=_render_index(manifest,*unissued_week(manifest),False).decode()
  new_resolver=accepted.accepted_resolver(new,expected)
  with patch.object(accepted,'_CURRENT',new_resolver),patch.object(accepted,'_LOADED',True):
   with self.assertRaises(ValueError):verify_generated_index(markup,manifest)
   self.assertTrue(verify_retained_generated_index(markup,manifest,old,expected))
   self.assertIs(accepted._CURRENT,new_resolver)
   for changed in [markup.replace('Earlier accepted heading','Unregistered hand edit'),markup.replace('revision 4','revision 999')]:
    with self.assertRaises(ValueError):verify_retained_generated_index(changed,manifest,old,expected)
   with self.assertRaises(ValueError):verify_retained_generated_index(markup,manifest,None,expected)
