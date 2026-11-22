import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {retainedIonviewRequest, catalogueRequests, pythonCatalogueRequests, shellCatalogueRequests, sha, protect} from '../scripts/collect_scarb_ai_requests.mjs';
import {SCARB_COPY} from '../docs/scarb-voice.mjs';
const paths = [
  'research/phase1b-csi/fixtures/official-source-contract/scarbto-neighbourhood158-source-contract-2026-10-27.json',
  'docs/area-selection.mjs',
  'docs/community-data/releases/887085d7e735b7e9f8484013abe2fa0193ae812f421cc9bca3b16f17003e4655.json',
  'docs/community-data/boundaries/9412f1c2737d7b0165867c7e6a38dd5e7549b834d0184cb9923c4241a85dd3f7.json',
  'docs/data/scarborough-neighbourhoods.geojson'
];
const inputs = Object.fromEntries(paths.map(path => [path,readFileSync(new URL('../'+path,import.meta.url))]));
test('retained geography constructor matches pinned source projection without publishing it', () => {
  const packet=retainedIonviewRequest(inputs);
  const facts=JSON.parse(packet.evidence[0].fact);
  const contract=JSON.parse(inputs[paths[0]]);
  const row=contract.spatial_crosswalk.find(row=>row.code==='125');
  const registry=JSON.parse(inputs[paths[3]]);
  const area=Object.values(registry).find(area=>area.city_code==='125');
  const release=JSON.parse(inputs[paths[2]]);
  assert.equal(release.registry_sha256,sha(registry));
  assert.equal(area.verification,'verified');
  assert.equal(facts.name,area.name);
  assert.equal(packet.locks.LIMIT,area.coverage_note);
  assert.equal(facts.coverage_note,area.coverage_note);
  assert.equal(facts.contract_created_at,contract.created_at);
  assert.deepEqual(facts.ward_codes,row.ward_overlaps.filter(x=>x.fraction_of_neighbourhood>=.01).map(x=>x.ward_code).sort());
  assert.equal(packet.evidence[0].sha256,sha(facts));
  assert.deepEqual([packet.locks.WARD_A,packet.locks.WARD_B],facts.ward_codes);
  assert.equal(packet.id,'geography.home-ionview-boundaries');
  const required=[...catalogueRequests(SCARB_COPY),...pythonCatalogueRequests(),...shellCatalogueRequests()];
  assert.equal(required.length,736);
  assert.equal(required.some(x=>x.id===packet.id),false);
});
for (const path of paths) {
  test('changed retained input is refused: '+path,()=>assert.throws(()=>retainedIonviewRequest({...inputs,[path]:Buffer.concat([inputs[path],Buffer.from(' ')])}),/evidence changed/));
  test('missing retained input is refused: '+path,()=>{const missing={...inputs};delete missing[path];assert.throws(()=>retainedIonviewRequest(missing),/source set/);});
}
test('extra input is refused',()=>assert.throws(()=>retainedIonviewRequest({...inputs,extra:Buffer.from('x')}),/source set/));
test('every request is independently constructed',()=>{const first=retainedIonviewRequest(inputs);first.locks.NAME='changed';assert.equal(retainedIonviewRequest(inputs).locks.NAME,'Ionview');});

test('exact LF Git mapping and CRLF checkout have identical request identity',()=>{
  const lf=Buffer.from(inputs['docs/area-selection.mjs'].toString('utf8').replaceAll('\r\n','\n'));
  const crlf=Buffer.from(lf.toString('utf8').replaceAll('\n','\r\n'));
  assert.deepEqual(retainedIonviewRequest({...inputs,'docs/area-selection.mjs':lf}),retainedIonviewRequest({...inputs,'docs/area-selection.mjs':crlf}));
});

test('existing official licence locks retain Unicode en-dash wording',()=>{
  for(const place of ['Toronto','Ontario']){const text='Open Government Licence \u2013 '+place;const result=protect(text);assert.deepEqual(Object.values(result.locks),[text]);}
});
