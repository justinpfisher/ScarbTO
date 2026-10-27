import test from 'node:test';
import assert from 'node:assert/strict';
import {dayInWindow, filterEstablishments, filterActivity, isStale, cityDineSafeRecordUrl, pageRecords, fitBoundsFromFeatures} from '../docs/logic.mjs';
const now = new Date('2026-10-24T15:00:00Z');
const data = [
 {name:'Alpha Café',address:'123 Main',status:'Pass',neighbourhood:'Agincourt',inspection_date:'2026-10-21'},
 {name:'Beta Diner',address:'233 Test',status:'Closed',neighbourhood:'Port Union',inspection_date:'2025-10-21'},
 {name:'Gamma',address:'456 Road',status:'Conditional Pass',neighbourhood:'Agincourt',inspection_date:'2026-10-19'}
];
const state={mode:'recent',status:'all',days:'7',neighbourhood:'',search:''};
test('calendar window uses explicit inspection dates',()=>{
 assert.equal(dayInWindow('2026-10-21','7',now),true);
 assert.equal(dayInWindow('2025-10-21','7',now),false);
 assert.equal(dayInWindow('2026-10-25','7',now),false);
 assert.equal(dayInWindow('2025-10-21','all',now),true);
 // 02:00 UTC on October 25 is still October 24 in Toronto.
 assert.equal(dayInWindow('2026-10-25','7',new Date('2026-10-25T02:00:00Z')),false);
});
test('time and outcome controls work across browsing modes',()=>{
 assert.deepEqual(filterEstablishments(data,state,now).map(x=>x.name),['Alpha Café','Gamma']);
 assert.deepEqual(filterEstablishments(data,{...state,mode:'all',status:'Closed',days:'all'},now).map(x=>x.name),['Beta Diner']);
 assert.deepEqual(filterEstablishments(data,{...state,neighbourhood:'Agincourt',search:'café'},now).map(x=>x.name),['Alpha Café']);
});
test('new activity filter measures observation dates, not source inspection dates',()=>{
 const events=[{...data[1],detected_at:'2026-10-23T14:00:00+00:00'}, {...data[0],detected_at:'2026-01-01T12:00:00+00:00'}];
 assert.deepEqual(filterActivity(events,state,now).map(x=>x.name),['Beta Diner']);
});
test('staleness warning starts only after 48 hours',()=>{
 assert.equal(isStale('2026-10-22T15:01:00Z', now),false);
 assert.equal(isStale('2026-10-22T15:00:00Z', now),false);
 assert.equal(isStale('2026-10-22T14:59:59.999Z', now),true);
 assert.equal(isStale('not-a-date', now),true);
});
test('geometry bounds are deterministic',()=>{
 assert.deepEqual(fitBoundsFromFeatures([{geometry:{type:'Polygon',coordinates:[[[0,1],[2,1],[2,4],[0,1]]]}}]),[0,1,2,4]);
});


test('record links use the official City lookup and encode the identifier',()=>{
 assert.equal(cityDineSafeRecordUrl('001Vo000013Qj6QIAS'),'https://www.toronto.ca/community-people/health-wellness-care/health-programs-advice/food-safety/dinesafe/#establishment/001Vo000013Qj6QIAS');
 assert.equal(cityDineSafeRecordUrl('id/with spaces'),'https://www.toronto.ca/community-people/health-wellness-care/health-programs-advice/food-safety/dinesafe/#establishment/id%2Fwith%20spaces');
});
test('record paging reveals additional matches and keeps a map-selected record visible',()=>{
 const records=Array.from({length:81},(_,i)=>({id:`id-${i}`}));
 assert.equal(pageRecords(records,80).length,80);
 assert.equal(pageRecords(records,81).length,81);
 assert.equal(pageRecords(records,80,'id-80').at(-1).id,'id-80');
});
