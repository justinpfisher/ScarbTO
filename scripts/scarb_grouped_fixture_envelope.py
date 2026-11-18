"""Offline grouped-envelope prototype. No transport, credentials, files or admission."""
import copy
from scripts import scarb_ai_fact_slots as f,scarb_ai_voice as v
VERSION='scarb-grouped-envelope-prototype-1'
ORIGIN='test-fixture-grouped-envelope'
AUTHOR=f.AUTHOR+'\nReturn an independent result for each exact ID. Evidence and meaning may not cross items.'
LEGACY_PROMPT='legacy-1'
CITATION_PROMPT='numeric-citation-2'
CITATION_RULE='\nNumeric citations in evidence (including section, regulation and clause numbers) are not permission to add their digits to prose. Include them only through an existing authorized protected slot; never invent a slot or reproduce its value. Preserve supported meaning without adding citation numbers. Never omit a material condition to make output pass; when safe representation is impossible, the existing fail-closed hold applies. Keep the output schema unchanged.'
def author_instruction(version):
 v.need(version in (LEGACY_PROMPT,CITATION_PROMPT),'Unknown grouped prompt version')
 return AUTHOR if version==LEGACY_PROMPT else AUTHOR+CITATION_RULE
REVIEWER=f.REVIEWER+'\nReturn an independent verdict for each exact ID. Evaluate each only against its evidence.'
def identities(packets):
 v.need(isinstance(packets,list) and 1<=len(packets)<=3,'Invalid batch size')
 for p in packets:f.schema(p)
 ids=[p['id'] for p in packets];v.need(len(set(ids))==len(ids),'Duplicate IDs');return ids
def check_membership(result,ids):
 v.need(isinstance(result,dict) and set(result)==set(ids),'Missing or extra ID')
def prompts(packets,models,authors=None,*,prompt_version=LEGACY_PROMPT):
 ids=identities(packets)
 v.need(set(models)=={'author','reviewer'} and models['author']!=models['reviewer'] and all(x in v.MODELS for x in models.values()),'Independent qualified models required')
 a=v.request_body(models['author'],author_instruction(prompt_version),{'requests':packets},v.object_schema({p['id']:f.schema(p) for p in packets}))
 if authors is None:return a
 check_membership(authors,ids);items=[]
 for p in packets:
  w=f.assemble(p,authors[p['id']]);items.append({'request':p,'candidate':w,'materialised_text':v.text_check(p,w)})
 r=v.request_body(models['reviewer'],REVIEWER,{'requests':items},v.object_schema({i:v.REVIEW_SCHEMA for i in ids}))
 v.need(len(v.encoded(a))<=48000 and len(v.encoded(r))<=48000,'Envelope input limit')
 return a,r
class FixtureJournal:
 def __init__(self,sealed=()):self.sealed=set(sealed)|set(f.SEALED_PACKET_SHA256);self.held=set();self.consumed=set()
 def begin(self,packets):
  identities(packets);hashes={v.digest(p) for p in packets}
  v.need(not hashes.intersection(self.sealed|self.held|self.consumed),'Source already dispatched or sealed')
  self.held.update(hashes);self.consumed.update(hashes)
 def finish(self,packets):self.held.difference_update(v.digest(p) for p in packets)
def make_fixture(packets,models,authors,reviews,journal):
 journal.begin(packets)
 ids=identities(packets);a,r=prompts(packets,models,authors);check_membership(reviews,ids)
 items={}
 for p in packets:
  key=p['id'];w=f.assemble(p,authors[key]);v.review_check(reviews[key])
  items[key]={'packet_sha256':v.digest(p),'author':copy.deepcopy(authors[key]),'review':copy.deepcopy(reviews[key]),'text':v.text_check(p,w)}
 e={'version':VERSION,'origin':ORIGIN,'packets':copy.deepcopy(packets),'models':copy.deepcopy(models),'author_request':a,'review_request':r,'items':items}
 e['sha256']=v.digest(e);verify_fixture(e,packets,models);journal.finish(packets);return e

def verify_fixture(e,expected_packets,expected_models):
 v.need(isinstance(e,dict) and set(e)=={'version','origin','packets','models','author_request','review_request','items','sha256'},'Envelope fields')
 v.need(e['version']==VERSION and e['origin']==ORIGIN,'Not a qualified prototype fixture')
 v.need(e['sha256']==v.digest({k:x for k,x in e.items() if k!='sha256'}),'Envelope hash')
 v.need(v.encoded(e['packets'])==v.encoded(expected_packets) and e['models']==expected_models,'Current batch changed')
 ids=identities(expected_packets);check_membership(e['items'],ids)
 authors={i:e['items'][i]['author'] for i in ids};a,r=prompts(expected_packets,expected_models,authors)
 v.need(e['author_request']==a and e['review_request']==r,'Prompt/schema/model provenance changed')
 for p in expected_packets:
  x=e['items'][p['id']];v.need(set(x)=={'packet_sha256','author','review','text'},'Per-ID fields')
  v.need(x['packet_sha256']==v.digest(p),'Cross-item packet mismatch')
  w=f.assemble(p,x['author']);v.review_check(x['review']);v.need(x['text']==v.text_check(p,w),'Projection text differs')
 return True

def project_fixture(e,key,packets,models):
 verify_fixture(e,packets,models);v.need(key in e['items'],'Unknown projection')
 return {'version':VERSION+'-view','origin':ORIGIN,'envelope_sha256':e['sha256'],'id':key,'item':copy.deepcopy(e['items'][key])}
def verify_projection(view,e,packets,models):
 v.need(view==project_fixture(e,view.get('id'),packets,models),'Detached or altered projection');return True
