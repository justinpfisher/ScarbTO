import test from 'node:test';
import assert from 'node:assert/strict';
import {boundsFromFeatures, expandBounds, responsiveMapPadding, unionBoundary} from '../docs/geometry.mjs';

const rectangle=(west,south,east,north)=>[[west,south],[east,south],[east,north],[west,north],[west,south]];
const polygon=coordinates=>({type:'Feature',properties:{},geometry:{type:'Polygon',coordinates}});

test('adjacent neighborhood polygons dissolve shared edges into one outline',()=>{
  const result=unionBoundary([polygon([rectangle(0,0,1,1)]),polygon([rectangle(1,0,2,1)])]);
  const rings=result.features[0].geometry.coordinates;
  assert.equal(rings.length,1);
  assert.equal(rings[0][0].join(','),rings[0].at(-1).join(','));
  assert.deepEqual(boundsFromFeatures([polygon([rings[0]])]),[[0,0],[2,1]]);
});

test('polygon holes and multipolygon islands remain separate closed boundary rings',()=>{
  const hole=unionBoundary([polygon([rectangle(0,0,10,10),rectangle(3,3,7,7).reverse()])]);
  const islands=unionBoundary([{type:'Feature',properties:{},geometry:{type:'MultiPolygon',coordinates:[[rectangle(0,0,1,1)],[rectangle(4,4,5,5)]]}}]);
  assert.equal(hole.features[0].geometry.coordinates.length,2);
  assert.equal(islands.features[0].geometry.coordinates.length,2);
});

test('incompatible shared-edge segmentation fails closed',()=>{
  const left=polygon([[[0,0],[1,0],[1,0.5],[1,1],[0,1],[0,0]]]);
  const right=polygon([rectangle(1,0,2,1)]);
  assert.throws(()=>unionBoundary([left,right]),/Boundary is not closed/);
});

test('buffered viewport retains edge points and mobile fit padding is responsive',()=>{
  const features=[polygon([rectangle(-79.3,43.67,-79.12,43.85)])];
  const bounds=boundsFromFeatures(features),camera=expandBounds(bounds,{longitude:0.04,latitude:0.03});
  assert.ok(camera[0][0]<-79.3&&camera[0][1]<43.67&&camera[1][0]>-79.12&&camera[1][1]>43.85);
  const desktop=responsiveMapPadding(1000,660),mobile=responsiveMapPadding(360,300);
  assert.ok(mobile.left<desktop.left&&mobile.top>=12&&mobile.bottom>=12);
  assert.throws(()=>responsiveMapPadding(0,300),/Map size/);
});
