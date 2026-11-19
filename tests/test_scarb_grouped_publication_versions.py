import copy,json,unittest,subprocess
from unittest.mock import patch
from tests.test_scarb_grouped_context_candidate import ContextProvenanceTests
from scripts import scarb_grouped_context_candidate as c
from scripts import scarb_grouped_provenance_candidate as v
from scripts.scarb_accepted_copy import accepted_resolver

class PublicationVersionTests(ContextProvenanceTests):
 def upgrade(self):
  tag=c.contract.CITATION_PROMPT
  authors,_=c.v.unpack(self.env['author_response'])
  a,r=c.context_prompts(self.p,self.models,self.env['source_context'],authors,prompt_version=tag)
  self.env.update(author_request=a,review_request=r,prompt_version=tag)
  self.pin['prompt_version']=tag;self.journal['prompt_version']=tag
  for stage,req in zip(self.journal['stages'],[a,r]):stage['request_sha256']=c.v.digest(req)
  self.cost_records();self.env['version']='scarb-grouped-run-envelope-3'
  self.seal.update(envelope_sha256=c.v.digest(self.env),journal_sha256=c.v.digest(self.journal));self.sync()
 def admitted_fixture(self):
  self.pin['solo_state_root']=str(self.root)
  return patch.object(v,'TRUSTED_GROUPED_RUNS',{self.pin['manifest_sha256']:self.pin})
 def test_version3_public_boundary_and_compiler_projection(self):
  self.upgrade()
  with self.admitted_fixture(),patch('scripts.scarb_grouped_membership_candidate.snapshot',return_value={}):
   self.assertEqual(v.verify_grouped_provenance(self.root,self.p)['packet_bindings'],self.pin['packet_bindings'])
   with patch.object(c.seam,'current_canonical_requests',return_value={p['id']:p for p in self.p}):
    draft=c.compile_admitted_mixed_draft({'solo_v1':{},'solo_v2':{},'grouped':[self.root]}, {})
  for identity,e in draft['entries'].items():
   self.assertEqual(e['origin'],'scarb-grouped-projection-3')
   self.assertEqual(e['provenance']['prompt_version'],c.contract.CITATION_PROMPT)
  # Full canonical compile constraint remains; only supply a fictional draft via its seam.
  current=c.seam.current_canonical_requests();entries={}
  for i,p in current.items():
   entries[i]={'text':'Fictional fixture','packet_sha256':c.v.digest(p),'receipt_sha256':'a'*64,'origin':'protected-verbatim'}
  entries.update(draft['entries'])
  with patch.object(c,'compile_admitted_mixed_draft',return_value={'entries':entries}):catalogue=c.compile_mixed_catalogue({}, {})
  expected={i:c.v.digest(p) for i,p in current.items()};accepted_resolver(catalogue,expected)
  self.assertTrue(js_resolves(catalogue,expected))
  i=self.p[0]['id']
  for tag in [None,'legacy-1','unknown']:
   altered=copy.deepcopy(catalogue)
   if tag is None:altered['entries'][i]['provenance'].pop('prompt_version')
   else:altered['entries'][i]['provenance']['prompt_version']=tag
   with self.assertRaises(ValueError):accepted_resolver(altered,expected)
 def test_version3_does_not_relax_bound_prompt_or_terminal(self):
  self.upgrade()
  for mutation in ['prompt','held']:
   with self.subTest(mutation=mutation):
    old=copy.deepcopy(self.journal)
    if mutation=='prompt':self.journal['prompt_version']='legacy-1'
    else:self.journal['status']='outcome-uncertain'
    self.sync()
    with self.admitted_fixture(),patch('scripts.scarb_grouped_membership_candidate.snapshot',return_value={}):
     with self.assertRaises(c.v.VoiceError):v.verify_grouped_provenance(self.root,self.p)
    self.journal=old

 def test_version3_adverse_review_cannot_be_resealed_into_acceptance(self):
  from tests.test_scarb_ai_voice import response,REVIEW
  self.upgrade()
  review=dict(REVIEW,approve=False,meaning_preserved=False,issues=['Synthetic adverse finding'])
  rr=response({p['id']:review for p in self.p});rr.update(id='context-reviewer',model=self.models['reviewer'])
  self.env['review_response']=rr
  _,usage=c.v.unpack(rr)
  self.journal['stages'][1].update(response_sha256=c.v.digest(rr),usage=usage)
  self.seal.update(envelope_sha256=c.v.digest(self.env),journal_sha256=c.v.digest(self.journal));self.sync()
  with self.admitted_fixture(),patch('scripts.scarb_grouped_membership_candidate.snapshot',return_value={}):
   with self.assertRaises(c.v.VoiceError):v.verify_grouped_provenance(self.root,self.p)


def js_resolves(catalogue,expected):
 script="""import {readFileSync} from 'node:fs';import {createScarbAiResolver} from './docs/scarb-ai-copy.mjs';const x=JSON.parse(readFileSync(0,'utf8'));try {const r=createScarbAiResolver(x.catalogue,x.expected);for(const k of Object.keys(x.expected)){if(r(k)!==x.catalogue.entries[k].text)throw Error('Mismatch');}console.log('true');}catch(e){console.log('false');}"""
 return subprocess.check_output(['node','--input-type=module','-e',script],input=json.dumps({'catalogue':catalogue,'expected':expected}),cwd=c.ROOT,encoding='utf8').strip()=='true'

class ResolverParityTests(unittest.TestCase):
 def test_shared_python_js_version_fixtures(self):
  expected={f'fixture.{i}':'a'*64 for i in range(736)}
  cat={'version':'scarb-ai-voice-mixed-1','entries':{i:{'text':'Fictional fixture.','packet_sha256':h,'receipt_sha256':'b'*64,'origin':'protected-verbatim'} for i,h in expected.items()}}
  for number in [2,3]:
   i=f'fixture.{number}';cat['entries'][i].update(origin=f'scarb-grouped-projection-{number}',provenance={'version':f'scarb-grouped-run-envelope-{number}','manifest_sha256':'b'*64,'packet_id':i})
   if number==3:cat['entries'][i]['provenance']['prompt_version']='numeric-citation-2'
  cases=[('mixed-positive',cat,True)]
  for name in ['missing-tag','legacy-tag','unknown-tag','extra-key','wrong-envelope','wrong-origin','wrong-id','wrong-manifest','unknown-envelope','legacy-extra-tag']:
   x=copy.deepcopy(cat);p=x['entries']['fixture.3']['provenance']
   if name=='missing-tag':p.pop('prompt_version')
   elif name=='legacy-tag':p['prompt_version']='legacy-1'
   elif name=='unknown-tag':p['prompt_version']='unknown'
   elif name=='extra-key':p['extra']=True
   elif name=='wrong-envelope':p['version']='scarb-grouped-run-envelope-2'
   elif name=='unknown-envelope':p['version']='scarb-grouped-run-envelope-9'
   elif name=='wrong-origin':x['entries']['fixture.3']['origin']='scarb-grouped-projection-2'
   elif name=='wrong-id':p['packet_id']='fixture.2'
   elif name=='wrong-manifest':p['manifest_sha256']='c'*64
   else:x['entries']['fixture.2']['provenance']['prompt_version']='numeric-citation-2'
   cases.append((name,x,False))
  for name,x,want in cases:
   with self.subTest(name=name):
    try:accepted_resolver(x,expected);python_ok=True
    except ValueError:python_ok=False
    self.assertEqual(python_ok,want);self.assertEqual(js_resolves(x,expected),want)
