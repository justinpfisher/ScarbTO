import test from 'node:test';
import assert from 'node:assert/strict';
import {canonical,sha,eventRequests} from '../scripts/collect_scarb_ai_requests.mjs';
import {eventFacts,resolveEventCopy} from '../docs/scarb-event-copy.mjs';
test('event prose uses exact current evidence, never latest establishment values',()=>{
 const event={id:'one',feed:'dinesafe',establishment_id:'x',name:'A',kind:'first_seen',status:'Pass',inspection_date:'2026-11-01',detected_at:'2026-11-02T00:00:00Z',source_url:'https://open.toronto.ca/dataset/dinesafe/'};
 const bindings={one:{key:'event.'+sha('one'),facts:canonical(eventFacts(event))}};let calls=0;
 const read=key=>{calls++;assert.equal(key,bindings.one.key);return 'Reviewed event explanation';};
 assert.equal(resolveEventCopy(event,bindings,read),'Reviewed event explanation');
 for(const changed of [{...event,status:'Closed'},{...event,name:'B'},{...event,inspection_date:'2026-11-02'},{...event,id:'two'}])assert.equal(resolveEventCopy(changed,bindings,read),null);
 assert.equal(calls,1);
 assert.equal(resolveEventCopy({...event,latitude:99,address:'Not prose evidence'},bindings,read),'Reviewed event explanation');
});
test('missing event catalogue is not a fabricated explanation or a network request',()=>{
 assert.equal(resolveEventCopy({id:'new'}, {},()=>{throw Error('must not read')}),null);
});
