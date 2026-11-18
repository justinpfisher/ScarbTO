"""Offline exact RSS fact-label contexts; no feed generation or event ingestion."""
import json,hashlib,re
from pathlib import Path
from scripts import scarb_ai_voice as v
ROOT=Path(__file__).resolve().parents[1]
SOURCE_PINS={'scripts/scarb_voice.py': ['eaa22ee4c6bb8f15eaa972d0bf6ddebe8db4c5929f17de8f33608232f0a8480b', '48921ff3372649708e9ed3405a31aa824b9d6f76da71f86c17d9a79b4beb2e45'], 'scripts/build_rss.py': ['d4bf13696c8264193ffdf8c1cdb3c55cabcbe469f10bac42d8e16c7888edb02e', '534ba93e7da4c9b9bc0b21323e818c9590483f0613833783b95b765d6999482a']}
EXPECTED={'rss-neighbourhood': 'Neighbourhood matched by Scarb.TO: {{NAME}}.', 'rss-previous': 'Previous DineSafe status: {{STATUS}}.', 'rss-source': 'City source dataset: {{URL}}.', 'rss-result': 'DineSafe result when added: {{STATUS}}.', 'rss-inspection': 'Inspection date: {{DATE}}.', 'rss-observed': 'Added to Scarb.TO: {{DATE}}. This is when I first recorded the update, not the inspection date.'}

FIELDS={'rss-neighbourhood':('NAME','event.neighbourhood: source-coordinate matched neighbourhood, not claimed local presence'),'rss-previous':('STATUS','optional event.previous_status, only emitted when present; never infer a previous result'),'rss-source':('URL','allowlisted https://open.toronto.ca/dataset/dinesafe/ dataset URL'),'rss-result':('STATUS','event.status at first recording of the event, not current safety'),'rss-inspection':('DATE','event.inspection_date as a calendar date; not observation or publication date'),'rss-observed':('DATE','event.detected_at converted to America/Toronto calendar date; first recorded change, not inspection or upstream publication')}
def contexts(packets,root=ROOT):
 root=Path(root);sources={}
 for name,pins in SOURCE_PINS.items():
  h=hashlib.sha256((root/name).read_bytes()).hexdigest();v.need(h in pins,'Reviewed RSS renderer/caller changed');sources[name]=h
 drafts=json.loads((root/'config/scarb-python-copy-drafts.json').read_text(encoding='utf-8'));classes=json.loads((root/'config/scarb-python-copy-classifications.json').read_text(encoding='utf-8'));out={}
 for p in packets:
  key=p['id'].removeprefix('python.');v.need(p['id']=='python.'+key and key in EXPECTED,'Unsupported RSS label')
  text=drafts[key];v.need(text==EXPECTED[key],'RSS source template changed');v.need([p['surface'],p['kind']]==classes[key],'RSS classification changed')
  material=p['draft']
  for k,value in p['locks'].items():material=material.replace('{{LOCK:'+k+'}}',value)
  v.need(material==text,'RSS packet/locks differ from template')
  field,meaning=FIELDS[key];v.need(re.findall(r'\{\{([A-Z]+)\}\}',text)==[field],'RSS placeholder multiplicity changed')
  v.need(len(p['evidence'])==1 and p['evidence'][0]=={'id':'python-copy.'+key,'source':'repo:config/scarb-python-copy-drafts.json#'+key,'sha256':v.digest(text),'fact':text},'RSS evidence differs')
  out[p['id']]={'source_sha256':sources,'template_sha256':v.digest(text),'renderer':'scripts/scarb_voice.py::rss_description -> compose_copy','caller':'scripts/build_rss.py::load_events/build_feed','field':field,'field_meaning':meaning,'locks':p['locks'],'meaning':'RSS fact-label template only, no actual event supplied. Preserve placeholder exactly once, dated source meaning, optional prior result and source-coordinate matched provenance. Adjacent coordinate-limits and safety clauses remain unchanged; do not claim current safety or alter RSS identity/timestamps.'}
 return out
