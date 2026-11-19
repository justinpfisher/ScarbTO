/** Retained directory facts for the existing static.directory-intro request. */
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {NEIGHBOURHOODS} from '../docs/area-selection.mjs';
const CONTRACT='research/phase1b-csi/fixtures/official-source-contract/scarbto-neighbourhood158-source-contract-2026-10-27.json';
const PIN='0f16bf16cde47f382f21003050a978251f71c258581746d64c9a8c9f5ae8564e';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const need=(ok,message)=>{if(!ok)throw new Error(message);};
export function directoryEvidence(bytes=readFileSync(new URL('../'+CONTRACT,import.meta.url)),areas=NEIGHBOURHOODS) {
  need(Buffer.isBuffer(bytes)&&sha(bytes)===PIN,'Retained directory source changed');
  const contract=JSON.parse(bytes),codes=Object.keys(areas).sort();
  need(JSON.stringify(codes)===JSON.stringify([...contract.scarborough_selection.selected_codes].sort()),'Retained directory selection changed');
  const registry=new Map(contract.registry.map(row=>[row.AREA_SHORT_CODE,row.AREA_NAME]));
  need(codes.every(code=>areas[code].name===registry.get(code)),'Retained directory name changed');
  const fact=JSON.stringify({qualified_directory_count:codes.length,selected_codes:codes,
    names:codes.map(code=>({code,name:areas[code].name})),selection_method:contract.scarborough_selection.method,
    publisher_supplied_membership_attribute:false,contract_created_at:contract.created_at,
    official_dataset:contract.geography.dataset_url,licence:contract.geography.licence_url,
    scope:'Retained derived map selection; not official City membership or current inspection conditions. COUNT is supplied by the directory generator from this verified selection.'});
  return [{id:'directory.retained-selection',source:'repo:'+CONTRACT+'#scarborough_selection',sha256:sha(fact),fact}];
}
