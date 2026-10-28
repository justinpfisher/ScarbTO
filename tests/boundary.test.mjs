import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {cameraBoundsForViewport, COUNCIL_BOUNDARY_BOUNDS, outsideMask, validateCouncilBoundary} from '../docs/boundary.mjs';

const root=resolve(fileURLToPath(new URL('../docs/data/',import.meta.url)));
const boundaryPath=resolve(root,'scarborough-council-boundary.geojson');
const expectedHash='f4e58c66254f2aea1b20c2994e4edc7a9840c170ed45e7841751151f44165aa2';

async function loadBoundary(){
  const bytes=await readFile(boundaryPath);
  const hash=createHash('sha256').update(bytes).digest('hex');
  assert.equal(hash,expectedHash);
  return validateCouncilBoundary(JSON.parse(bytes.toString('utf8')));
}

function area(ring){let sum=0;for(let i=1;i<ring.length;i++)sum+=ring[i-1][0]*ring[i][1]-ring[i][0]*ring[i-1][1];return sum/2;}

test('display geometry is the hash-pinned official Community Council feature',async()=>{
  const feature=await loadBoundary();
  assert.equal(feature.properties.AREA_ID,2476922);
  assert.equal(feature.properties.OBJECTID,17503889);
  assert.equal(feature.geometry.type,'Polygon');
  assert.equal(feature.geometry.coordinates.length,1);
  assert.equal(feature.geometry.coordinates[0].length,5132);
});

test('outside mask preserves the official boundary as a hole and does not filter records',async()=>{
  const feature=await loadBoundary();
  const mask=outsideMask(feature);
  const polygon=mask.features[0].geometry.coordinates;
  assert.equal(mask.features[0].properties.role,'outside-scarborough-mask');
  assert.equal(polygon.length,2);
  assert.ok(area(polygon[0])>0,'world exterior uses counter-clockwise winding');
  assert.ok(area(polygon[1])<0,'Scarborough hole uses clockwise winding');
  assert.deepEqual(polygon[1],feature.geometry.coordinates[0]);
  assert.equal(mask.features[0].properties.filtersRecords,undefined);
});

test('neighbourhood or business feature cannot be substituted for the administrative boundary',async()=>{
  const feature=await loadBoundary();
  assert.throws(()=>validateCouncilBoundary({...feature,properties:{...feature.properties,AREA_NAME:'Pleasant View'}}),/identity/);
  assert.throws(()=>validateCouncilBoundary({...feature,geometry:{type:'MultiPolygon',coordinates:[feature.geometry.coordinates]}}),/one polygon exterior/);
});

test('camera bounds fit full boundary with buffer at desktop and narrow mobile aspect ratios',async()=>{
  await loadBoundary();
  for(const [width,height] of [[1365,900],[1024,660],[390,844],[900,340]]){
    const bounds=cameraBoundsForViewport(width,height);
    assert.ok(bounds[0][0]<COUNCIL_BOUNDARY_BOUNDS[0][0]);
    assert.ok(bounds[0][1]<COUNCIL_BOUNDARY_BOUNDS[0][1]);
    assert.ok(bounds[1][0]>COUNCIL_BOUNDARY_BOUNDS[1][0]);
    assert.ok(bounds[1][1]>COUNCIL_BOUNDARY_BOUNDS[1][1]);
  }
  assert.throws(()=>cameraBoundsForViewport(0,0),/viewport/);
});
