// Reviewed against the official DineSafe wording and codes on 12 November 2026.
// Exact matches only: an unfamiliar finding is never assigned an invented meaning.
import {SOURCE_TRANSLATIONS} from './inspection-translations.mjs';
export const FINDING_SOURCE='https://open.toronto.ca/dataset/dinesafe/';
const translations=new Map([
  ...SOURCE_TRANSLATIONS,
  ['food premise maintained in manner permitting adverse effect on food - sec. 7(1)(a)(iii)','Conditions at the premises could adversely affect the food. This finding does not establish that contamination or illness occurred.'],
  ['fail to maintain handwashing stations (liquid soap and paper towels) - sec. 7(3)(c)','Handwashing stations were not properly maintained with liquid soap and paper towels.'],
  ['fail to protect food from contamination or adulteration - sec. 26(1)','Food was not adequately protected from contamination or adulteration. This does not establish that contamination occurred.'],
  ['maintain potentially hazardous foods at internal temperature between 4°c and 60°c - sec. 27(1)','Food requiring temperature control was held between 4°C and 60°C.'],
  ['fail to ensure equipment surface cleaned as necessary - sec. 22','Equipment surfaces were not cleaned as required.'],
]);
export const presentText=value=>typeof value==='string'&&!/^(?:none|null|undefined|n\/a)?$/i.test(value.trim())?value.trim():'';
export function explainFinding(wording) {
  return translations.get(presentText(wording).toLocaleLowerCase('en-CA')) || null;
}
export function availableFindings(entry) {
  if(Array.isArray(entry.inspection_findings))return entry.inspection_findings.filter(row=>presentText(row?.wording));
  const wording=presentText(entry.inspection_detail);
  return wording?[{wording}]:[];
}
export function renderInspectionFindings(document,entry) {
  const root=document.createElement('section');root.className='inspection-findings';
  const add=(parent,tag,text)=>{const el=document.createElement(tag);el.textContent=text;parent.append(el);return el;};
  const rows=availableFindings(entry);
  add(root,'p',Array.isArray(entry.inspection_findings)
    ? `${rows.length} available finding${rows.length===1?'':'s'} in the City's records for this date and outcome. The source does not supply an inspection identifier; check the official report for the full inspection.`
    : 'This saved preview may omit findings. Open the City report for the full inspection.');
  if(rows.length){
    const list=document.createElement('ul');root.append(list);
    for(const row of rows){
      const text=explainFinding(row.wording);
      add(list,'li',text||'The City recorded an additional finding. Its original wording is in the source details below; check the official report for its meaning.');
    }
  }else add(root,'p','No finding text is supplied here. This is not a claim that the inspection found no problems.');
  const details=document.createElement('details');details.className='inspection-originals';
  add(details,'summary','Original findings and source details');
  add(details,'p',`City outcome: ${entry.status}. Inspection date: ${entry.inspection_date}.`);
  if(presentText(entry.type))add(details,'p',`City category: ${entry.type}`);
  for(const row of Array.isArray(entry.inspection_findings)?entry.inspection_findings:rows){
    const item=document.createElement('div');details.append(item);
    for(const [key,label] of [['wording','Original finding'],['severity','Source severity'],['category','Source category'],['row_id','Source row ID'],['inspection_date','Original date'],['observation','Source observation'],['outcome_date','Prosecution outcome date'],['outcome','Prosecution outcome'],['fine','Fine']]){
      if(row[key]!==undefined&&row[key]!==null)add(item,'p',`${label}: ${row[key]}`);
    }
  }
  root.append(details);return root;
}
