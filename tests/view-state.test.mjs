import test from 'node:test';
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
