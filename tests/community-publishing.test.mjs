import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {counts,validateGeometry,pointInGeometry,validateProfile,selectCoverage,composeEdition,finaliseEdition,verifyReceipt,SOURCE,LICENCE} from '../docs/community-publishing.mjs';
import {composeLatestProof,latestInspections,mergeSnapshot,readPublicationSettings,widgetUrl,widgetView} from '../docs/community-latest.mjs';
const geometry={type:'Polygon',coordinates:[[[-79.3,43.7],[-79.2,43.7],[-79.2,43.8],[-79.3,43.8],[-79.3,43.7]]]};
const registry={a:{name:'Core area',verification:'verified',geometry,version:'a'},b:{name:'Nearby area',verification:'verified',geometry,version:'b'}};
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


const snapshotPointer={release_id:'a'.repeat(64),boundary_version:'b'.repeat(64),checked_at:release.checked_at};
const oldInspection={id:'older',name:'Old <Market>',status:'Pass',inspection_date:'2025-09-03',longitude:-79.25,latitude:43.75};
const recentInspection={...oldInspection,id:'recent',name:'Recent Bakery',status:'Conditional Pass',inspection_date:'2026-11-01'};
const available={...release,id:snapshotPointer.release_id,registry_sha256:snapshotPointer.boundary_version,schema_version:1,
 snapshot_sha256:'c'.repeat(64),upstream_date_as_supplied:'2026-11-02 05:20',licence_url:LICENCE,records:[oldInspection,recentInspection]};

test('new widget configuration marks Latest explicitly; old widgets and saved settings still select changes',()=>{
 const legacy=new URLSearchParams('areas=a&nearby=b&days=30');
 assert.equal(widgetView(legacy),'changes');
 assert.equal(widgetView(new URLSearchParams('areas=a')),'changes');
 assert.equal(new URL(widgetUrl(profile,'changes')).search,'?areas=a&nearby=b&days=30');
 const latest=new URL(widgetUrl(profile,'latest')).searchParams;
 assert.equal(widgetView(latest),'latest');
 assert.equal(latest.has('days'),false);
 assert.throws(()=>widgetView(new URLSearchParams('areas=a&view=latest&days=30')),{message:"I don’t recognise those widget settings. You can still see the inspections on Scarb.TO."});
 assert.throws(()=>widgetView(new URLSearchParams('areas=a&view=changes')),{message:"I don’t recognise those widget settings. You can still see the inspections on Scarb.TO."});
 assert.deepEqual(readPublicationSettings(profile,registry),{profile,view:'changes'});
 assert.deepEqual(readPublicationSettings({schema_version:2,view:'latest',profile},registry),{profile,view:'latest'});
 assert.throws(()=>readPublicationSettings({schema_version:2,view:'unknown',profile},registry),{message:"I can’t make a proof with those settings. Try choosing the area and what to show again."});
});

