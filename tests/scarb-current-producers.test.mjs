import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {currentEventPackets,parseDataModule} from '../scripts/scarb_current_events.mjs';
import {eventRequests} from '../scripts/collect_scarb_ai_requests.mjs';
import {materializeShell} from '../scripts/build_scarb_static.mjs';
const pointer=JSON.parse(readFileSync(new URL('../docs/community-data/latest.json',import.meta.url)));
const release=JSON.parse(readFileSync(new URL('../docs/community-data/releases/'+pointer.release_id+'.json',import.meta.url)));
test('event bindings recomputed from retained qualified source, not accepted claims',()=>{
 const packet=eventRequests(release)[0],id=JSON.parse(packet.evidence[0].fact).id,binding={key:packet.id,facts:packet.evidence[0].fact};
 assert.deepEqual(currentEventPackets(release,{[id]:binding}),[packet]);
 assert.throws(()=>currentEventPackets(release,{[id]:{...binding,facts:'{}'}}));
 assert.throws(()=>currentEventPackets(release,{[id]:{...binding,key:'static.home-title'}}));
 assert.throws(()=>currentEventPackets(release,{[id]:{...binding,override:'accept'}}));
 assert.deepEqual(currentEventPackets(release,{}),[]);
});
test('generated modules are data only, no executable claims',()=>{
 assert.deepEqual(parseDataModule('export default {};\n'),{});
 assert.throws(()=>parseDataModule('export default (()=>({}))();'));
});
test('static dry-run preserves six original shells and rejects extra placeholders',()=>{
 const shells=JSON.parse(readFileSync(new URL('../config/scarb-static-shells.json',import.meta.url)));
 for(const record of Object.values(shells)){const values=Object.fromEntries(record.slots.map(s=>[s.id,s.draft]));assert.equal(materializeShell(record,id=>values[id]),record.source);}
 const record={source:'Hello',slots:[{id:'one',start:0,end:5,draft:'Hello',attribute:false}]};
 assert.equal(materializeShell(record,()=>'<new> & clear'),'&lt;new&gt; &amp; clear');
 assert.throws(()=>materializeShell(record,()=>'{{UNREGISTERED}}'));
});
import {checkVoiceGateway} from '../scripts/check_scarb_voice.mjs';
test('new shell text outside declared slots cannot bypass accepted materialization',()=>{
 const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
 const shells=JSON.parse(read('config/scarb-static-shells.json'));
 shells['docs/index.html'].source+='<p>A newly invented public claim</p>';
 assert.throws(()=>checkVoiceGateway(path=>path==='config/scarb-static-shells.json'?JSON.stringify(shells):read(path)),/Unregistered shell text/);
});
import {isRetainedIndex} from '../scripts/check_scarb_voice.mjs';
test('preserved index requires exact previous index, manifest and issued HTML evidence',()=>{
 const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
 assert.equal(isRetainedIndex(read),true);
 for(const path of ['docs/briefs/index.html','docs/briefs/editions.json','docs/briefs/2026-11-02/index.html'])assert.equal(isRetainedIndex(p=>read(p)+(p===path?'changed':'')),false);
});
