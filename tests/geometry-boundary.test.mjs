import test from 'node:test';
import assert from 'node:assert/strict';
import {aspectAwareMapBounds, boundsFromFeatures, expandBounds, responsiveMapPadding, scarboroughWardQueryURL, unionBoundary, validateScarboroughWardFeatures} from '../docs/geometry.mjs';

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

const wardFeature=(code)=>({type:'Feature',properties:{AREA_ID:code,AREA_SHORT_CODE:String(code),AREA_LONG_CODE:String(code),AREA_NAME:`Ward ${code}`,OBJECTID:code},geometry:{type:'Polygon',coordinates:[rectangle(-79.4+code*.001,43.65,-79.3+code*.001,43.75)]}});

test('ward query is exact, bounded, and requests geographic polygon output',()=>{
  const url=new URL(scarboroughWardQueryURL());
  assert.equal(url.origin,'https://gis.toronto.ca');
  assert.equal(url.pathname,'/arcgis/rest/services/cot_geospatial22/FeatureServer/0/query');
  assert.equal(url.searchParams.get('where'),"AREA_SHORT_CODE IN ('20','21','22','23','24','25')");
  assert.equal(url.searchParams.get('outFields'),'AREA_ID,AREA_SHORT_CODE,AREA_LONG_CODE,AREA_NAME,OBJECTID');
  assert.equal(url.searchParams.get('returnGeometry'),'true');
  assert.equal(url.searchParams.get('outSR'),'4326');
  assert.equal(url.searchParams.get('f'),'geojson');
  assert.equal(url.searchParams.get('orderByFields'),'AREA_SHORT_CODE');
  assert.equal(url.searchParams.get('resultRecordCount'),'7');
});

test('ward boundary validator requires exactly the six administrative wards',()=>{
  const features=[20,21,22,23,24,25].map(wardFeature);
  assert.deepEqual(validateScarboroughWardFeatures(features,{responseBytes:2500}).map(f=>f.properties.AREA_SHORT_CODE),['20','21','22','23','24','25']);
  assert.throws(()=>validateScarboroughWardFeatures(features.slice(0,5),{responseBytes:2500}),/exactly six/);
  assert.throws(()=>validateScarboroughWardFeatures([...features.slice(0,5),wardFeature(24)],{responseBytes:2500}),/unique and exactly/);
  assert.throws(()=>validateScarboroughWardFeatures(features,{responseBytes:20*1024*1024+1}),/byte limit/);
  assert.throws(()=>validateScarboroughWardFeatures(features,{responseBytes:2500,maxVertices:23}),/vertex limit/);
});

test('aspect-aware max bounds fit the source bounds in short-wide and desktop viewports',()=>{
  const source=[[-79.43,43.65],[-79.09,43.89]];
  const mercator=lat=>Math.log(Math.tan(Math.PI/4+lat*Math.PI/360));
  for(const [width,height] of [[1048,660],[900,340]]){
    const fit=aspectAwareMapBounds(source,width,height,{padding:16,bufferFraction:.08});
    assert.ok(fit[0][0]<source[0][0]&&fit[0][1]<source[0][1]);
    assert.ok(fit[1][0]>source[1][0]&&fit[1][1]>source[1][1]);
    const projectedAspect=((fit[1][0]-fit[0][0])*Math.PI/180)/(mercator(fit[1][1])-mercator(fit[0][1]));
    const usableAspect=(width-32)/(height-32);
    assert.ok(Math.abs(projectedAspect-usableAspect)<1e-10,`${width}x${height}: ${projectedAspect} != ${usableAspect}`);
  }
  assert.throws(()=>aspectAwareMapBounds(source,900,340,{padding:200}),/viewport dimensions/);
});

