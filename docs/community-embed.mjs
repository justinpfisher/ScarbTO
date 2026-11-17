import {readerDate} from './reader-date.mjs';
import {composeEdition,validateProfile} from './community-publishing.mjs';
const status=document.getElementById('status');
async function json(path){const response=await fetch(path,{cache:'no-cache'});if(!response.ok)throw new Error('I could not load these updates. Follow the link below to explore Scarb.TO directly.');return response.json();}
try{
 const params=new URLSearchParams(location.search);if([...params.keys()].some(k=>!['areas','nearby','days'].includes(k)))throw new Error('This widget has an unsupported setting.');
 const parse=value=>value?value.split(','):[];const core=parse(params.get('areas')),nearby=parse(params.get('nearby'));
 const keys=[...new Set([...core,...nearby])];if(!keys.length||keys.length>40||keys.some(k=>!/^(?:city-\d{1,3}|custom-[a-z0-9-]{1,70})-[a-f0-9]{12}$/.test(k)))throw new Error('Choose verified City areas in the community publishing tool first.');
 const days=Number(params.get('days')||30);if(!Number.isInteger(days)||days<1||days>365)throw new Error('Choose a reporting period from 1 to 365 days.');
 const latest=await json('/community-data/latest.json');if(!/^[a-f0-9]{64}$/.test(latest.release_id))throw new Error('The qualified release reference is unavailable.');
 const areas=new Map(latest.areas.map(a=>[a.id,a]));if(keys.some(k=>!areas.has(k)))throw new Error('A selected boundary version changed. Open the publishing tool to review this coverage before updating the widget.');
 const pieces=await Promise.all(keys.map(k=>json(`/community-data/releases/${latest.release_id}/${k}.json`)));
 const registry=Object.assign({},...pieces.map(p=>p.boundaries));
 const events=new Map();for(const p of pieces)for(const e of p.events){if(events.has(e.id)&&JSON.stringify(events.get(e.id))!==JSON.stringify(e))throw new Error('The source projections disagree. These updates are unavailable.');events.set(e.id,e);}
 const release={...pieces[0],events:[...events.values()]};
 const now=new Date(),start=new Date(Math.max(now.valueOf()-days*86400000,Date.parse(release.history_start)));
 const profile=validateProfile({schema_version:1,name:core.length<=2?core.map(k=>areas.get(k).name).join(', '):core.length+' selected coverage areas',core,nearby,topics:['dinesafe'],limits:{words:600,scope:'panel'},layout:{width_mm:148,height_mm:210}},registry);
 const sourceNode=document.getElementById('source');
 for(const [label,url] of [['Official DineSafe source','https://open.toronto.ca/dataset/dinesafe/'],['Open Government Licence - Toronto','https://open.toronto.ca/open-data-licence/'],['Pinned source evidence',`https://scarb.to/community/evidence/?release=${latest.release_id}`]]){const a=document.createElement('a');a.textContent=label;a.href=url;a.target='_blank';a.rel='noopener';sourceNode.append(a,document.createElement('br'));}
 if(start.valueOf()>=Date.parse(release.checked_at)){status.textContent=`I have no successfully checked information for this rolling period. Last checked ${readerDate(release.checked_at)}. That does not mean nothing happened; the pinned evidence below retains the last qualified information.`;}
 else {
 const draft=composeEdition({profile,registry,release,start:start.toISOString(),end:now.toISOString(),generatedAt:now.toISOString()});
 document.getElementById('copy').textContent=draft.copy;const note=document.createElement('p');note.textContent='Last successfully checked '+readerDate(release.checked_at)+'. Coverage: '+keys.map(k=>areas.get(k).name).join(', ')+'.';sourceNode.prepend(note);status.textContent=`${draft.included_event_ids.length} updates shown from ${draft.candidate_event_ids.length} eligible updates. ${draft.omissions.length} omitted for space. Coverage is limited to qualified records in the six Scarborough wards.`;
}
}catch(error){status.textContent=error.message;}
