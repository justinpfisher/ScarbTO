import test from 'node:test';
import assert from 'node:assert/strict';
import {counts,validateGeometry,pointInGeometry,validateProfile,selectCoverage,composeEdition,finaliseEdition,verifyReceipt,SOURCE} from '../docs/community-publishing.mjs';
const geometry={type:'Polygon',coordinates:[[[-79.3,43.7],[-79.2,43.7],[-79.2,43.8],[-79.3,43.8],[-79.3,43.7]]]};
const registry={a:{verification:'verified',geometry,version:'a'},b:{verification:'verified',geometry,version:'b'}};
const profile=validateProfile({schema_version:1,name:'Our neighbourhood',core:['a'],nearby:['a','b'],topics:['dinesafe'],limits:{words:600},layout:{width_mm:148,height_mm:210}},registry);
const event={id:'1',feed:'dinesafe',kind:'first_seen',establishment_id:'place',name:'Café Montréal',status:'Pass',previous_status:null,inspection_date:'2026-10-01',detected_at:'2026-11-02T12:00:00Z',source_url:SOURCE,longitude:-79.25,latitude:43.75};
const release={id:'abc',source_url:SOURCE,checked_at:'2026-11-03T12:00:00Z',history_start:'2026-10-01T00:00:00Z',events:[event]};
const args={profile,registry,release,start:'2026-11-01T00:00:00Z',end:'2026-11-03T12:00:00Z',generatedAt:'2026-11-03T12:00:00Z'};
test('NFC Unicode code points and LF count consistently',()=>{assert.deepEqual(counts('Cafe\u0301 👋\r\nhello'),{words:3,characters:12});});
test('validated profile separates coverage meanings and deduplicates nearby',()=>{assert.deepEqual(profile.nearby,['b']);assert.throws(()=>validateProfile({...profile,core:['missing']},registry));});
test('edge inclusion, holes, multipart and invalid geometry',()=>{
  validateGeometry(geometry);assert.equal(pointInGeometry([-79.3,43.75],geometry),true);
  const g=structuredClone(geometry);g.coordinates.push([[-79.28,43.72],[-79.22,43.72],[-79.22,43.78],[-79.28,43.78],[-79.28,43.72]]);
  validateGeometry(g);assert.equal(pointInGeometry([-79.25,43.75],g),false);assert.equal(pointInGeometry([-79.28,43.75],g),true);
  assert.equal(pointInGeometry([-79.25,43.75],{type:'MultiPolygon',coordinates:[geometry.coordinates]}),true);
  assert.throws(()=>validateGeometry({type:'Point',coordinates:[0,0]}));
  assert.throws(()=>validateGeometry({type:'Polygon',coordinates:[[[-79.3,43.7],[-79.2,43.8],[-79.3,43.8],[-79.2,43.7],[-79.3,43.7]]]}));
});
test('overlap counts source identity once, with core priority',()=>{const rows=selectCoverage([event,event],profile,registry);assert.equal(rows.length,1);assert.equal(rows[0].coverage,'core');});
test('copy retains old inspection date and does not call new record an opening',()=>{const d=composeEdition(args);assert.equal(d.included_event_ids.length,1);assert.match(d.copy,/not a confirmed opening/);assert.match(d.copy,/October 1, 2026/);assert.match(d.copy,/not restaurant ratings/);});
test('draft never changes previous cutoff and final receipt detects tampering',async()=>{
  const draft=composeEdition(args),final=await finaliseEdition(draft);assert.equal(draft.state,'draft');await verifyReceipt(final);
  const changed=structuredClone(final);changed.copy+=' altered';await assert.rejects(()=>verifyReceipt(changed));
  const next=composeEdition({...args,start:null,previous:final,end:'2026-11-04T12:00:00Z',generatedAt:'2026-11-04T12:00:00Z',release:{...release,checked_at:'2026-11-04T12:00:00Z'}});
  assert.equal(next.included_event_ids.length,0);assert.match(next.copy,/no new updates/);assert.equal(final.source_cutoffs.dinesafe,'2026-11-03T12:00:00.000Z');
});
test('same-day subsequent observed event qualifies but old omissions do not',()=>{
  const previous={state:'finalised',source_cutoffs:{dinesafe:'2026-11-02T12:00:00Z'},included_event_ids:[],profile};
  const newer={...event,id:'2',detected_at:'2026-11-02T12:00:01Z',kind:'new_inspection'};
  const d=composeEdition({...args,start:null,previous,release:{...release,events:[event,newer]}});assert.deepEqual(d.included_event_ids,['2']);
});
test('hard caps never remove warnings or truncate an item',()=>{assert.throws(()=>composeEdition({...args,profile:{...profile,limits:{words:3}}}),/limit/);const d=composeEdition({...args,profile:{...profile,limits:{characters:5000,words:600,scope:'panel'}}});assert.ok(d.counts.panel.words<=600);assert.ok(d.counts.panel.characters<=5000);});
test('future and unavailable history are rejected',()=>{assert.throws(()=>composeEdition({...args,end:'2027-01-01T00:00:00Z'}));assert.throws(()=>composeEdition({...args,start:'2025-01-01T00:00:00Z'}));});
test('stale source cutoff does not advance to requested future coverage',()=>{const d=composeEdition({...args,end:'2026-11-10T00:00:00Z',generatedAt:'2026-11-10T00:00:00Z'});assert.equal(d.source_cutoffs.dinesafe,'2026-11-03T12:00:00.000Z');assert.match(d.copy,/couldn't check/);});

test('first-ever retained observation is included without inventing earlier history',()=>{const d=composeEdition({...args,start:event.detected_at,release:{...release,history_start:event.detected_at}});assert.deepEqual(d.included_event_ids,['1']);assert.equal(d.requested_period.start_inclusive,true);});
test('fractional exact cutoff excludes omitted event at that instant',()=>{const previous={state:'finalised',source_cutoffs:{dinesafe:'2026-11-02T12:00:00.750Z'},included_event_ids:[],profile};const d=composeEdition({...args,start:null,previous,release:{...release,events:[{...event,detected_at:'2026-11-02T12:00:00.750Z'}]}});assert.equal(d.candidate_event_ids.length,0);});
test('holes crossing exterior and overlapping components are rejected',()=>{const g=structuredClone(geometry);g.coordinates.push([[-79.28,43.72],[-79.18,43.72],[-79.18,43.78],[-79.28,43.78],[-79.28,43.72]]);assert.throws(()=>validateGeometry(g));assert.throws(()=>validateGeometry({type:'MultiPolygon',coordinates:[geometry.coordinates,geometry.coordinates]}));});
test('correction retains original copy and identity',async()=>{const {reviseEdition}=await import('../docs/community-publishing.mjs');const original=await finaliseEdition(composeEdition(args));const revision=await reviseEdition(original,composeEdition({...args,profile:{...profile,name:'Our revised coverage'}}),'Corrected coverage label, no new inspection claim.');await verifyReceipt(revision);assert.equal(revision.edition_id,original.edition_id);assert.equal(revision.original.copy,original.copy);assert.equal(revision.revision,2);});

test('single first observation can form an inclusive first edition',()=>{const d=composeEdition({...args,start:event.detected_at,end:event.detected_at,generatedAt:event.detected_at,release:{...release,checked_at:event.detected_at,history_start:event.detected_at}});assert.deepEqual(d.included_event_ids,['1']);});

test('three editions retain exclusions and corrections preserve original eligibility',async()=>{
 const first=await finaliseEdition(composeEdition(args));
 const later={...release,checked_at:'2026-11-05T12:00:00Z'};
 const second=await finaliseEdition(composeEdition({...args,release:later,previous:first,start:'2026-11-01T00:00:00Z',end:later.checked_at,generatedAt:later.checked_at}));
 assert.deepEqual(second.included_event_ids,[]);assert.deepEqual(second.publication_included_event_ids,['1']);
 const third=composeEdition({...args,release:later,previous:second,start:'2026-11-01T00:00:00Z',end:later.checked_at,generatedAt:later.checked_at});assert.deepEqual(third.included_event_ids,[]);
 const corrected=composeEdition({...args,release:second.evidence,start:second.requested_period.start,end:second.source_cutoffs.dinesafe,generatedAt:later.checked_at,correctionOf:second});assert.deepEqual(corrected.candidate_event_ids,second.candidate_event_ids);assert.deepEqual(corrected.included_event_ids,[]);assert.equal(corrected.requested_period.start_inclusive,second.requested_period.start_inclusive);
 const removed=composeEdition({...args,correctionOf:{...first,candidate_event_ids:[]}});assert.deepEqual(removed.included_event_ids,[]);assert.deepEqual(removed.publication_included_event_ids,['1']);
});
