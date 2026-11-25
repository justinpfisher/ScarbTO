import test from 'node:test';
import {filterEstablishments} from '../docs/logic.mjs';
import assert from 'node:assert/strict';
import {viewFromSearch,searchFromView} from '../docs/view-state.mjs';
test('public filters round-trip independently from selected map geometry',()=>{
  const v=viewFromSearch('?mode=all&days=all&overlay=ward&areaKind=ward&areaCode=25&neighbourhood=West+Rouge&q=tea&status=Pass');
  assert.deepEqual(viewFromSearch(searchFromView(v.state,v.overlay)),v);
  const cleared=viewFromSearch(searchFromView({...v.state,areaKind:'',areaCode:''},'off'));
  assert.equal(cleared.state.neighbourhood,'West Rouge');assert.equal(cleared.state.search,'');assert.equal(cleared.state.status,'Pass');
  assert.equal(cleared.state.areaKind,'');
});
test('free-text searches never enter public links',()=>{
  const state={...viewFromSearch('').state,search:'123 Private Home Road'};
  assert.equal(new URLSearchParams(searchFromView(state)).has('q'),false);
});
test('legacy area links work; incompatible or invalid geometry is not hidden',()=>{
  assert.equal(viewFromSearch('?areaKind=neighbourhood&areaCode=143').overlay,'neighbourhood');
  assert.equal(viewFromSearch('?overlay=off&areaKind=ward&areaCode=25').state.areaCode,'');
  assert.equal(viewFromSearch('?overlay=ward&areaKind=neighbourhood&areaCode=143').state.areaCode,'');
});

const knownNeighbourhoods=['West Rouge','Pleasant View','Wexford/Maryvale'];

test('post-load history drops unknown neighbourhoods without hiding otherwise matching records',()=>{
  const search='?mode=all&days=all&overlay=off&neighbourhood=Fabricated+Unknown+Neighbourhood';
  const records=[{id:'synthetic',name:'Synthetic cafe',address:'',status:'Pass',neighbourhood:'Pleasant View'}];
  const before=viewFromSearch(search);
  assert.equal(filterEstablishments(records,before.state).length,0);
  const restored=viewFromSearch(search,knownNeighbourhoods);
  assert.equal(restored.state.neighbourhood,'');
  assert.equal(filterEstablishments(records,restored.state).length,1);
  assert.equal(new URLSearchParams(searchFromView(restored.state,restored.overlay)).has('neighbourhood'),false);
  assert.deepEqual(viewFromSearch(search,undefined),before);
  assert.equal(viewFromSearch(search,[]).state.neighbourhood,'');
});

test('post-load history preserves provided source choices including Pleasant View',()=>{
  for(const neighbourhood of knownNeighbourhoods){
    const search='?'+new URLSearchParams({mode:'all',days:'all',neighbourhood});
    const restored=viewFromSearch(search,knownNeighbourhoods);
    assert.equal(restored.state.neighbourhood,neighbourhood);
    assert.deepEqual(viewFromSearch(searchFromView(restored.state,restored.overlay),knownNeighbourhoods),restored);
  }
});

test('known neighbourhood validation leaves public modes, filters, privacy and geometry unchanged',()=>{
  for(const mode of ['recent','all','beach','selected-calls']){
    for(const geometry of ['', '&areaKind=neighbourhood&areaCode=143', '&overlay=ward&areaKind=ward&areaCode=25', '&overlay=off&areaKind=ward&areaCode=25', '&overlay=ward&areaKind=neighbourhood&areaCode=143', '&overlay=ward&areaKind=ward&areaCode=invalid']){
      const search=`?mode=${mode}&days=90&status=Pass&q=private+search${geometry}`;
      const original=viewFromSearch(search);
      assert.deepEqual(viewFromSearch(search,knownNeighbourhoods),original);
      assert.deepEqual(viewFromSearch(search+'&neighbourhood=Unknown',knownNeighbourhoods),original);
      const legitimate=viewFromSearch(search+'&neighbourhood=Pleasant+View',knownNeighbourhoods);
      assert.deepEqual(legitimate,{...original,state:{...original.state,neighbourhood:'Pleasant View'}});
      assert.equal(legitimate.state.search,'');
      assert.equal(new URLSearchParams(searchFromView({...legitimate.state,search:'private search'},legitimate.overlay)).has('q'),false);
    }
  }
});
