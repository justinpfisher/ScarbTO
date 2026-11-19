import {staticCopy} from './scarb-voice.mjs';
import {areaFor, councillorFor, WARDS} from './area-selection.mjs';
import {cityDineSafeRecordUrl, displayAddress, filterEstablishments, isStale, relatedSourceRecords} from './logic.mjs';
import {initializePageActions} from './neighbourhood-page-actions.mjs';
import {readerDate} from './reader-date.mjs';
import {renderInspectionFindings} from './inspection-findings.mjs';

const root=globalThis.document?.querySelector('[data-neighbourhood-page]');
const byId=id=>document.getElementById(id);
const escapeText=value=>typeof value==='string'?value:'';
const PAGE_SIZE=20;

function setStatus(message,state=''){
  const node=byId('feed-status');
  node.textContent=message;
  if(state)node.dataset.state=state;else delete node.dataset.state;
}

function renderWards(area){
  const list=byId('ward-links');
  list.replaceChildren();
  for(const code of area.wards||[]){
    const ward=WARDS[String(code)];
    if(!ward)continue;
    const item=document.createElement('li');
    const link=document.createElement('a');
    link.href=councillorFor(code)?.url||'https://www.toronto.ca/city-government/council/members-of-council/';
    link.target='_blank';link.rel='noopener noreferrer';
    link.textContent=staticCopy('neighbourhood-page-dynamic-01',{ VALUE0:(code), VALUE1:(ward.name) });
    item.append(link);list.append(item);
  }
}

export function installAreaPrint({windowRef=globalThis.window,documentRef=globalThis.document,list,summary,showMore,renderAll}){
  let saved=null;
  windowRef?.addEventListener('beforeprint',()=>{
    if(saved)return;
    saved={children:[...list.childNodes],summary:summary.textContent,moreHidden:showMore.hidden,focus:documentRef.activeElement};
    renderAll();
    for(const detail of list.querySelectorAll('details'))detail.open=true;
  });
  windowRef?.addEventListener('afterprint',()=>{
    if(!saved)return;
    list.replaceChildren(...saved.children);summary.textContent=saved.summary;showMore.hidden=saved.moreHidden;
    const focus=saved.focus;saved=null;
    if(focus?.isConnected)focus.focus?.({preventScroll:true});
  });
}

function renderRecords(records,sourceRecords=records){
  const list=byId('inspection-list');
  const summary=byId('record-summary');
  const showMore=byId('show-more');
  let visible=PAGE_SIZE;
  const render=(limit=visible)=>{
    list.replaceChildren();
    for(const row of records.slice(0,limit)){
      const item=document.createElement('li');item.className='record-item';
      const heading=document.createElement('h3');heading.textContent=escapeText(row.name)||'Name not listed';item.append(heading);
      const meta=document.createElement('p');meta.className='record-meta';
      const inspectionDate=readerDate(row.inspection_date);
      const parts=[escapeText(row.status)||'Inspection result not listed',inspectionDate!=='Date unavailable'?staticCopy('neighbourhood-page-dynamic-02',{ VALUE0:(inspectionDate) }):'Inspection date not listed',displayAddress(row.address)||'Address not listed'];
      meta.textContent=parts.join(' · ');item.append(meta);
      const detail=document.createElement('details');
      const label=document.createElement('summary');label.textContent='View inspection findings';detail.append(label,renderInspectionFindings(document,row));item.append(detail);
      if(row.id!==undefined&&row.id!==null&&String(row.id)!==''){
        const source=document.createElement('a');source.className='record-source';source.href=cityDineSafeRecordUrl(row.id);source.target='_blank';source.rel='noopener noreferrer';source.textContent="See the City's record";item.append(source);
      }
      const related=relatedSourceRecords(sourceRecords,row);
      if(related.length){
        const group=document.createElement('details'),title=document.createElement('summary');
        title.textContent=staticCopy('neighbourhood-page-01');group.append(title);
        const note=document.createElement('p');note.textContent=staticCopy('neighbourhood-page-02');group.append(note);
        for(const other of related){
          const p=document.createElement('p'),link=document.createElement('a');
          link.href=cityDineSafeRecordUrl(other.id);link.target='_blank';link.rel='noopener noreferrer';
          link.textContent=staticCopy('neighbourhood-page-dynamic-03',{ VALUE0:(other.id), VALUE1:(other.status||'result not listed'), VALUE2:(readerDate(other.inspection_date)) });
          p.append(link);group.append(p);
        }
        item.append(group);
      }
      list.append(item);
    }
    summary.textContent=records.length?staticCopy('neighbourhood-page-dynamic-04',{ VALUE0:(Math.min(limit,records.length)), VALUE1:(records.length) }):staticCopy('neighbourhood-page-03');
    showMore.hidden=limit>=records.length;
  };
  showMore.onclick=()=>{visible+=PAGE_SIZE;render();};
  render();
  installAreaPrint({list,summary,showMore,renderAll:()=>render(records.length)});
}

async function loadPage(){
  if(!root)return;
  const area=areaFor('neighbourhood',root.dataset.areaCode);
  if(!area){setStatus(staticCopy('neighbourhood-page-04'),'error');return;}
  document.title=staticCopy('neighbourhood-page-dynamic-05',{ VALUE0:(area.name) });
  byId('page-title').textContent=area.name;
  byId('map-link').href=`/?areaKind=neighbourhood&areaCode=${encodeURIComponent(area.code)}&mode=all&days=all`;
  renderWards(area);
  try{
    const response=await fetch('../data/snapshot.json',{cache:'no-cache'});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const candidate=await response.json();
    if(candidate?.schema_version!==1||candidate.ready!==true||!Array.isArray(candidate.establishments)||candidate.establishments.length===0)throw new Error("The City records aren't ready to show");
    const records=filterEstablishments(candidate.establishments,{mode:'all',status:'all',days:'all',neighbourhood:'',areaKind:'neighbourhood',areaCode:area.code,search:''});
    const stale=isStale(candidate.published_at);
    const checked=readerDate(candidate.published_at);
    setStatus(stale?staticCopy('neighbourhood-page-dynamic-06',{ VALUE0:(checked) }):staticCopy('neighbourhood-page-dynamic-07',{ VALUE0:(checked) }),stale?'warning':'');
    const provenance=byId('source-provenance');
    if(provenance)provenance.textContent=staticCopy('neighbourhood-page-dynamic-08',{ VALUE0:(candidate.published_at), VALUE1:(candidate.source?.last_refreshed||'not supplied') });
    renderRecords(records,candidate.establishments);
  }catch(error){
    byId('inspection-list').replaceChildren();
    byId('record-summary').textContent='';
    byId('show-more').hidden=true;
    setStatus(staticCopy('neighbourhood-page-05'),'error');
  }
}

void loadPage();
initializePageActions();
