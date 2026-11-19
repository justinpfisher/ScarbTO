// Reviewed against the official DineSafe wording and codes on 12 November 2026.
// Exact matches only: an unfamiliar finding is never assigned an invented meaning.
import {findingVoice} from './scarb-voice.mjs';
export const FINDING_SOURCE='https://open.toronto.ca/dataset/dinesafe/';
export const presentText=value=>typeof value==='string'&&!/^(?:none|null|undefined|n\/a)?$/i.test(value.trim())?value.trim():'';
export function explainFinding(wording) {
  const source=presentText(wording);
  // City row 2913ed6f8436882ab0b231bfcf48292c adds one space after the dash.
  // Match the whole phrase; never change the original displayed source wording.
  const lookup=source.toLocaleLowerCase('en-CA')==='maintain potentially hazardous foods at internal temperature between 4°c and 60°c -  sec. 27(1)'
    ? 'maintain potentially hazardous foods at internal temperature between 4°c and 60°c - sec. 27(1)'
    : source;
  return findingVoice('translation',{wording:lookup});
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
    ? findingVoice('coverage',{count:rows.length})
    : findingVoice('legacy'));
  if(rows.length){
    const list=document.createElement('ul');root.append(list);
    for(const row of rows){
      const text=explainFinding(row.wording);
      add(list,'li',text||findingVoice('untranslated'));
    }
  }else add(root,'p',findingVoice('empty'));
  const details=document.createElement('details');details.className='inspection-originals';
  add(details,'summary',findingVoice('source-title'));
  add(details,'p',findingVoice('outcome',{status:entry.status,date:entry.inspection_date}));
  if(presentText(entry.type))add(details,'p',findingVoice('category',{category:entry.type}));
  for(const row of Array.isArray(entry.inspection_findings)?entry.inspection_findings:rows){
    const item=document.createElement('div');details.append(item);
    for(const [key,label] of [['wording','Original finding'],['severity','Source severity'],['category','Source category'],['row_id','Source row ID'],['inspection_date','Original date'],['observation','Source observation'],['outcome_date','Prosecution outcome date'],['outcome','Prosecution outcome'],['fine','Fine']]){
      if(row[key]!==undefined&&row[key]!==null)add(item,'p',`${label}: ${row[key]}`);
    }
  }
  root.append(details);return root;
}
