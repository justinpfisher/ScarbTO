"""Offline production candidate; no bridge wiring, registry grant or writes."""
import json,hashlib
from pathlib import Path
from scripts import scarb_ai_voice as v,scarb_ai_fact_slots as solo
from scripts import scarb_grouped_fixture_envelope as contract
from scripts import scarb_grouped_projection_seam as seam
from scripts import scarb_grouped_provenance_candidate as provenance
ROOT=Path(__file__).resolve().parents[1]
ANCHORS={'shell.shell-b04b38d4-007':('/neighbourhoods/','Neighbourhoods'),'shell.shell-b04b38d4-008':('/briefs/','Weekly briefs')}

def current_contexts(packets):
 current=seam.current_canonical_requests();path=ROOT/'docs/index.html';raw=path.read_bytes();text=raw.decode('utf8');contexts={}
 for packet in packets:
  identity=packet['id'];v.need(identity in ANCHORS and current.get(identity)==packet,'Unsupported or stale context producer')
  destination,label=ANCHORS[identity];anchor=f'<a href="{destination}" class="about-link">{label}</a>'
  v.need(text.count(anchor)==1 and packet['draft']==label,'Exact unique source anchor missing')
  contexts[identity]={'path':'docs/index.html','source_sha256':hashlib.sha256(raw).hexdigest(),'anchor_html':anchor,'destination':destination,'meaning':'Existing navigation label only; preserve its destination and unambiguous function; no new claims.'}
 return contexts

def context_prompts(packets,models,contexts,authors=None):
 v.need(isinstance(contexts,dict) and set(contexts)==set(contract.identities(packets)),'Missing or extra source context')
 bodies=contract.prompts(packets,models,authors)
 def bind(body):
  payload=json.loads(body['input'][0]['content'][0]['text']);payload['source_context']=contexts
  body['input'][0]['content'][0]['text']=json.dumps(payload,sort_keys=True,separators=(',',':'))
  v.need(len(v.encoded(body))<=48000,'Context exceeds input bound');return body
 return bind(bodies) if authors is None else tuple(bind(x) for x in bodies)

def compile_admitted_mixed_draft(bundle,config):
 """Pure disabled-by-empty-registry candidate. Not a production-reader artifact."""
 v.need(set(bundle)=={'solo_v1','solo_v2','grouped'},'Mixed input fields')
 current=seam.current_canonical_requests();entries={}
 for key,checker in [('solo_v1',v.receipt_check),('solo_v2',solo.receipt_check)]:
  for identity,receipt in bundle[key].items():
   v.need(identity in current and identity not in entries,'Unknown or duplicate solo ID')
   text=checker(receipt,current[identity],config)
   entries[identity]={'text':text,'packet_sha256':v.digest(current[identity]),'receipt_sha256':receipt['sha256'],'origin':receipt['origin']}
 for root in bundle['grouped']:
  # Registry pin selects members: caller-supplied envelope cannot grant membership.
  digest=provenance.file_hash(Path(root)/'manifest.json');pin=provenance.TRUSTED_GROUPED_RUNS.get(digest)
  v.need(pin is not None,'No admitted grouped run')
  ids=list(pin['packet_bindings']);v.need(all(i in current and i not in entries for i in ids),'Unknown or overlapping group')
  packets=[current[i] for i in ids];proof=provenance.verify_grouped_provenance(root,packets)
  env=json.loads((Path(root)/'envelope.json').read_text(encoding='utf8'));authors,_=v.unpack(env['author_response'])
  for packet in packets:
   identity=packet['id'];text=v.text_check(packet,solo.assemble(packet,authors[identity]))
   v.need(v.digest(text)==proof['text_sha256'][identity],'Verified projection differs')
   entries[identity]={'text':text,'packet_sha256':v.digest(packet),'receipt_sha256':digest,'origin':'scarb-grouped-projection-2'}
 v.need(set(entries)==set(current),'Missing full 736-item current catalogue')
 return {'version':'scarb-mixed-production-draft-1','entries':entries}


def compile_mixed_catalogue(bundle,config):
 """Compile only privately admitted receipts; never promote a supplied draft.
 Public metadata identifies grouped provenance without exposing private records.
 """
 draft=compile_admitted_mixed_draft(bundle,config)
 current=seam.current_canonical_requests()
 v.need(len(current)==736 and set(draft['entries'])==set(current),'Complete current 736-item catalogue required')
 entries={}
 for identity,item in draft['entries'].items():
  entry=dict(item)
  if entry['origin']=='scarb-grouped-projection-2':
   entry['provenance']={'version':'scarb-grouped-run-envelope-2','manifest_sha256':entry['receipt_sha256'],'packet_id':identity}
  entries[identity]=entry
 catalogue={'version':'scarb-ai-voice-mixed-1','entries':entries}
 from scripts.scarb_accepted_copy import accepted_resolver
 accepted_resolver(catalogue,{i:v.digest(p) for i,p in current.items()})
 return catalogue


def verify_mixed_catalogue(bundle,config,artifact):
 """Recompile from original admitted evidence; no caller-provided trust claims."""
 path=Path(artifact)
 v.need(path.is_file() and path.stat().st_size<=10*1024*1024,'Mixed catalogue missing or oversized')
 actual=json.loads(path.read_text(encoding='utf8'))
 v.need(v.encoded(actual)==v.encoded(compile_mixed_catalogue(bundle,config)),'Mixed catalogue differs from admitted receipts')
 return True