test('latest snapshots keep old inspection dates, merge overlapping IDs, and fail closed on disagreements',()=>{
 const merged=mergeSnapshot(snapshotPointer,[available,{...available,records:[oldInspection]}]);
 const snapshot=latestInspections(merged,profile,registry,'2026-11-10T00:00:00Z');
 assert.deepEqual(snapshot.rows.map(r=>r.id),['older','recent']);
 assert.equal(snapshot.rows[0].inspection_date,'2025-09-03');
 assert.match(snapshot.rows[0].sourceUrl,/#establishment\/older$/);
 assert.equal(snapshot.stale,true);
 assert.match(snapshot.checkedLabel,/November 3, 2026/);
 assert.equal(snapshot.upstreamLabel,"Date on the City’s data: 2026-11-02 05:20.");
 assert.equal(latestInspections({...available,upstream_date_as_supplied:null},profile,registry,args.generatedAt).upstreamLabel,"The City’s data didn’t come with a date.");
 assert.throws(()=>mergeSnapshot(snapshotPointer,[available,{...available,records:[{...oldInspection,status:'Closed'}]}]),{message:"The source records disagree. I’m not picking a winner."});
 assert.throws(()=>mergeSnapshot(snapshotPointer,[available,{...available,snapshot_sha256:'d'.repeat(64)}]),{message:"I can’t show the inspection records right now. You can still check the City’s DineSafe site."});
 assert.throws(()=>latestInspections({...available,records:[{...oldInspection,inspection_date:'2026-02-31'}]},profile,registry,args.generatedAt),{message:"I can’t show that inspection without both the date and the result."});
});

test('latest proof retains source links and truthful record omissions without carrying a changes cutoff',()=>{
 const snapshot=latestInspections(available,profile,registry,'2026-11-10T00:00:00Z');
 const proof=composeLatestProof({snapshot,release:available,profile,registry,generatedAt:'2026-11-10T00:00:00Z',fitsPage:draft=>draft.rows.length<2});
 assert.ok(proof.copy.startsWith('Last inspections on record in Core area, Nearby area\n'));
 assert.equal(proof.rows.length,1);
 assert.equal(proof.omitted,1);
 assert.ok(proof.copy.includes('I could fit 1 of 2 places on this page.'));
 assert.ok(!proof.copy.includes('See all'));
 assert.ok(proof.footer.includes('See the records behind this proof: https://scarb.to/community/evidence/?release='+available.id));
 assert.match(proof.copy,/Wednesday, September 3, 2025/);
 assert.match(proof.copy,/See the City record: https:\/\/www\.toronto\.ca\/.+#establishment\/older/);
 assert.ok(proof.copy.includes("I couldn’t verify anything newer. These are the last records I could check."));
 assert.ok(proof.copy.includes("The date does some heavy lifting here. It tells you what the inspector found that day, not what you’d find if you walked in now. The City may have a newer result."));
 assert.equal(Object.hasOwn(proof,'source_cutoffs'),false);
 assert.equal(Object.hasOwn(proof,'requested_period'),false);
 assert.throws(()=>composeLatestProof({snapshot,release:available,profile,registry,generatedAt:args.generatedAt,fitsPage:draft=>!draft.rows.length}),{message:"This page won’t fit a whole inspection and its source. Try a larger page or a longer copy limit."});
 assert.throws(()=>composeLatestProof({snapshot,release:available,profile,registry,generatedAt:args.generatedAt,fitsPage:()=>false}),{message:"Give the dates and sources a little more room. Try a larger page or a longer copy limit."});
 const empty=latestInspections({...available,records:[]},profile,registry,args.generatedAt);
 assert.equal(empty.stale,false);
 assert.ok(composeLatestProof({snapshot:empty,release:available,profile,registry,generatedAt:args.generatedAt}).copy.includes("I don’t have an inspection on record for this area. That doesn’t mean nobody’s been inspected."));
});

test('unmeasured Latest copy retains whole rows, limits, omissions and evidence without a physical fit claim',async()=>{
 const {canExportPrint,preparePdf}=await import('../docs/community-exports.mjs');
 const snapshot=latestInspections(available,profile,registry,args.generatedAt);
 const inputs={snapshot,release:available,profile,registry,generatedAt:args.generatedAt};
 const full=composeLatestProof(inputs);
 assert.equal(full.print_measured,false);
 assert.equal(full.rows.length,2);
 assert.match(full.summary,/0 omitted for space\./);
 assert.doesNotMatch(full.copy,/I could fit|on this page/);
 assert.match(full.copy,/#establishment\/older/);
 assert.match(full.copy,/#establishment\/recent/);
 assert.match(full.footer,/Open Government Licence - Toronto/);
 assert.match(full.footer,/community\/evidence\/\?release=/);
 const limited=composeLatestProof({...inputs,profile:{...profile,limits:{scope:'panel',characters:full.counts.panel.characters-1}}});
 assert.equal(limited.rows.length,1);
 assert.equal(limited.omitted,1);
 assert.match(limited.copy,/1 omitted for space\./);
 assert.ok(limited.counts.panel.characters<full.counts.panel.characters);
 assert.equal(canExportPrint(limited),false);
 await assert.rejects(()=>preparePdf(limited),{message:'The PDF didn’t come together. You can still download the text.'});
 assert.equal(canExportPrint(null),false);
 assert.equal(canExportPrint(composeEdition(args)),true);
 const measured=composeLatestProof({...inputs,fitsPage:()=>true});
 assert.equal(canExportPrint(measured),true);
 assert.match(measured.copy,/I could fit 2 of 2 places on this page\./);
});

test('Latest text notice uses actual qualified and included rows, exact approved bytes, and text limits',()=>{
 const records=Array.from({length:15},(_,i)=>({...oldInspection,id:'place-'+i,name:'Place '+String(i).padStart(2,'0')}));
 const snapshot=latestInspections({...available,records:[...records,records[0],{...oldInspection,id:'outside',longitude:0}]},profile,registry,args.generatedAt);
 assert.equal(snapshot.rows.length,15);
 const inputs={snapshot,release:available,profile:{...profile,limits:{scope:'panel'}},registry,generatedAt:args.generatedAt};
 const expected='3 more places aren’t shown in this text version. See all 15 on Scarb.TO.';
 assert.equal(createHash('sha256').update(expected).digest('hex'),'e679082e09bc031cfde8981162f7512214798d5fd88a6ea37e187d14d5e636b5');
 const measured=composeLatestProof({...inputs,fitsPage:proof=>proof.rows.length<=12});
 assert.equal(measured.rows.length,12);
 assert.equal(measured.textCopy.split('See the City record: ').length-1,12);
 assert.ok(measured.textCopy.endsWith('\n\n'+expected));
 assert.equal(measured.textCopy.split(expected).length-1,1);
 assert.match(measured.copy,/I could fit 12 of 15 places on this page\./);
 assert.doesNotMatch(measured.copy+'\n'+measured.summary+'\n'+measured.footer,/more places aren’t shown|See all/);
 const withoutNotice=measured.textCopy.slice(0,-expected.length-2);
 assert.equal(withoutNotice,measured.copy);
 for(const scope of ['editorial','panel'])for(const unit of ['words','characters']){
   const limit=measured.textCounts[scope][unit];
   const limited=composeLatestProof({...inputs,profile:{...profile,limits:{scope,[unit]:limit}}});
   const tally=counts(limited.textCopy+(scope==='panel'?'\n\n'+limited.footer:''));
   assert.ok(tally[unit]<=limit);
   assert.deepEqual(limited.textCounts[scope],tally);
   const included=limited.textCopy.split('See the City record: ').length-1;
   assert.equal(included,limited.rows.length);
   assert.ok(limited.textCopy.endsWith((15-included)+' more places aren’t shown in this text version. See all 15 on Scarb.TO.'));
   assert.doesNotMatch(limited.textCopy,/omitted for space|I could fit/);
   const tighter=composeLatestProof({...inputs,profile:{...profile,limits:{scope,[unit]:limit-1}},fitsPage:proof=>proof.rows.length<=12});
   assert.ok(tighter.rows.length<12);
   assert.ok(tighter.textCounts[scope][unit]<limit);
 }
 for(const fitsPage of [undefined,()=>true]){
   const full=composeLatestProof({...inputs,fitsPage});
   assert.equal(full.rows.length,15);assert.equal(full.textCopy,full.copy);
   const exact=composeLatestProof({...inputs,profile:{...profile,limits:{scope:'panel',characters:full.textCounts.panel.characters}},fitsPage});
   assert.equal(exact.rows.length,15);
   const empty=composeLatestProof({...inputs,snapshot:{...snapshot,rows:[]},fitsPage});
   assert.equal(empty.textCopy,empty.copy);assert.doesNotMatch(empty.textCopy,/more places aren’t shown/);
 }
});

test('editor retains text for missing jsPDF and failed font, recovers, and guards stale exports across proof modes',async t=>{
 // Minimal DOM and renderer doubles: no browser, network, assets or output files.
 const names=['document','window','fetch','location','localStorage','FontFace'];
 const originals=new Map(names.map(name=>[name,Object.getOwnPropertyDescriptor(globalThis,name)]));
 const originalCreate=URL.createObjectURL,originalRevoke=URL.revokeObjectURL;
 t.after(()=>{
   for(const [name,descriptor] of originals)if(descriptor)Object.defineProperty(globalThis,name,descriptor);else delete globalThis[name];
   URL.createObjectURL=originalCreate;URL.revokeObjectURL=originalRevoke;
 });
 const nodes=new Map(),downloads=[],blobs=new Map();let fontRequests=0,fontOK=false,pdfCreated=0,expectedOmitted=0;
 class Element {
   value='';checked=false;disabled=false;hidden=false;textContent='';children=[];listeners={};
   addEventListener(type,callback){this.listeners[type]=callback;}
   append(...children){this.children.push(...children);}
   replaceChildren(...children){this.children=children;}
   setAttribute(){}
   querySelectorAll(){return this.children.flatMap(child=>child.children).filter(child=>child instanceof Element);}
   click(){if(this.download)downloads.push({name:this.download,blob:blobs.get(this.href)});}
 }
 const el=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
 const canvas={getContext:()=>({fillRect(){},fillText(text){assert.doesNotMatch(text,/more places aren’t shown/);},measureText:()=>({width:1})}),toBlob(callback){
   const png=new Uint8Array(33);new DataView(png.buffer).setUint32(8,13);png.set([73,72,68,82],12);callback(new Blob([png],{type:'image/png'}));
 }};
 globalThis.document={getElementById:el,createElement:tag=>tag==='canvas'?canvas:new Element(),createTextNode:text=>text,
   querySelectorAll:selector=>selector==='#core input:checked'?[{value:'a'}]:[],fonts:{add(){}}};
 globalThis.location={search:''};globalThis.localStorage={getItem:()=>null,setItem(){throw new Error('Unexpected receipt write');}};
 globalThis.window={};
 globalThis.fetch=async path=>{
   if(path==='/assets/community/DMSans.ttf'){fontRequests++;return {ok:fontOK,arrayBuffer:async()=>new Uint8Array([1]).buffer};}
   const value=path.endsWith('/latest.json')?{...snapshotPointer,areas:[]}:path.includes('/boundaries/')?registry:available;
   return {ok:true,json:async()=>value};
 };
 URL.createObjectURL=blob=>{const url='blob:test-'+blobs.size;blobs.set(url,blob);return url;};URL.revokeObjectURL=()=>{};
 for(const [id,value] of Object.entries({name:profile.name,words:'600',scope:'editorial',width:'148',height:'210',margin:'8'}))el(id).value=value;
 await import('../docs/community-editor.mjs?dependency-failures');
 const submit=()=>el('settings').listeners.submit({preventDefault(){}});
 const fallback='The PDF didn’t come together. You can still download the text.';
 async function assertTextOnly(){
   assert.equal(el('proof-section').hidden,false);assert.equal(el('embed-section').hidden,false);
   assert.equal(el('status').textContent,fallback);assert.doesNotMatch(el('proof').textContent,/I could fit|on this page/);
   assert.equal(el('pdf').disabled,true);assert.equal(el('png').disabled,true);
   const before=downloads.length,requests=fontRequests;
   await el('pdf').onclick();await el('png').onclick();
   assert.equal(downloads.length,before);assert.equal(fontRequests,requests);
   el('text').onclick();assert.equal(downloads.length,before+1);
   const text=await downloads.at(-1).blob.text();
   assert.match(text,/#establishment\/older/);assert.match(text,/Open Government Licence - Toronto/);
   assert.match(text,/community\/evidence\/\?release=/);assert.doesNotMatch(text,/I could fit|on this page/);
   assert.doesNotMatch(el('proof').textContent,/more places aren’t shown/);
   if(expectedOmitted){
     const notice='1 more place isn’t shown in this text version. See all 2 on Scarb.TO.';
     assert.equal(text.split('See the City record: ').length-1,1);
     assert.equal(text.split(notice).length-1,1);
     assert.ok(text.indexOf(notice)>text.indexOf('See the City record: '));
     assert.ok(text.indexOf(notice)<text.indexOf('City of Toronto DineSafe: '));
     assert.doesNotMatch(text,/omitted for space/);
     assert.ok(counts(text).characters<=Number(el('characters').value));
   }else assert.doesNotMatch(text,/more places aren’t shown/);
 }
 await submit();await assertTextOnly();assert.equal(fontRequests,0);
 el('characters').value=String(counts(await downloads.at(-1).blob.text()).characters-1);
 el('scope').value='panel';expectedOmitted=1;
 await submit();await assertTextOnly();assert.equal(fontRequests,0);
 class PDF {
   constructor(){pdfCreated++;}
   addFileToVFS(){} addFont(){} setFont(){} setFontSize(){} splitTextToSize(text){return [text];}
   getFont(){return {metadata:{characterToGlyph:()=>1}};}
   text(text){assert.doesNotMatch(text,/more places aren’t shown/);} link(){} setCreationDate(){} setFileId(){} setProperties(){}
   output(){return new Blob(['pdf'],{type:'application/pdf'});}
 }
 window.jspdf={jsPDF:PDF};
 await submit();await assertTextOnly();assert.equal(fontRequests,1);assert.equal(pdfCreated,0);
 // Fetch rejection also retains the proof, then a successful retry restores normal copy.
 const fetchResponse=globalThis.fetch;
 globalThis.fetch=async path=>{if(path.endsWith('.ttf'))throw new Error('offline');return fetchResponse(path);};
 await submit();await assertTextOnly();globalThis.fetch=fetchResponse;
 fontOK=true;await submit();
 el('text').onclick();
 const measuredText=await downloads.at(-1).blob.text();
 assert.match(measuredText,/1 more place isn’t shown in this text version\. See all 2 on Scarb\.TO\./);
 assert.match(measuredText,/I could fit 1 of 2 places on this page\./);
 assert.ok(counts(measuredText).characters<=Number(el('characters').value));
 globalThis.FontFace=class {async load(){return this;}};
 await el('pdf').onclick();await el('png').onclick();
 el('characters').value='';el('scope').value='editorial';expectedOmitted=0;await submit();
 assert.equal(el('pdf').disabled,false);assert.equal(el('png').disabled,false);
 assert.match(el('proof').textContent,/I could fit 2 of 2 places on this page\./);
 assert.equal(el('status').textContent,'Your proof’s ready. Download it as a PDF, an image or editable text. This won’t change where your next roundup picks up.');
 globalThis.FontFace=class {async load(){return this;}};
 await el('pdf').onclick();assert.equal(downloads.at(-1).name,'scarb-community-proof.pdf');
 await el('png').onclick();assert.equal(downloads.at(-1).name,'scarb-community-proof.png');
 async function staleExport(nextView,reject=false){
   let finish,started;
   const ready=new Promise(resolve=>{started=resolve;});
   globalThis.FontFace=class {load(){started();return new Promise((resolve,fail)=>{finish=()=>reject?fail(new Error('old failure')):resolve(this);});}};
   const before=downloads.length,pending=el('pdf').onclick();await ready;
   window.jspdf=undefined;el('publication-view').value=nextView;await submit();
   const currentStatus=el('status').textContent;
   finish();await pending;
   assert.equal(downloads.length,before);assert.equal(el('status').textContent,currentStatus);
   assert.equal(el('pdf').disabled,nextView==='latest');assert.equal(el('png').disabled,nextView==='latest');
 }
 await staleExport('latest');await assertTextOnly();
 window.jspdf={jsPDF:PDF};await submit();await staleExport('latest',true);await assertTextOnly();
 window.jspdf={jsPDF:PDF};await submit();await staleExport('changes');
 assert.equal(el('finalise').hidden,false);assert.equal(el('map').hidden,false);
 assert.match(el('status').textContent,/Proof prepared from/);
 el('text').onclick();
 const changesText=await downloads.at(-1).blob.text();
 assert.equal(changesText,el('proof').textContent+'\n\n'+el('sources').textContent);
 assert.doesNotMatch(changesText,/more places aren’t shown/);
 el('publication-view').value='latest';await submit();await assertTextOnly();
 el('settings').listeners.input();assert.equal(el('pdf').disabled,true);assert.equal(el('png').disabled,true);
});
