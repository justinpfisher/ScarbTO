import {prepareOutputs,downloadBlob,attributedMap,retainedOutput} from './community-exports.mjs';
import {validateProfile,composeEdition,finaliseEdition,reviseEdition,verifyReceipt,digest,canonical,counts,COUNT_RULE} from './community-publishing.mjs';
import {staticCopy} from './scarb-voice.mjs';
const el=id=>document.getElementById(id);
let registry,release,previous=null,draft=null,exactStart=null,importGeneration=0;
const status=value=>{el('status').textContent=value;};
const localInput=value=>{const d=new Date(value);return new Date(d.valueOf()-d.getTimezoneOffset()*60000).toISOString().slice(0,19);};
async function json(path){const r=await fetch(path,{cache:'no-cache'});if(!r.ok)throw new Error(staticCopy('community-editor-message-01'));return r.json();}
async function verifiedSourceReceipt(value){
 await verifyReceipt(value);
 if(!/^[a-f0-9]{64}$/.test(value.release_id||''))throw new Error(staticCopy('community-editor-message-02'));
 const pinned=release?.id===value.release_id?release:await json(`/community-data/releases/${value.release_id}.json`);
 if(canonical(pinned)!==canonical(value.evidence))throw new Error(staticCopy('community-editor-message-03'));
 if(!/^[a-f0-9]{64}$/.test(pinned.registry_sha256||''))throw new Error(staticCopy('community-editor-message-04'));
 const boundaries=await json(`/community-data/boundaries/${pinned.registry_sha256}.json`);
 for(const id of [...value.profile.core,...value.profile.nearby])if(canonical(boundaries[id])!==canonical(value.boundaries[id]))throw new Error(staticCopy('community-editor-message-05'));
 return value;
}
function download(value,name,type='application/json'){
 const blob=new Blob([typeof value==='string'?value:JSON.stringify(value,null,2)],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function profile(){return validateProfile({schema_version:1,name:el('name').value,association:el('association').value||null,distribution:el('distribution').value||null,core:[...document.querySelectorAll('#core input:checked')].map(x=>x.value),nearby:[...document.querySelectorAll('#nearby input:checked')].map(x=>x.value),topics:['dinesafe'],include_snapshot:el('snapshot').checked,limits:{words:el('words').value?Number(el('words').value):null,characters:el('characters').value?Number(el('characters').value):null,scope:el('scope').value},layout:{width_mm:Number(el('width').value),height_mm:Number(el('height').value),margin_mm:Number(el('margin').value),grayscale:el('grayscale').checked}},registry);}
function applyProfile(p,known=registry){p=validateProfile(p,known);el('name').value=p.name;el('association').value=p.association||'';el('distribution').value=p.distribution||'';el('snapshot').checked=p.include_snapshot;for(const kind of ['core','nearby'])for(const input of el(kind).querySelectorAll('input'))input.checked=p[kind].includes(input.value);el('words').value=p.limits.words??'';el('characters').value=p.limits.characters??'';el('scope').value=p.limits.scope;el('width').value=p.layout.width_mm;el('height').value=p.layout.height_mm;el('margin').value=p.layout.margin_mm;el('grayscale').checked=p.layout.grayscale;}
function restoreReceipt(value) {
 previous=value;exactStart=value.source_cutoffs.dinesafe;el('start').value=localInput(exactStart);
 try {applyProfile(value.profile);status(staticCopy('community-editor-message-06'));}
 catch {applyProfile(value.profile,value.boundaries);for(const input of document.querySelectorAll('#core input,#nearby input'))input.checked=false;el('name').value=value.profile.name;status(staticCopy('community-editor-message-07'));}
}
function invalidate(){importGeneration++;draft=null;el('proof-section').hidden=true;el('embed-section').hidden=true;}
el('settings').addEventListener('input',invalidate);
el('start').addEventListener('input',()=>{exactStart=null;});
el('settings').addEventListener('submit',event=>{event.preventDefault();try{
 let p;
 if(el('correction').checked){if(!previous)throw new Error(staticCopy('community-editor-message-08'));p=validateProfile({...previous.profile,name:el('name').value,limits:{words:el('words').value?Number(el('words').value):null,characters:el('characters').value?Number(el('characters').value):null,scope:el('scope').value},layout:{width_mm:Number(el('width').value),height_mm:Number(el('height').value),margin_mm:Number(el('margin').value),grayscale:el('grayscale').checked}},previous.boundaries);}
 else p=profile();
 if(el('correction').checked){if(!previous)throw new Error(staticCopy('community-editor-message-09'));if(!el('explanation').value.trim())throw new Error(staticCopy('community-editor-message-10'));p={...previous.profile,name:p.name,limits:p.limits,layout:p.layout};draft=composeEdition({profile:p,registry:previous.boundaries,release:previous.evidence,correctionOf:previous,start:previous.requested_period.start,end:previous.source_cutoffs.dinesafe,generatedAt:new Date().toISOString()});draft.correction_original=structuredClone(previous);draft.correction_explanation=el('explanation').value.trim();draft.footer=draft.footer.replace('Edition revision 1.',staticCopy('community-editor-dynamic-01',{ VALUE0:(previous.revision+1) }))+staticCopy('community-editor-dynamic-02',{ VALUE0:(draft.correction_explanation) });draft.counts.sources=counts(draft.footer);draft.counts.panel=counts(draft.copy+'\n\n'+draft.footer);const n=p.limits.scope==='panel'?draft.counts.panel:draft.counts.editorial;if((p.limits.words&&n.words>p.limits.words)||(p.limits.characters&&n.characters>p.limits.characters))throw new Error(staticCopy('community-editor-message-11'));}
 else draft=composeEdition({profile:p,registry,release,start:exactStart||new Date(el('start').value).toISOString(),end:new Date(el('end').value).toISOString(),previous,generatedAt:new Date().toISOString()});el('proof').textContent=draft.copy;el('sources').textContent=draft.footer;el('counts').textContent=staticCopy('community-editor-dynamic-03',{ VALUE0:(draft.counts.editorial.words), VALUE1:(draft.counts.editorial.characters), VALUE2:(draft.counts.sources.words), VALUE3:(draft.counts.panel.words), VALUE4:(draft.counts.panel.characters) });el('count-rule').textContent=COUNT_RULE;el('proof-section').hidden=false;
 const query=new URLSearchParams({areas:p.core.join(','),nearby:p.nearby.join(','),days:'30'});const url='https://scarb.to/embed/?'+query;el('embed-code').value=`<iframe src="${url.replaceAll('&','&amp;')}" title="${staticCopy('community-editor-message-12').replaceAll('&','&amp;').replaceAll('"','&quot;')}" width="100%" height="550" loading="lazy"></iframe>\n<p><a href="${url.replaceAll('&','&amp;')}">Read the updates on Scarb.TO</a></p>`;el('embed-link').href=url;el('embed-section').hidden=false;status(staticCopy('community-editor-dynamic-04',{ VALUE0:(draft.candidate_event_ids.length), VALUE1:(draft.omissions.length) }));
 }catch(error){invalidate();status(error.message);}});
let savedProfiles={};
function refreshSavedProfiles(){el('saved-profiles').replaceChildren();const blank=document.createElement('option');blank.value='';blank.textContent=staticCopy('community-editor-message-13');el('saved-profiles').append(blank);for(const [id,p] of Object.entries(savedProfiles)){const option=document.createElement('option');option.value=id;option.textContent=p.name;el('saved-profiles').append(option);}}
el('saved-profiles').onchange=event=>{try{if(event.target.value){applyProfile(savedProfiles[event.target.value]);previous=null;exactStart=release.history_start;el('start').value=localInput(exactStart);invalidate();status(staticCopy('community-editor-message-14'));}}catch{status(staticCopy('community-editor-message-15'));}};
el('save-settings').onclick=async()=>{try{const p=profile();download(p,'scarb-community-settings.json');const id=await digest(p);savedProfiles[id]=p;if(Object.keys(savedProfiles).length>30)throw new Error(staticCopy('community-editor-message-16'));try{localStorage.setItem('scarb-community-profiles',JSON.stringify(savedProfiles));refreshSavedProfiles();status(staticCopy('community-editor-message-17'));}catch{status(staticCopy('community-editor-message-18'));}}catch(e){status(e.message);}};
el('text').onclick=()=>{if(draft)download(draft.copy+'\n\n'+draft.footer,'scarb-community-copy.txt','text/plain;charset=utf-8');};
el('finalise').onclick=async()=>{if(!draft)return;const button=el('finalise');button.disabled=true;try{const activeDraft=draft,candidate=structuredClone(draft);const outputs=await prepareOutputs(candidate);if(draft!==activeDraft)throw new Error(staticCopy('community-editor-message-19'));const prepared={...candidate,renderer:{version:1,jspdf_version:'4.2.1',jspdf_git_blob:'0e600d49d2b2bf81dd97c1509e22d108c2ddd3b4'},outputs:{text:await retainedOutput(new Blob([candidate.copy+'\n\n'+candidate.footer],{type:'text/plain;charset=utf-8'})),pdf:await retainedOutput(outputs.pdf),png:await retainedOutput(outputs.png),map:await retainedOutput(attributedMap(candidate))}};const original=prepared.correction_original,explanation=prepared.correction_explanation;delete prepared.correction_original;delete prepared.correction_explanation;const receipt=original?await reviseEdition(original,prepared,explanation):await finaliseEdition(prepared);if(draft!==activeDraft)throw new Error(staticCopy('community-editor-message-20'));if(new Blob([JSON.stringify(receipt,null,2)]).size>5*1024*1024)throw new Error(staticCopy('community-editor-message-21'));download(receipt,`scarb-edition-${receipt.edition_id}.json`);previous=receipt;exactStart=receipt.source_cutoffs.dinesafe;el('start').value=localInput(exactStart);try{localStorage.setItem('scarb-community-finalised',JSON.stringify(receipt));}catch{status(staticCopy('community-editor-message-22'));return;}status(staticCopy('community-editor-message-23'));}catch(error){status(error.message);}finally{button.disabled=false;}};
el('import').onchange=async event=>{
 const file=event.target.files[0];if(!file)return;
 event.target.value='';const generation=++importGeneration;
 try{
  if(file.size>5*1024*1024)throw new Error(staticCopy('community-editor-message-24'));
  const value=JSON.parse(await file.text());if(generation!==importGeneration)return;
  if(value.state==='finalised'){
   await verifiedSourceReceipt(value);if(generation!==importGeneration)return;
   restoreReceipt(value);
  }else{
   applyProfile(value);previous=null;exactStart=release.history_start;el('start').value=localInput(exactStart);
   status(staticCopy('community-editor-message-25'));
  }
  invalidate();
 }catch(error){if(generation===importGeneration)status(error.message);}
};
try{
 const latest=await json('/community-data/latest.json');if(!/^[a-f0-9]{64}$/.test(latest.release_id)||!/^[a-f0-9]{64}$/.test(latest.boundary_version))throw new Error(staticCopy('community-editor-message-26'));
 [registry,release]=await Promise.all([json(`/community-data/boundaries/${latest.boundary_version}.json`),json(`/community-data/releases/${latest.release_id}.json`)]);
 for(const kind of ['core','nearby'])for(const area of latest.areas){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=area.id;label.append(input,document.createTextNode(' '+area.name));el(kind).append(label);}
 const code=new URLSearchParams(location.search).get('area');if(code)for(const input of el('core').querySelectorAll('input'))input.checked=registry[input.value].city_code===code;
 exactStart=release.history_start;el('start').value=localInput(exactStart);el('end').value=localInput(new Date().toISOString());
 try{const saved=JSON.parse(localStorage.getItem('scarb-community-finalised')||'null');if(saved&&!code){await verifiedSourceReceipt(saved);restoreReceipt(saved);}}catch{status(staticCopy('community-editor-message-27'));}
 try{savedProfiles=JSON.parse(localStorage.getItem('scarb-community-profiles')||'{}');if(!savedProfiles||typeof savedProfiles!=='object'||Array.isArray(savedProfiles)||Object.keys(savedProfiles).length>30)savedProfiles={};refreshSavedProfiles();}catch{savedProfiles={};}
 el('settings').hidden=false;if(!previous)status(staticCopy('editor-start'));
}catch(error){status(error.message);}
for(const kind of ['pdf','png'])el(kind).onclick=async()=>{if(!draft)return;const button=el(kind);button.disabled=true;try{const activeDraft=draft,candidate=structuredClone(draft);const output=await prepareOutputs(candidate);if(draft!==activeDraft)throw new Error(staticCopy('community-editor-message-28'));downloadBlob(output[kind],`scarb-community-proof.${kind}`);status(staticCopy('community-editor-dynamic-05',{ VALUE0:(output.width_mm), VALUE1:(output.height_mm), VALUE2:(output.pixels.join(' by ')) }));}catch(error){status(error.message);}finally{button.disabled=false;}};
el('map').onclick=()=>{if(draft)downloadBlob(attributedMap(draft),'scarb-community-map.svg');};
