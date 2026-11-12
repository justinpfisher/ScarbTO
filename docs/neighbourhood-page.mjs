import {areaFor, councillorFor, WARDS} from './area-selection.mjs';
import {cityCatalogueRefreshText, cityDineSafeRecordUrl, displayAddress, filterEstablishments, isStale} from './logic.mjs';
import {initializePageActions} from './neighbourhood-page-actions.mjs';

const root=document.querySelector('[data-neighbourhood-page]');
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
    link.textContent=`Ward ${code} — ${ward.name}: Find your City councillor`;
    item.append(link);list.append(item);
  }
}

function renderRecords(records){
  const list=byId('inspection-list');
  const summary=byId('record-summary');
  const showMore=byId('show-more');
  let visible=PAGE_SIZE;
  const render=()=>{
    list.replaceChildren();
    for(const row of records.slice(0,visible)){
      const item=document.createElement('li');item.className='record-item';
      const heading=document.createElement('h3');heading.textContent=escapeText(row.name)||'Name not listed';item.append(heading);
      const meta=document.createElement('p');meta.className='record-meta';
      const parts=[escapeText(row.status)||'Inspection result not listed',row.inspection_date?`Inspected ${escapeText(row.inspection_date)}`:'Inspection date not listed',displayAddress(row.address)||'Address not listed'];
      meta.textContent=parts.join(' · ');item.append(meta);
      if(row.inspection_detail){const detail=document.createElement('p');detail.className='record-detail';detail.textContent=`The inspection record says: ${escapeText(row.inspection_detail)}`;item.append(detail);}
      if(row.id!==undefined&&row.id!==null&&String(row.id)!==''){
        const source=document.createElement('a');source.className='record-source';source.href=cityDineSafeRecordUrl(row.id);source.target='_blank';source.rel='noopener noreferrer';source.textContent="See the City's record";item.append(source);
      }
      list.append(item);
    }
    summary.textContent=records.length?`Showing ${Math.min(visible,records.length)} of ${records.length} places listed here by the City.`:"I didn't find any places labelled with this neighbourhood in the DineSafe records checked. That doesn't mean there are none.";
    showMore.hidden=visible>=records.length;
  };
  showMore.onclick=()=>{visible+=PAGE_SIZE;render();};
  render();
}

async function loadPage(){
  if(!root)return;
  const area=areaFor('neighbourhood',root.dataset.areaCode);
  if(!area){setStatus("I couldn't find this neighbourhood page. Choose a neighbourhood from the Scarb.TO map instead.",'error');return;}
  document.title=`${area.name} · Scarb.TO`;
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
    const cityTime=cityCatalogueRefreshText(candidate.source?.last_refreshed);
    const checked=typeof candidate.published_at==='string'?candidate.published_at:'time not listed';
    setStatus(stale?`These results may be out of date. Last checked ${checked}. ${cityTime}. Check the City's record for anything newer.`:`Last checked ${checked}. ${cityTime}. These are dated results, not a live inspection service.`,stale?'warning':'');
    renderRecords(records);
  }catch(error){
    byId('inspection-list').replaceChildren();
    byId('record-summary').textContent='';
    byId('show-more').hidden=true;
    setStatus("I couldn't load the food inspection results. That doesn't mean there are no records here. Try again or check the City's DineSafe data below.",'error');
  }
}

void loadPage();
initializePageActions();
