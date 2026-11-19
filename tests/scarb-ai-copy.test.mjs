import test from 'node:test';
import assert from 'node:assert/strict';
import {catalogueRequests,eventRequests,protect,sha} from '../scripts/collect_scarb_ai_requests.mjs';
import {createScarbAiResolver} from '../docs/scarb-ai-copy.mjs';

const source = 'https://open.toronto.ca/dataset/dinesafe/';
const event = {id:'fixture1',feed:'dinesafe',establishment_id:'fixture-place',name:'Fixture Café',kind:'first_seen',status:'Pass',
  previous_status:null,inspection_date:'2026-11-10',detected_at:'2026-11-12T12:00:00Z',source_url:source};
const release = {id:'a'.repeat(64),schema_version:1,source_url:source,licence_url:'https://open.toronto.ca/open-data-licence/',
  checked_at:'2026-11-13T12:00:00Z',events:[event]};
const entry = {text:'Fixture only.',packet_sha256:'a'.repeat(64),receipt_sha256:'b'.repeat(64),origin:'openai-api-reviewed'};

test('catalogue copy is classified; unknown new copy fails closed', () => {
  const requests = catalogueRequests({'home-intro':'A little map nerdiness about Scarborough.'});
  assert.equal(requests[0].id,'static.home-intro');
  assert.equal(requests[0].kind,'editorial');
  assert.throws(() => catalogueRequests({'unclassified-new-copy':'Do not publish me.'}));
});
test('placeholders, exact names, numbers and links become unique protected tokens', () => {
  const {draft, locks} = protect('Scarb.TO has {{COUNT}} records in {{NAME}}: 30. DineSafe: https://example.test/');
  assert.equal(Object.values(locks).includes('{{NAME}}'),true);
  assert.equal(Object.values(locks).includes('30'),true);
  assert.equal(draft.includes('https:'),false);
  assert.throws(() => protect('{{LOCK:INJECTED}}'));
});
test('event input allowlist never sends coordinates or publisher/private fields', () => {
  const packet = eventRequests({...release,events:[{...event,latitude:43.7,longitude:-79.2,privateNote:'private-fixture'}]})[0];
  assert.equal(JSON.stringify(packet).includes('private-fixture'),false);
  assert.equal(JSON.stringify(packet).includes('latitude'),false);
  assert.match(packet.locks.NOVELTY,/not a confirmed opening/);
  assert.match(packet.locks.CAUTION,/not a restaurant rating/);
  assert.match(packet.locks.INSPECTION_DATE,/November 10, 2026/);
});
test('refresh without changed facts preserves request and cache identities', () => {
  assert.deepEqual(eventRequests(release),eventRequests({...release,id:'b'.repeat(64),checked_at:'2026-11-14T12:00:00Z'}));
  assert.notEqual(sha(eventRequests(release)[0]),sha(eventRequests({...release,events:[{...event,status:'Closed'}]})[0]));
});
test('serious outcomes use calm safety voice; source errors rejected', () => {
  assert.equal(eventRequests({...release,events:[{...event,status:'Conditional Pass'}]})[0].kind,'safety');
  for (const bad of [{...release,source_url:'https://wrong.test'}, {...release,events:[event,event]},
    {...release,events:[{...event,status:'All clear'}]}, {...release,events:[{...event,inspection_date:'2026-02-30'}]},
    {...release,events:[{...event,detected_at:'2027-01-01T00:00:00Z'}]}]) assert.throws(() => eventRequests(bad));
});
test('accepted resolver requires exact current input and rejects fixture/fallback masquerading as AI', () => {
  const cat = {version:'scarb-ai-voice-1',entries:{example:entry}};
  const read = createScarbAiResolver(cat,{example:'a'.repeat(64)});
  assert.equal(read('example'),'Fixture only.');
  assert.throws(() => read('missing'));
  assert.throws(() => createScarbAiResolver(cat,{example:'c'.repeat(64)}));
  assert.throws(() => createScarbAiResolver({...cat,entries:{example:{...entry,origin:'test-fixture'}}},{example:'a'.repeat(64)}));
  assert.throws(() => createScarbAiResolver({...cat,entries:{example:entry,extra:entry}},{example:'a'.repeat(64)}));
  cat.entries.example.text = 'Changed after construction';
  assert.equal(read('example'),'Fixture only.');
});

