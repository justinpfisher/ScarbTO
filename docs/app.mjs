import {DEFAULTS, STATUS, filterActivity, filterEstablishments, isStale, cityDineSafeRecordUrl, pageRecords, fitBoundsFromFeatures} from './logic.mjs';
import {beginListRedraw, finishListRedraw, revealSelectedRecord} from './list-focus.mjs';
import {beachPreviewFeature, renderBeachSamplePreview, validateBeachSamplePreview} from './beach-history.mjs';

const $ = id => document.getElementById(id);
const SCARB_BOUNDS = [[-79.43,43.65],[-79.09,43.89]];
const STORAGE_KEY = 'scarbto-filters-v1';
let state = {...DEFAULTS};
try {
  const remembered = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  if (['recent','all','beach'].includes(remembered.mode)) state.mode = remembered.mode;
  if (['all', ...STATUS].includes(remembered.status)) state.status = remembered.status;
  if (['7','30','90','all'].includes(remembered.days)) state.days = remembered.days;
  if (typeof remembered.neighbourhood === 'string') state.neighbourhood = remembered.neighbourhood;
} catch { /* Private browsing, old preferences or disabled storage must not break the map. */ }
let snapshot = null, beachPreview = null, map = null, selectedId = null, shapes = {type:'FeatureCollection',features:[]};
let features = [], visiblePlaces = [], visibleActivity = [], usingActivity = false, usingBeach = false, listLimit = 80;
let dineSafeStatus={text:'Checking official data.',className:''}, dineSafeLoadState='loading', dineSafeLoadError='', beachPreviewState='loading';

