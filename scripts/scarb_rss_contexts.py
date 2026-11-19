"""Offline exact RSS fact-label contexts; no feed generation or event ingestion."""
import json,hashlib,re
from pathlib import Path
from scripts import scarb_ai_voice as v
ROOT=Path(__file__).resolve().parents[1]
SOURCE_PINS={'scripts/scarb_voice.py': ['eaa22ee4c6bb8f15eaa972d0bf6ddebe8db4c5929f17de8f33608232f0a8480b', '48921ff3372649708e9ed3405a31aa824b9d6f76da71f86c17d9a79b4beb2e45'], 'scripts/build_rss.py': ['d4bf13696c8264193ffdf8c1cdb3c55cabcbe469f10bac42d8e16c7888edb02e', '534ba93e7da4c9b9bc0b21323e818c9590483f0613833783b95b765d6999482a']}
EXPECTED={'rss-neighbourhood': 'Neighbourhood matched by Scarb.TO: {{NAME}}.', 'rss-previous': 'Previous DineSafe status: {{STATUS}}.', 'rss-source': 'City source dataset: {{URL}}.', 'rss-result': 'DineSafe result when added: {{STATUS}}.', 'rss-inspection': 'Inspection date: {{DATE}}.', 'rss-observed': 'Added to Scarb.TO: {{DATE}}. This is when I first recorded the update, not the inspection date.'}

FIELDS={'rss-neighbourhood':('NAME','event.neighbourhood: source-coordinate matched neighbourhood, not claimed local presence'),'rss-previous':('STATUS','optional event.previous_status, only emitted when present; never infer a previous result'),'rss-source':('URL','allowlisted https://open.toronto.ca/dataset/dinesafe/ dataset URL'),'rss-result':('STATUS','event.status at first recording of the event, not current safety'),'rss-inspection':('DATE','event.inspection_date as a calendar date; not observation or publication date'),'rss-observed':('DATE','event.detected_at converted to America/Toronto calendar date; first recorded change, not inspection or upstream publication')}
CHANNEL_EXPECTED={'rss-title': 'Scarb.TO food inspection updates', 'rss-intro': "A familiar place, a dated inspection, another detail to follow: here is Scarborough's DineSafe paper trail. I bring the recorded updates together with their City sources so you can check the details yourself.", 'rss-limits': "Inspection dates come from City records; added dates show when I first recorded each change. The City status may have changed since. A place newly added here is not necessarily a new business. Scarb.TO's editorial voice is AI-assisted, not first-hand reporting.", 'rss-licence-link': 'Licence: {{URL}}'}
CHANNEL_CLASSES={'rss-title': ['rss', 'functional'], 'rss-intro': ['rss', 'editorial'], 'rss-limits': ['rss', 'safety'], 'rss-licence-link': ['source-note', 'functional']}
LICENCE_URL='https://open.toronto.ca/open-data-licence/'
CHANNEL_MEANINGS={
 'rss-title':'Channel title describing Scarb.TO food inspection updates, not a current safety verdict.',
 'rss-intro':'Channel introduction to recorded Scarborough DineSafe updates with City sources; not first-hand reporting or a new factual finding.',
 'rss-limits':'Preserve inspection date versus first-recorded change date, possible later City status changes, newly added versus newly opened business, and AI-assisted rather than first-hand reporting.',
 'rss-licence-link':'Channel attribution link to the exact Toronto Open Data Licence; do not substitute the DineSafe dataset URL or alter licence terms.'}

def contexts(packets,root=ROOT):
 root=Path(root);sources={}
 for name,pins in SOURCE_PINS.items():
  h=hashlib.sha256((root/name).read_bytes()).hexdigest();v.need(h in pins,'Reviewed RSS renderer/caller changed');sources[name]=h
 drafts=json.loads((root/'config/scarb-python-copy-drafts.json').read_text(encoding='utf-8'));classes=json.loads((root/'config/scarb-python-copy-classifications.json').read_text(encoding='utf-8'));out={}
 for p in packets:
  key=p['id'].removeprefix('python.');v.need(p['id']=='python.'+key and key in EXPECTED.keys()|CHANNEL_EXPECTED.keys(),'Unsupported RSS label')
  text=drafts[key];v.need(text==(CHANNEL_EXPECTED[key] if key in CHANNEL_EXPECTED else EXPECTED[key]),'RSS source template changed');v.need([p['surface'],p['kind']]==classes[key],'RSS classification changed')
  material=p['draft']
  for k,value in p['locks'].items():material=material.replace('{{LOCK:'+k+'}}',value)
  v.need(material==text,'RSS packet/locks differ from template')
  if key in CHANNEL_EXPECTED:
   v.need(classes[key]==CHANNEL_CLASSES[key],'RSS channel classification changed')
   v.need(len(p['evidence'])==1 and p['evidence'][0]=={'id':'python-copy.'+key,'source':'repo:config/scarb-python-copy-drafts.json#'+key,'sha256':v.digest(text),'fact':text},'RSS evidence differs')
   placeholders=re.findall(r'\{\{([A-Z]+)\}\}',text)
   v.need(placeholders==(['URL'] if key=='rss-licence-link' else []),'RSS channel placeholder multiplicity changed')
   out[p['id']]={'source_sha256':sources,'template_sha256':v.digest(text),'renderer':'scripts/scarb_voice.py::'+('compose_copy' if key=='rss-licence-link' else 'copy'),'caller':'scripts/build_rss.py::build_feed/channel/'+('title' if key=='rss-title' else 'description'),'field':'URL' if key=='rss-licence-link' else None,'parameters':{'URL':LICENCE_URL} if key=='rss-licence-link' else {},'locks':p['locks'],'meaning':CHANNEL_MEANINGS[key]+' Channel copy only; no actual event supplied. Preserve existing event templates, GUIDs, timestamps, freshness and archived editions unchanged.'}
   continue
  field,meaning=FIELDS[key];v.need(re.findall(r'\{\{([A-Z]+)\}\}',text)==[field],'RSS placeholder multiplicity changed')
  v.need(len(p['evidence'])==1 and p['evidence'][0]=={'id':'python-copy.'+key,'source':'repo:config/scarb-python-copy-drafts.json#'+key,'sha256':v.digest(text),'fact':text},'RSS evidence differs')
  out[p['id']]={'source_sha256':sources,'template_sha256':v.digest(text),'renderer':'scripts/scarb_voice.py::rss_description -> compose_copy','caller':'scripts/build_rss.py::load_events/build_feed','field':field,'field_meaning':meaning,'locks':p['locks'],'meaning':'RSS fact-label template only, no actual event supplied. Preserve placeholder exactly once, dated source meaning, optional prior result and source-coordinate matched provenance. Adjacent coordinate-limits and safety clauses remain unchanged; do not claim current safety or alter RSS identity/timestamps.'}
 return out
