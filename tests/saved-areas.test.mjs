import test from 'node:test';
import assert from 'node:assert/strict';
import {validatedAreas, publicAreaHref, mountSavedAreas, SAVED_AREAS_KEY} from '../docs/saved-areas.mjs';

test('saved public identities reject unknown areas, deduplicate and discard arbitrary data',()=>{
  assert.deepEqual(validatedAreas([{kind:'ward',code:20,name:'invented',address:'private'}, {kind:'ward',code:'20'}, null, {kind:'ward',code:'999'}]),[{kind:'ward',code:'20'}]);
  assert.deepEqual(validatedAreas({}),[]);
  assert.equal(publicAreaHref({kind:'neighbourhood',code:'143'}),'/?areaKind=neighbourhood&areaCode=143&mode=all&days=all');
  assert.equal(publicAreaHref({kind:'home',code:'private'}),null);
});
class Element {
  children=[];handlers={};value='';disabled=true;textContent='';
  append(...items){this.children.push(...items);}
  replaceChildren(){this.children=[];}
  setAttribute(key,value){this[key]=value;}
  addEventListener(name,fn){this.handlers[name]=fn;}
  focus(){this.focused=true;}
}
function fixture(storage){
  const els=Object.fromEntries(['saved-area-choice','save-public-area','saved-areas-list','saved-areas-status'].map(id=>[id,new Element()]));
  mountSavedAreas({getElementById:id=>els[id],createElement:()=>new Element()},storage);
  return {els,add(value){els['saved-area-choice'].value=value;els['saved-area-choice'].handlers.change();els['save-public-area'].handlers.click();}};
}
test('multiple areas persist separately, duplicate saves are idempotent, removal restores focus',()=>{
  const values=new Map([['scarbto-filters-v1','untouched'],['scarb-community-finalised','untouched']]);
  const storage={getItem:key=>values.get(key),setItem:(key,value)=>values.set(key,value)};
  const {els,add}=fixture(storage);add('ward:20');add('neighbourhood:143');add('ward:20');
  assert.equal(els['saved-areas-list'].children.length,2);
  assert.match(els['saved-areas-status'].textContent,/already saved/);
  assert.equal(fixture(storage).els['saved-areas-list'].children.length,2);
  els['saved-areas-list'].children[0].children[1].handlers.click();
  assert.equal(els['saved-areas-list'].children.length,1);
  assert.equal(els['saved-area-choice'].focused,true);
  assert.deepEqual(JSON.parse(values.get(SAVED_AREAS_KEY)),[{kind:'neighbourhood',code:'143'}]);
  assert.equal(values.get('scarbto-filters-v1'),'untouched');assert.equal(values.get('scarb-community-finalised'),'untouched');
});
test('unavailable storage does not claim persistence or mutate the list',()=>{
  const {els,add}=fixture({getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}});
  add('ward:20');assert.equal(els['saved-areas-list'].children.length,0);
  assert.match(els['saved-areas-status'].textContent,/could not save/);
});
test('failed remove preserves saved state and malformed storage can recover',()=>{
  const {els}=fixture({getItem:()=>JSON.stringify([{kind:'ward',code:'20'}]),setItem(){throw Error('quota');}});
  els['saved-areas-list'].children[0].children[1].handlers.click();assert.equal(els['saved-areas-list'].children.length,1);
  let saved;const recovery=fixture({getItem:()=>'{',setItem:(key,value)=>saved=value});recovery.add('ward:21');
  assert.deepEqual(JSON.parse(saved),[{kind:'ward',code:'21'}]);
});