function save() {
  try {const {mode,status,days,neighbourhood}=state;localStorage.setItem(STORAGE_KEY,JSON.stringify({mode,status,days,neighbourhood}));}catch{}
}
function els(tag, cls, value) {
  const element = document.createElement(tag);
  if (cls) element.className = cls;
  if (value !== undefined && value !== null) element.textContent = String(value);
  return element;
}
function publishedAt(iso) {
  const date=new Date(iso);
  if (!Number.isFinite(date.valueOf())) return 'date unavailable';
  return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Toronto',month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(date);
}
function localDate(iso) {
  const t = Date.parse((iso || '').slice(0,10)+'T12:00:00Z');
  return Number.isFinite(t) ? new Intl.DateTimeFormat('en-CA',{timeZone:'UTC',month:'short',day:'numeric',year:'numeric'}).format(t):'Date unavailable';
}
function outcomeClass(status){return status==='Closed'?'closed':status==='Conditional Pass'?'conditional':'pass';}
function syncDataStatus() {
  const status=$('data-status');
  status.classList.remove('error','warning');
  if(state.mode==='beach'){
    if(beachPreviewState==='loading')status.textContent='Loading Toronto beach sample preview.';
    else if(beachPreview){
      const latest=beachPreview.records.reduce((value,row)=>row.collectionDate>value?row.collectionDate:value,'0000-00-00');
      status.textContent=`Toronto sample rows checked ${beachPreview.retrieved_on}; latest sample ${latest}. Not current swimming status.`;
      status.classList.add('warning');
    }else{
      status.textContent='Toronto beach sample preview unavailable. Not current swimming status.';
      status.classList.add('error');
    }
    return;
  }
  if(dineSafeStatus.className)status.classList.add(dineSafeStatus.className);
  status.textContent=dineSafeStatus.text;
}
function setDineSafeStatus(text,className='') {
  dineSafeStatus={text,className};
  syncDataStatus();
}
function syncControls() {
  $('window').value=state.days;
  $('neighbourhood').value=state.neighbourhood;
  $('search').value=state.search;
  document.querySelectorAll('.tab').forEach(b=>{let hit=b.dataset.mode===state.mode;b.classList.toggle('active',hit);b.setAttribute('aria-pressed',String(hit));});
  document.querySelectorAll('.chip').forEach(b=>{let hit=b.dataset.status===state.status;b.classList.toggle('selected',hit);b.setAttribute('aria-pressed',String(hit));});
  const beachMode=state.mode==='beach';
  $('beach-filter-note').hidden=!beachMode;
  document.querySelectorAll('#search,#neighbourhood,#window,.outcomes button').forEach(control=>{control.disabled=beachMode;});
  syncDataStatus();
}
function populateNeighbourhoods() {
  const names=[...new Set(snapshot.establishments.map(e=>e.neighbourhood).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'en-CA'));
  const select=$('neighbourhood');
  for(const name of names){const opt=els('option','',name);opt.value=name;select.append(opt);}
  if(!names.includes(state.neighbourhood))state.neighbourhood='';
  syncControls();
}
function geoFeature(e, activity = false) {
  return {type:'Feature',id:String(e.id),geometry:{type:'Point',coordinates:[e.longitude,e.latitude]},properties:{id:String(e.establishment_id||e.id),name:e.name,status:e.status,activity,selected:String(e.establishment_id||e.id)===selectedId}};
}
function updateSource() {
  if(!map || !map.getSource('places'))return;
  features=usingBeach && beachPreview ? [beachPreviewFeature(beachPreview)] : visiblePlaces.map(e=>geoFeature(e));
  map.getSource('places').setData({type:'FeatureCollection',features});
}
function performFilters() {
  listLimit=80;
  if(state.mode==='beach'){
    usingBeach=true;visiblePlaces=[];visibleActivity=[];usingActivity=false;
    $('results-kicker').textContent='Toronto Open Data · dated samples';
    $('results-title').textContent=beachPreview?.beach_name||'Beach samples';
    $('results-caption').textContent='A limited sample preview from the Toronto catalogue. Dated measurements are not current swimming advice.';
    updateSource();renderList();
    return;
  }
  usingBeach=false;
  if(!snapshot?.ready){
    visiblePlaces=[];visibleActivity=[];usingActivity=false;
    $('results-kicker').textContent='Official inspections';
    $('results-title').textContent='Matching places';
    $('results-caption').textContent='Results follow the map and your filters.';
    updateSource();renderList();
    return;
  }
  // Outcome and neighbourhood refer to a place's current recorded state; the recent window
  // refers to when a change was observed, not when inspected.
  const eligible=filterEstablishments(snapshot.establishments||[],{...state,days:'all'});
  const eligibleIds=new Set(eligible.map(e=>e.id));
  visibleActivity=filterActivity(snapshot.activity||[],{...state,status:'all'}).filter(e=>eligibleIds.has(e.establishment_id));
  usingActivity=state.mode==='recent' && visibleActivity.length>0;
  const activeIds=new Set(visibleActivity.map(e=>e.establishment_id));
  visiblePlaces=usingActivity ? eligible.filter(e=>activeIds.has(e.id)) : filterEstablishments(snapshot.establishments||[],state);
  $('results-kicker').textContent=state.mode==='recent'?(usingActivity?'Changes first observed by Scarb.TO':'Latest City inspection records'):'DineSafe establishments';
  $('results-title').textContent=state.mode==='recent'?(usingActivity?'Recent changes':'Recently inspected'):'Matching places';
  $('results-caption').textContent=usingActivity?'Changes detected on successive daily imports; inspection dates may be older.':
    state.mode==='recent'?'Showing establishments with a recent recorded inspection date; not necessarily newly published.':
    'Showing the latest inspection record available for each establishment.';
  updateSource();renderList();
}
function renderList({focusMore = false, revealSelection = false} = {}) {
  const list=$('record-list');
  const previousFocus=beginListRedraw(list,document.activeElement,{focusMore});
  if(usingBeach){
    $('results-count').textContent=beachPreview?`${beachPreview.rows_included} sample rows`:beachPreviewState==='loading'?'Loading':'Unavailable';
    if(!beachPreview){
      const message=beachPreviewState==='loading'?'Loading the dated Toronto beach sample preview.':'The dated Toronto sample preview is unavailable.';
      list.append(els('p','empty',message));
      const source=els('a','record-source-link','Check Toronto Open Data source');source.href='https://open.toronto.ca/dataset/toronto-beaches-water-quality/';source.target='_blank';source.rel='noopener noreferrer';list.append(source);
      finishListRedraw(list,previousFocus);return;
    }
    list.append(renderBeachSamplePreview(document,beachPreview));
    finishListRedraw(list,previousFocus);return;
  }
  if(!snapshot?.ready){const message=dineSafeLoadState==='error'?`Could not load the published dataset (${dineSafeLoadError}). Check the update history link below.`:dineSafeLoadState==='loading'?'Loading the validated City data snapshot.':'No validated DineSafe snapshot has been published. The map will populate after the first successful import.';list.append(els('p','empty',message));$('results-count').textContent=dineSafeLoadState==='error'?'Unavailable':'0 in view';finishListRedraw(list,previousFocus);return;}
  const bounds=map?.loaded()?map.getBounds():null;
  const inView=e=>!bounds||bounds.contains([e.longitude,e.latitude]);
  const matches=visiblePlaces.filter(inView);
  const allById=new Map(matches.map(e=>[e.id,e]));
  let records=[];
  if(usingActivity){
    const activities=visibleActivity.filter(inView);
    const selected=new Set();
    for(const event of activities){if(allById.has(event.establishment_id) && !selected.has(event.establishment_id)){records.push({...allById.get(event.establishment_id),event});selected.add(event.establishment_id);}}
    for(const entry of matches){if(!selected.has(entry.id))records.push(entry);}
  } else {
    records=matches.sort((a,b)=>b.inspection_date.localeCompare(a.inspection_date)||a.name.localeCompare(b.name));
  }
  $('results-count').textContent=`${records.length.toLocaleString('en-CA')} in view`;
  if(!records.length){list.append(els('p','empty','No matching places in the current map view. Widen the date or outcome filters, or choose "Show all Scarborough".'));finishListRedraw(list,previousFocus);return;}
  for(const entry of pageRecords(records,listLimit,selectedId)) {
    const card=els('div','record-card');
    card.dataset.id=entry.id;
    const button=els('button','record-item'+(entry.id===selectedId?' active':''));
    button.type='button';button.dataset.id=entry.id;button.setAttribute('aria-expanded',String(entry.id===selectedId));
    const head=els('div','record-top');head.append(els('span','record-title',entry.name));
    head.append(els('span','status-label '+outcomeClass(entry.status),entry.status));
    button.append(head,els('div','record-address',entry.address||'Address unavailable'));
    const meta=els('div','record-meta');
    meta.append(els('span','',localDate(entry.inspection_date)));
    if(entry.neighbourhood)meta.append(els('span','',entry.neighbourhood));
    if(entry.event){
      const title={first_seen:'New to feed',new_inspection:'New inspection recorded',status_changed:`Changed from ${entry.event.previous_status||'unknown'}`} [entry.event.kind] || 'Updated';
      meta.append(els('span','',title));
    }
    button.append(meta);
    button.addEventListener('click',()=>selectPlace(entry.id,true));
    card.append(button);
    if(entry.id===selectedId){
      const detailId='selected-record-details';
      button.setAttribute('aria-controls',detailId);
      const detail=els('div','record-details');
      detail.id=detailId;
      detail.append(els('p','record-detail-note',entry.type&&entry.type!=='None'?`Recorded inspection detail: ${entry.type}`:'No additional detail in this source row.'));
      const source=els('a','record-source-link','Open the City DineSafe record');
      source.dataset.id=entry.id;source.href=cityDineSafeRecordUrl(entry.id);source.target='_blank';source.rel='noopener noreferrer';
      detail.append(source);card.append(detail);
    }
    list.append(card);
  }
  if(records.length>listLimit){
    const remaining=records.length-listLimit;
    const more=els('button','more-results',`Show next ${Math.min(80,remaining).toLocaleString('en-CA')} matches`);
    more.type='button';more.addEventListener('click',()=>{listLimit=Math.min(listLimit+80,records.length);renderList({focusMore:true});});
    list.append(more);
  }
  finishListRedraw(list,previousFocus);
  if(revealSelection)revealSelectedRecord(list,selectedId);
}
function selectPlace(id, move, revealSelection = false) {
  if(id==='beach:10'){state.mode='beach';save();syncControls();performFilters();return;}
  const item=snapshot?.establishments.find(e=>e.id===id);
  if(!item)return;
  selectedId=id;
  if(move&&map)map.easeTo({center:[item.longitude,item.latitude],zoom:Math.max(map.getZoom(),14),duration:450});
  updateSource();renderList({revealSelection});
}
function fitAll() {if(map)map.fitBounds(SCARB_BOUNDS,{padding:28,duration:350,maxZoom:11.2});}
function selectNeighbourhood(){
  if(!map||!state.neighbourhood)return;
  const matched=shapes.features.filter(f=>f.properties?.AREA_NAME===state.neighbourhood);
  const bounds=fitBoundsFromFeatures(matched);
  if(bounds)map.fitBounds([[bounds[0],bounds[1]],[bounds[2],bounds[3]]],{padding:35,maxZoom:13,duration:350});
}
function initMap() {
  if(typeof maplibregl==='undefined'){
    $('map-fallback').hidden=false;
    $('fit').hidden=true;
    return;
  }
  map=new maplibregl.Map({container:'map',style:'https://tiles.openfreemap.org/styles/liberty',center:[-79.255,43.775],zoom:10.45,
    maxBounds:[[-79.65,43.52],[-78.96,43.98]],attributionControl:true});
  map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-left');
  map.on('load',()=>{
    map.addSource('places',{type:'geojson',data:{type:'FeatureCollection',features:[]},cluster:true,clusterMaxZoom:13,clusterRadius:38});
    map.addLayer({id:'clusters',type:'circle',source:'places',filter:['has','point_count'],paint:{'circle-color':'#174d43','circle-radius':['step',['get','point_count'],18,30,23,150,29],'circle-opacity':.90,'circle-stroke-width':2,'circle-stroke-color':'#fff'}});
    map.addLayer({id:'cluster-count',type:'symbol',source:'places',filter:['has','point_count'],layout:{'text-field':['get','point_count_abbreviated'],'text-size':12},paint:{'text-color':'#fff'}});
    map.addLayer({id:'single',type:'circle',source:'places',filter:['!',['has','point_count']],paint:{'circle-color':['match',['get','status'],'Pass','#318f62','Conditional Pass','#e2a03d','Closed','#c4534c','Beach sample','#506c80','#667d71'],'circle-radius':['case',['get','selected'],11,7],'circle-stroke-width':2,'circle-stroke-color':'#fff'}});
    map.on('click','clusters',e=>{const geom=e.features?.[0]?.geometry;if(geom?.type==='Point')map.easeTo({center:geom.coordinates,zoom:Math.min(map.getZoom()+2,15),duration:350});});
    map.on('click','single',e=>{const id=String(e.features?.[0]?.properties?.id||'');if(id)selectPlace(id,false,true);});
    for(const layer of ['clusters','single']){map.on('mouseenter',layer,()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave',layer,()=>map.getCanvas().style.cursor='');}
    map.on('moveend',()=>{listLimit=80;renderList();});
    updateSource();renderList();
  });
  map.on('error',e=>console.warn('Map rendering issue:',e?.error?.message||e));
}
function bindControls(){
  document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{const next=b.dataset.mode;state.mode=next;if(next==='all')state.days='all';else if(next==='recent'&&state.days==='all')state.days='30';save();syncControls();performFilters();if(next==='beach'&&map&&beachPreview)map.easeTo({center:beachPreview.coordinates,zoom:Math.max(map.getZoom(),13),duration:350});}));
  document.querySelectorAll('.chip').forEach(b=>b.addEventListener('click',()=>{state.status=b.dataset.status;save();syncControls();performFilters();}));
  $('window').addEventListener('change',e=>{state.days=e.target.value;save();performFilters();});
  $('neighbourhood').addEventListener('change',e=>{state.neighbourhood=e.target.value;save();selectNeighbourhood();performFilters();});
  $('search').addEventListener('input',e=>{state.search=e.target.value;performFilters();});
  $('reset').addEventListener('click',()=>{state={...DEFAULTS};selectedId=null;syncControls();fitAll();save();performFilters();});
  $('fit').addEventListener('click',fitAll);
  $('toggle-filters').addEventListener('click',()=>{
    const expanded=document.querySelector('.filters').classList.toggle('expanded');
    $('toggle-filters').setAttribute('aria-expanded',String(expanded));
    $('toggle-filters').textContent=expanded?'Hide filters':'Filters';
  });
}
async function loadBeachPreview() {
  try{
    const response=await fetch('data/beach-sample-preview.json',{cache:'no-cache'});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const candidate=validateBeachSamplePreview(await response.json());
    beachPreview=candidate;beachPreviewState='ready';
  }catch(error){
    beachPreview=null;beachPreviewState='error';
    console.warn('Beach sample preview unavailable:',error?.message||error);
  }
  syncDataStatus();
  if(state.mode==='beach')performFilters();
}
async function loadDineSafeSnapshot() {
  try{
    const response=await fetch('data/snapshot.json',{cache:'no-cache'});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const candidate=await response.json();
    if(candidate?.schema_version!==1)throw new Error('Unsupported schema');
    if(candidate.ready && (!Array.isArray(candidate.establishments)||!candidate.establishments.length))throw new Error('Empty published snapshot');
    // Only install a fully validated candidate. A rejected payload must never become visible
    // later when the user switches away from Beach mode.
    snapshot=candidate;
    dineSafeLoadState=candidate.ready?'ready':'not-ready';dineSafeLoadError='';
    if(!candidate.ready){setDineSafeStatus('Awaiting first validated City data import','warning');performFilters();return;}
    try{const r=await fetch('data/scarborough-neighbourhoods.geojson',{cache:'force-cache'});if(r.ok)shapes=await r.json();}catch{}
    populateNeighbourhoods();
    const stale=isStale(candidate.published_at);
    setDineSafeStatus(stale?`Data may be stale: last validated ${publishedAt(candidate.published_at)} · check update history`:
      `City data checked ${publishedAt(candidate.published_at)} · not live`,stale?'warning':'');
    performFilters();
  }catch(error){
    snapshot=null;dineSafeLoadState='error';dineSafeLoadError=error.message;
    setDineSafeStatus('City data unavailable - last verified publication retained where possible','error');
    performFilters();
  }
}
function boot() {
  bindControls();syncControls();initMap();
  // Each feed loads independently so an optional beach request never holds DineSafe hostage.
  void loadBeachPreview();
  void loadDineSafeSnapshot();
}
boot();
