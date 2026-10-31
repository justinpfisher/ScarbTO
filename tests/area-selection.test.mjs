import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {areaFor, areaForName, areaMatches, councillorFor, WARDS, NEIGHBOURHOODS, validateAreaFeatures} from '../docs/area-selection.mjs';
import {filterEstablishments} from '../docs/logic.mjs';

function feature(code,name,lon=-79.25,lat=43.76) {
  return {type:'Feature',properties:{AREA_SHORT_CODE:code,AREA_NAME:name},
    geometry:{type:'Polygon',coordinates:[[[lon,lat],[lon+.005,lat],[lon+.005,lat+.005],[lon,lat+.005],[lon,lat]]]}};
}
function collection(kind) {
  const dict=kind==='ward'?WARDS:NEIGHBOURHOODS;
  return {type:'FeatureCollection',features:Object.entries(dict).map(([code,v])=>feature(code,v.name))};
}

test('official research-contract registry is reused without reclassifying selected 30 neighbourhoods',async()=>{
  const path=fileURLToPath(new URL('../research/phase1b-csi/fixtures/official-source-contract/scarbto-neighbourhood158-source-contract-2026-10-27.json',import.meta.url));
  const contract=JSON.parse(await readFile(path,'utf8'));
  const registry=new Map(contract.registry.map(r=>[r.AREA_SHORT_CODE,r.AREA_NAME]));
  assert.equal(Object.keys(NEIGHBOURHOODS).length,30);
  assert.equal(Object.keys(WARDS).length,6);
  assert.deepEqual(Object.keys(NEIGHBOURHOODS).sort(),contract.scarborough_selection.selected_codes.slice().sort());
  for(const [code,record] of Object.entries(NEIGHBOURHOODS)){
    const measured=contract.spatial_crosswalk.find(row=>row.code===code);
    assert.equal(record.name,registry.get(code));
    assert.deepEqual(record.wards,measured.ward_overlaps.filter(row=>row.fraction_of_neighbourhood>=.01).map(row=>row.ward_code).sort());
  }
  assert.deepEqual(areaFor('neighbourhood','125').wards,['20','21']);
  assert.deepEqual(areaFor('neighbourhood','139').wards,['20','24']);
  assert.equal(areaFor('neighbourhood','046'),null,'tiny overlap is not qualified Scarborough membership');
});

test('official boundary files must have exact valid source IDs, names, counts and closed rings',()=>{
  for(const kind of ['ward','neighbourhood']) {
    const good=collection(kind);
    assert.equal(validateAreaFeatures(kind,good),good);
    const dup=structuredClone(good);dup.features[1].properties.AREA_SHORT_CODE=dup.features[0].properties.AREA_SHORT_CODE;
    assert.throws(()=>validateAreaFeatures(kind,dup),/duplicated/);
    const missing=structuredClone(good);missing.features.pop();
    assert.throws(()=>validateAreaFeatures(kind,missing),/count/);
    const renamed=structuredClone(good);renamed.features[0].properties.AREA_NAME='An invented name';
    assert.throws(()=>validateAreaFeatures(kind,renamed),/changed/);
    const open=structuredClone(good);open.features[0].geometry.coordinates[0].pop();
    assert.throws(()=>validateAreaFeatures(kind,open),/ring/);
    const outside=structuredClone(good);outside.features[0].geometry.coordinates[0][1][0]=-100;
    assert.throws(()=>validateAreaFeatures(kind,outside),/outside Toronto/);
  }
});

test('one selected area filters establishments by actual source neighbourhood or ward, never proportionally',()=>{
  const items=[
    {name:'A',address:'',status:'Pass',inspection_date:'2026-10-25',neighbourhood:'Ionview',ward:'Scarborough Southwest'},
    {name:'B',address:'',status:'Pass',inspection_date:'2026-10-25',neighbourhood:'Ionview',ward:'Scarborough Centre'},
    {name:'C',address:'',status:'Pass',inspection_date:'2026-10-25',neighbourhood:'Oakridge',ward:'Scarborough Southwest'},
  ];
  const st={status:'all',days:'all',search:'',neighbourhood:'',areaKind:'neighbourhood',areaCode:'125'};
  assert.deepEqual(filterEstablishments(items,st).map(x=>x.name),['A','B'],'whole neighbourhood DineSafe matches without pretending single-ward containment');
  assert.deepEqual(filterEstablishments(items,{...st,areaKind:'ward',areaCode:'20'}).map(x=>x.name),['A','C']);
  assert.deepEqual(filterEstablishments(items,{...st,areaKind:'',areaCode:'',neighbourhood:'Oakridge'}).map(x=>x.name),['C']);
  assert.equal(areaMatches(items[0],{areaKind:'ward',areaCode:'99'}),false);
  assert.equal(areaForName('neighbourhood','Ionview')?.code,'125');
});

test('Ward 23 councillor transition is effective at term start, not election certification',()=>{
  const before=councillorFor('23',new Date('2026-11-14T18:00:00Z'));
  const after=councillorFor('23',new Date('2026-11-15T18:00:00Z'));
  assert.equal(before.name,'Jamaal Myers');
  assert.equal(before.transition,'Shaun Chen');
  assert.equal(after.name,'Shaun Chen');
  assert.equal(after.transition,null);
  assert.match(after.url,/councillor-ward-23/);
  assert.equal(councillorFor('20').name,'Parthi Kandavel');
});