test('recorded legacy previous outcome stays exact rather than being renamed', () => {
  const packet = eventRequests({...release,events:[{...event,kind:'status_changed',previous_status:'Conditional'}]})[0];
  assert.equal(packet.locks.PREVIOUS,'Conditional');
});


import {SCARB_COPY,renderStaticCopy} from '../docs/scarb-voice.mjs';
import {createCurrentCopy,COPY_QUALIFICATION,assertAcceptedCopyReady} from '../docs/scarb-current-copy.mjs';
import {pythonCatalogueRequests,requestManifest} from '../scripts/collect_scarb_ai_requests.mjs';
test('all migrated source drafts are explicitly classified and never re-fed accepted copy',()=>{
  const packets=catalogueRequests(SCARB_COPY);
  assert.equal(packets.length,Object.keys(SCARB_COPY).length);
  assert.ok(packets.length>=275);
  assert.equal(packets.some(p=>p.kind==='verbatim'),false);
  const before=JSON.stringify(packets);
  const packet=packets.find(p=>p.id==='static.neighbourhood-intro');
  const lookup=createCurrentCopy({version:'scarb-ai-voice-1',entries:{[packet.id]:{...entry,text:'A fixture-only alternative for {{NAME}}.',packet_sha256:sha(packet)}}},{[packet.id]:sha(packet)});
  assert.equal(renderStaticCopy('neighbourhood-intro',{NAME:'West Rouge'},id=>lookup(id)),'A fixture-only alternative for West Rouge.');
  assert.equal(JSON.stringify(catalogueRequests(SCARB_COPY)),before);
  assert.throws(()=>renderStaticCopy('neighbourhood-intro',{NAME:'West Rouge'},()=> 'Missing source field'),/placeholders/);
  assert.throws(()=>renderStaticCopy('neighbourhood-intro',{NAME:'West Rouge'},()=> '{{NAME}} {{NAME}}'),/placeholders/);
});
test('dormant inputs cannot pass the publication guard',()=>{
  assert.equal(COPY_QUALIFICATION,'offline-draft');
  assert.throws(()=>assertAcceptedCopyReady(),/dormant/);
});
test('functional concatenation whitespace is a protected layout value',()=>{
  const packet=catalogueRequests({'app-43':SCARB_COPY['app-43']})[0];
  assert.equal(packet.locks.LAYOUT_SUFFIX,' ');
  assert.ok(packet.draft.endsWith('{{LOCK:LAYOUT_SUFFIX}}'));
  const newline=catalogueRequests({'community-editor-dynamic-02':SCARB_COPY['community-editor-dynamic-02']})[0];
  assert.equal(newline.locks.LAYOUT_PREFIX,'\n');
  assert.ok(newline.draft.startsWith('{{LOCK:LAYOUT_PREFIX}}'));
});
test('finding explanations retain official original wording as separate evidence',()=>{
  const packet=catalogueRequests(SCARB_COPY).find(p=>p.id.startsWith('static.finding-explanation-'));
  assert.equal(packet.kind,'safety');
  assert.equal(packet.evidence.length,2);
  assert.equal(packet.evidence[1].source,source);
  assert.notEqual(packet.evidence[0].fact,packet.evidence[1].fact);
});
test('Python and JS requests use one shared accepted-catalogue namespace',()=>{
  const packets=[...catalogueRequests(SCARB_COPY),...pythonCatalogueRequests()];
  const current=requestManifest(packets);
  assert.equal(Object.keys(current).length,packets.length);
  assert.ok(current['python.weekly-intro']);assert.ok(current['python.rss-intro']);
  assert.throws(()=>requestManifest([packets[0],packets[0]]),/Duplicate/);
});
