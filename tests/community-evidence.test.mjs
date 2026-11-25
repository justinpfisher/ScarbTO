import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {composeEdition,finaliseEdition,verifyReceipt,validateProfile} from '../docs/community-publishing.mjs';
import {readerDate} from '../docs/reader-date.mjs';

const id='e154f47b353dd72f19300a03adfae6b8a77ff51b1ec3e409a7768ac7882b02cc';
const loadJSON=async path=>JSON.parse(await readFile(new URL(path,import.meta.url),'utf8'));
const release=await loadJSON(`../docs/community-data/releases/${id}.json`);
const registry=await loadJSON(`../docs/community-data/boundaries/${release.registry_sha256}.json`);
const profile=validateProfile({schema_version:1,name:'Recovery fixture',core:['city-140-f649e4df4c60'],nearby:[],topics:['dinesafe'],limits:{words:600},layout:{width_mm:148,height_mm:210}},registry);
const source=await readFile(new URL('../docs/community-evidence.mjs',import.meta.url),'utf8');
// Execute the actual page handlers with local DOM/fetch substitutes, not a browser or network.
const runPage=new (Object.getPrototypeOf(async function(){}).constructor)(
 'document','location','fetch','verifyReceipt','readerDate',
 source.replace(/^import .*;\r?\n/gm,'')+'\nawait releaseReady;');
function node(){return {textContent:'',children:[],append(child){this.children.push(child);},replaceChildren(fragment){this.children=[...fragment.children];}};}
async function page(search,fetch){
 const elements=Object.fromEntries(['status','metadata','events','receipt','downloads','copy'].map(id=>[id,node()]));
 await runPage({getElementById:id=>elements[id],createElement:node,createDocumentFragment:node},{search},fetch,verifyReceipt,readerDate);
 return {elements,async import(receipt){const text=JSON.stringify(receipt),target={files:[{size:Buffer.byteLength(text),text:async()=>text}],value:'fixture.json'};await elements.receipt.onchange({target});assert.equal(target.value,'');}};
}
async function receiptFor(evidence){
 const draft=composeEdition({profile,registry,release:evidence,start:evidence.history_start,end:evidence.checked_at,generatedAt:evidence.checked_at});
 const text=Buffer.from(draft.copy+'\n\n'+draft.footer);
 draft.outputs={text:{encoding:'base64',mime_type:'text/plain;charset=utf-8',content:text.toString('base64'),sha256:createHash('sha256').update(text).digest('hex')}};
 return verifyReceipt(await finaliseEdition(draft));
}

test('retained receipt recovers after failed pinned fetch without losing the requested release',async()=>{
 const receipt=await receiptFor(release),otherRelease={...release,id:'a'.repeat(64)},other=await receiptFor(otherRelease);
 assert.ok(receipt.included_event_ids.length,'real retained fixture includes edition events');
 const original=JSON.stringify(receipt);
 const rejected='This receipt belongs to a different source release. Open its exact evidence link.';
 const recovered='The receipt hash matches its retained copy and evidence. This detects changes, not organisational identity or approval.';
 const cases=[
  ['matching',async()=>({ok:true,json:async()=>release}),`Pinned information checked ${readerDate(release.checked_at)}. These are dated inspection outcomes, not conditions today.`],
  ['mismatched',async()=>({ok:true,json:async()=>otherRelease}),'The source release identity does not match.'],
  ['HTTP failure',async()=>({ok:false}),'I could not load that retained release. Your downloaded receipt also contains its supporting evidence.'],
  ['network failure',async()=>{throw new Error('Offline fixture');},'Offline fixture'],
  ['JSON failure',async()=>({ok:true,json:async()=>{throw new Error('Invalid JSON fixture');}}),'Invalid JSON fixture']
 ];
 for(const [name,response,status] of cases){
  const p=await page('?release='+id,async url=>{assert.equal(url,`/community-data/releases/${id}.json`);return response();});
  assert.equal(p.elements.status.textContent,status,name);
  assert.equal(p.elements.events.children.length,name==='matching'?release.events.length:0,name);
  await p.import(other);assert.equal(p.elements.status.textContent,rejected,name);
  await p.import(receipt);assert.equal(p.elements.status.textContent,recovered,name);
  assert.equal(p.elements.copy.textContent,receipt.copy+'\n\n'+receipt.footer,name);
  assert.deepEqual(p.elements.events.children.map(e=>e.id),receipt.evidence.events.filter(e=>receipt.included_event_ids.includes(e.id)).map(e=>'event-'+e.id),name);
  assert.equal(p.elements.downloads.children[0].textContent,'Download original text',name);
  const retainedCopy=p.elements.copy.textContent;
  await p.import(other);assert.equal(p.elements.status.textContent,rejected,name);
  assert.equal(p.elements.copy.textContent,retainedCopy,name);
 }
 for(const search of ['', '?release=invalid']){
  const p=await page(search,async()=>{assert.fail('An unpinned page must not fetch');});
  await p.import(receipt);assert.equal(p.elements.status.textContent,recovered);
  await p.import(other);assert.equal(p.elements.status.textContent,recovered);
 }
 assert.equal(JSON.stringify(receipt),original,'receipt and original output hashes remain unchanged');
});
