import {areaFor, councillorFor, WARDS} from './area-selection.mjs';
import {cityCatalogueRefreshText, cityDineSafeRecordUrl, displayAddress, filterEstablishments, isStale} from './logic.mjs';

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
    link.textContent=`Ward ${code} — ${ward.name}: City councillor information`;
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
      const heading=document.createElement('h3');heading.textContent=escapeText(row.name)||'Unnamed establishment';item.append(heading);
      const meta=document.createElement('p');meta.className='record-meta';
      const parts=[escapeText(row.status)||'Inspection outcome not supplied',row.inspection_date?`Inspected ${escapeText(row.inspection_date)}`:'Inspection date not supplied',displayAddress(row.address)||'Address not supplied'];
      meta.textContent=parts.join(' · ');item.append(meta);
      if(row.inspection_detail){const detail=document.createElement('p');detail.className='record-detail';detail.textContent=`Inspection detail: ${escapeText(row.inspection_detail)}`;item.append(detail);}
      if(row.id!==undefined&&row.id!==null&&String(row.id)!==''){
        const source=document.createElement('a');source.className='record-source';source.href=cityDineSafeRecordUrl(row.id);source.target='_blank';source.rel='noopener noreferrer';source.textContent='View official City record';item.append(source);
      }
      list.append(item);
    }
    summary.textContent=`Showing ${Math.min(visible,records.length)} of ${records.length} City-assigned establishments in this published snapshot.`;
    showMore.hidden=visible>=records.length;
  };
  showMore.onclick=()=>{visible+=PAGE_SIZE;render();};
  render();
}

async function loadPage(){
  if(!root)return;
  const area=areaFor('neighbourhood',root.dataset.areaCode);
  if(!area){setStatus('This neighbourhood page is unavailable. Choose an area from the Scarb.TO map.','error');return;}
  document.title=`${area.name} · Scarb.TO`;
  byId('page-title').textContent=area.name;
  byId('map-link').href=`/?areaKind=neighbourhood&areaCode=${encodeURIComponent(area.code)}&mode=all&days=all`;
  renderWards(area);
  try{
    const response=await fetch('../data/snapshot.json',{cache:'no-cache'});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const candidate=await response.json();
    if(candidate?.schema_version!==1||candidate.ready!==true||!Array.isArray(candidate.establishments))throw new Error('No validated City snapshot is available');
    const records=filterEstablishments(candidate.establishments,{mode:'all',status:'all',days:'all',neighbourhood:'',areaKind:'neighbourhood',areaCode:area.code,search:''});
    const stale=isStale(candidate.published_at);
    const cityTime=cityCatalogueRefreshText(candidate.source?.last_refreshed);
    const checked=typeof candidate.published_at==='string'?candidate.published_at:'time not supplied';
    setStatus(stale?`Scarb.TO data may be stale; last checked ${checked}. ${cityTime}.`:`Scarb.TO checked ${checked}. ${cityTime}. This is not live inspection data.`,stale?'warning':'');
    renderRecords(records);
  }catch(error){
    byId('inspection-list').replaceChildren();
    byId('record-summary').textContent='';
    byId('show-more').hidden=true;
    setStatus(`City DineSafe data is unavailable: ${error?.message||'request failed'}. The page does not treat this as zero records.`,'error');
  }
}

void loadPage();
