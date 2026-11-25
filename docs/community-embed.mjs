import {readerDate} from './reader-date.mjs';
import {composeEdition,validateProfile,SOURCE} from './community-publishing.mjs';
import {INSPECTION_LIMITS, INSPECTION_SCOPE, LATEST, NO_INSPECTIONS, SNAPSHOT_UNAVAILABLE, STALE_INSPECTIONS, WIDGET_SETTINGS_ERROR, inspectionListItem, latestInspections, mergeSnapshot, widgetView} from './community-latest.mjs';
const status=document.getElementById('status');
async function json(path,view){
 try{
   const response=await fetch(path,{cache:'no-cache'});
   if(!response.ok)throw new Error('I could not load these updates. Follow the link below to explore Scarb.TO directly.');
   return await response.json();
 }catch(error){
   if(view===LATEST)throw new Error("I couldn’t fetch the inspections here. Try opening them on Scarb.TO.");
   throw error;
 }
}
function addSourceLink(node,label,url){
 const a=document.createElement('a');
 a.textContent=label;a.href=url;a.target='_blank';a.rel='noopener';
 node.append(a,document.createElement('br'));
}
try{
 const params=new URLSearchParams(location.search);
 const view=widgetView(params);
 const sourceNode=document.getElementById('source');
 if(view===LATEST){
   document.getElementById('widget-title').textContent='Last inspection on record';
   addSourceLink(sourceNode,'Official DineSafe source',SOURCE);
 }
 const parse=value=>value?value.split(','):[];const core=parse(params.get('areas')),nearby=parse(params.get('nearby'));
 const keys=[...new Set([...core,...nearby])];if((view===LATEST&&!core.length)||!keys.length||keys.length>40||keys.some(k=>!/^(?:city-\d{1,3}|custom-[a-z0-9-]{1,70})-[a-f0-9]{12}$/.test(k)))throw new Error(view===LATEST?WIDGET_SETTINGS_ERROR:'Choose verified City areas in the community publishing tool first.');
 const days=Number(params.get('days')||30);if(!Number.isInteger(days)||days<1||days>365)throw new Error('Choose a reporting period from 1 to 365 days.');
 const latest=await json('/community-data/latest.json',view);
 if(view===LATEST&&!Array.isArray(latest?.areas))throw new Error(SNAPSHOT_UNAVAILABLE);
 if(!/^[a-f0-9]{64}$/.test(latest.release_id))throw new Error(view===LATEST?SNAPSHOT_UNAVAILABLE:'The qualified release reference is unavailable.');
 const areas=new Map(latest.areas.map(a=>[a.id,a]));if(keys.some(k=>!areas.has(k)))throw new Error(view===LATEST?WIDGET_SETTINGS_ERROR:'A selected boundary version changed. Open the publishing tool to review this coverage before updating the widget.');
 const pieces=await Promise.all(keys.map(k=>json(`/community-data/releases/${latest.release_id}/${k}.json`,view)));
 const registry=Object.assign({},...pieces.map(p=>p.boundaries));
 const now=new Date();
 const profile=validateProfile({schema_version:1,name:core.length<=2?core.map(k=>areas.get(k).name).join(', '):core.length+' selected coverage areas',core,nearby,topics:['dinesafe'],limits:{words:600,scope:'panel'},layout:{width_mm:148,height_mm:210}},registry);
 const coverageLabel='Coverage: '+keys.map(k=>areas.get(k).name).join(', ')+'.';
 const coverageLimit='Coverage is limited to qualified records in the six Scarborough wards.';
 if(view!==LATEST)addSourceLink(sourceNode,'Official DineSafe source',SOURCE);
 for(const [label,url] of [['Open Government Licence - Toronto','https://open.toronto.ca/open-data-licence/'],['Pinned source evidence',`https://scarb.to/community/evidence/?release=${latest.release_id}`]])addSourceLink(sourceNode,label,url);
 if(view===LATEST){
   const snapshot=latestInspections(mergeSnapshot(latest,pieces),profile,registry,now.toISOString());
   document.getElementById('latest-results').hidden=false;
   for(const message of [snapshot.checkedLabel,snapshot.upstreamLabel,...(snapshot.stale?[STALE_INSPECTIONS]:[]),'Looking at: '+keys.map(k=>areas.get(k).name).join(', ')+'.',INSPECTION_SCOPE,INSPECTION_LIMITS]){
     const note=document.createElement('p');
     note.textContent=message;
     document.getElementById('snapshot-notes').append(note);
   }
   const list=document.getElementById('latest-rows');
   const more=document.getElementById('more-inspections');
   let shown=0;
   function appendPage(moveFocus){
     const next=snapshot.rows.slice(shown,shown+20).map(inspectionListItem);
     list.append(...next);
     shown+=next.length;
     more.hidden=shown>=snapshot.rows.length;
     status.textContent=snapshot.rows.length?
       'Showing '+shown+' of '+snapshot.rows.length+' places.':NO_INSPECTIONS;
     if(moveFocus&&next.length){next[0].tabIndex=-1;next[0].focus();}
   }
   more.addEventListener('click',()=>appendPage(true));
   appendPage(false);
 }else{
   const events=new Map();for(const p of pieces)for(const e of p.events){if(events.has(e.id)&&JSON.stringify(events.get(e.id))!==JSON.stringify(e))throw new Error('The source projections disagree. These updates are unavailable.');events.set(e.id,e);}
   const release={...pieces[0],events:[...events.values()]};
   const start=new Date(Math.max(now.valueOf()-days*86400000,Date.parse(release.history_start)));
   if(start.valueOf()>=Date.parse(release.checked_at)){status.textContent=`I have no successfully checked information for this rolling period. Last checked ${readerDate(release.checked_at)}. That does not mean nothing happened; the pinned evidence below retains the last qualified information.`;}
   else {
   const draft=composeEdition({profile,registry,release,start:start.toISOString(),end:now.toISOString(),generatedAt:now.toISOString()});
   document.getElementById('copy').textContent=draft.copy;const note=document.createElement('p');note.textContent='Last successfully checked '+readerDate(release.checked_at)+'. '+coverageLabel;sourceNode.prepend(note);status.textContent=`${draft.included_event_ids.length} updates shown from ${draft.candidate_event_ids.length} eligible updates. ${draft.omissions.length} omitted for space. ${coverageLimit}`;
  }
 }
}catch(error){status.textContent=error.message;}
