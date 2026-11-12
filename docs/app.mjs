import {readerDate, readerDateTime} from './reader-date.mjs';
import {viewFromSearch,searchFromView} from './view-state.mjs';
import {renderInspectionFindings} from './inspection-findings.mjs';
import {areaFor, areaForName} from './area-selection.mjs';
import {createAreaExplorer} from './area-explorer.mjs';
import {DEFAULTS, STATUS, filterActivity, filterEstablishments, isStale, displayAddress, cityCatalogueRefreshText, cityDineSafeRecordUrl, pageRecords, fitBoundsFromFeatures} from './logic.mjs';
import {beginListRedraw, finishListRedraw, revealSelectedRecord} from './list-focus.mjs';
import {beachPreviewFeature, renderBeachSamplePreview, validateBeachSamplePreview} from './beach-history.mjs';
import {SelectedCallsClient, selectedCallsPolicy, selectedCallsMessage} from './selected-calls.mjs';
import {cameraBoundsForViewport, COUNCIL_BOUNDARY_BOUNDS, outsideMask, validateCouncilBoundary} from './boundary.mjs';

const $ = id => document.getElementById(id);
const SCARB_BOUNDS = [[-79.43,43.65],[-79.09,43.89]];
const STORAGE_KEY = 'scarbto-filters-v1';
let state = {...DEFAULTS};
let initialAreaOverlay = null;
try {
  const remembered = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  if (['recent','all','beach'].includes(remembered.mode)) state.mode = remembered.mode;
  if (['all', ...STATUS].includes(remembered.status)) state.status = remembered.status;
  if (['7','30','90','all'].includes(remembered.days)) state.days = remembered.days;
  if (typeof remembered.neighbourhood === 'string') state.neighbourhood = remembered.neighbourhood;
  if (areaFor(remembered.areaKind, remembered.areaCode)) {
    state.areaKind=remembered.areaKind;state.areaCode=String(remembered.areaCode);
  }
} catch { /* Private browsing, old preferences or disabled storage must not break the map. */ }
// Stable neighbourhood pages link into the same filtered map/list experience.
// Accept only a qualified area identity; query strings never override record data.
try {
  const params=new URLSearchParams(location.search);
  const requestedArea=areaFor(params.get('areaKind'),params.get('areaCode'));
  if(requestedArea){
    state.areaKind=requestedArea.kind;state.areaCode=requestedArea.code;state.neighbourhood='';
    state.status='all';
    initialAreaOverlay=requestedArea.kind;
    const requestedMode=params.get('mode');
    if(['recent','all'].includes(requestedMode))state.mode=requestedMode;
    const requestedDays=params.get('days');
    if(['7','30','90','all'].includes(requestedDays))state.days=requestedDays;
  }
} catch { /* An invalid shared link leaves the ordinary saved view intact. */ }
if(globalThis.location?.search){const view=viewFromSearch(location.search);state=view.state;initialAreaOverlay=view.overlay;}
else if(state.areaKind)initialAreaOverlay=state.areaKind;
let historyReady=false, restoringHistory=false, overlayTransition=false, navigationGeneration=0;
function rememberView({replace=false}={}) {
  if(!historyReady||restoringHistory||overlayTransition||!globalThis.history?.pushState)return;
  const search=searchFromView(state,areaExplorer?.getOverlay()||'off');
  if(search===location.search&&history.state?.scarbSearch===state.search)return;
  history[replace?'replaceState':'pushState']({scarbSearch:state.search},'',location.pathname+search+location.hash);
}
let snapshot = null, beachPreview = null, map = null, selectedId = null, shapes = {type:'FeatureCollection',features:[]};
let neighbourhoodShapesPromise = null;
let neighbourhoodFitRequestId = 0;
let features = [], visiblePlaces = [], visibleActivity = [], usingActivity = false, usingBeach = false, listLimit = 80;
let dineSafeStatus={text:'Loading the City records.',className:''}, dineSafeLoadState='loading', dineSafeLoadError='', beachPreviewState='loading';
const selectedCallsClient = new SelectedCallsClient();
let selectedCallsViewState = {status:'unavailable',reason:'not loaded',counts:[]};
let selectedCallsExpiryTimer=null, selectedCallsExpiryDeadlineMono=null, selectedCallsExpiryFetchedAt=null;
let mapUnavailable = false;
let councilBoundary = null;
let areaExplorer = null;
let mapLegendCollapsed=globalThis.matchMedia?.('(max-width: 570px)').matches||false;
let statusMarkerImagesAvailable=true;

function clearSelectedCallsExpiry(){
  clearTimeout(selectedCallsExpiryTimer);selectedCallsExpiryTimer=null;
  selectedCallsExpiryDeadlineMono=null;selectedCallsExpiryFetchedAt=null;
}
function scheduleSelectedCallsExpiry(view){
  if(view?.status!=='available'){clearSelectedCallsExpiry();return;}
  if(selectedCallsExpiryFetchedAt!==view.fetchedAt){
    selectedCallsExpiryFetchedAt=view.fetchedAt;
    const lifetime=Math.max(0,Math.min(selectedCallsPolicy.maxLocalAgeMs,selectedCallsPolicy.maxUpstreamAgeMs-view.sourceAgeMsAtFetch));
    selectedCallsExpiryDeadlineMono=performance.now()+lifetime;
  }
  clearTimeout(selectedCallsExpiryTimer);
  const remaining=Math.max(0,selectedCallsExpiryDeadlineMono-performance.now());
  selectedCallsExpiryTimer=setTimeout(()=>{
    if(state.mode!=='selected-calls'||document.visibilityState==='hidden')return;
    selectedCallsViewState=selectedCallsClient.state();syncControls();updateSource();renderList();
  },remaining+1);
}
function deactivateSelectedCalls(){
  clearSelectedCallsExpiry();
  selectedCallsClient.setVisible(false);
  selectedCallsViewState=selectedCallsClient.state();
}
function save() {
  try {const {status,days,neighbourhood,areaKind,areaCode}=state;const mode=state.mode==='selected-calls'?'recent':state.mode;localStorage.setItem(STORAGE_KEY,JSON.stringify({mode,status,days,neighbourhood,areaKind,areaCode}));}catch{}
}
function els(tag, cls, value) {
  const element = document.createElement(tag);
  if (cls) element.className = cls;
  if (value !== undefined && value !== null) element.textContent = String(value);
  return element;
}
function publishedAt(iso) { return readerDate(iso); }
function localDate(iso) { return readerDate(iso); }
function outcomeClass(status){return status==='Closed'?'closed':status==='Conditional Pass'?'conditional':'pass';}
function addStatusMarkerImages(mapInstance){
  const definitions=[
    ['pass','Pass','#318f62','circle','P'],
    ['conditional','Conditional Pass','#a96f12','triangle','C'],
    ['closed','Closed','#b3423c','square','X'],
    ['beach','Beach sample','#506c80','diamond','B'],
    ['other','other','#667d71','circle','?'],
  ];
  try{
    for(const [id,,color,shape,label] of definitions){
      const canvas=document.createElement('canvas');canvas.width=32;canvas.height=32;
      const context=canvas.getContext('2d');if(!context)return false;
      context.clearRect(0,0,32,32);context.fillStyle=color;context.strokeStyle='#fff';context.lineWidth=2;
      context.beginPath();
      if(shape==='circle')context.arc(16,16,12,0,Math.PI*2);
      else if(shape==='triangle'){context.moveTo(16,3);context.lineTo(30,28);context.lineTo(2,28);context.closePath();}
      else if(shape==='square')context.rect(4,4,24,24);
      else{context.moveTo(16,2);context.lineTo(30,16);context.lineTo(16,30);context.lineTo(2,16);context.closePath();}
      context.fill();context.stroke();context.fillStyle='#fff';context.font='bold 13px sans-serif';context.textAlign='center';context.textBaseline='middle';context.fillText(label,16,17);
      mapInstance.addImage(`status-${id}`,context.getImageData(0,0,32,32),{pixelRatio:2});
    }
    return true;
  }catch{return false;}
}
function syncDataStatus() {
  const status=$('data-status');
  const provenance=$('source-provenance-content');
  provenance?.replaceChildren();
  const sourceDetail=(label,value)=>{if(provenance&&value)provenance.append(els('p','',`${label}: ${value}`));};
  status.classList.remove('error','warning');
  if(state.mode==='selected-calls'){
    if(selectedCallsViewState.status==='available')status.classList.add('warning');else if(selectedCallsViewState.reason!=='loading')status.classList.add('error');
    status.textContent=selectedCallsViewState.status==='available'
      ? `TPS last changed these records ${readerDateTime(selectedCallsViewState.sourceEditedAt)}; checked ${readerDateTime(selectedCallsViewState.fetchedAt)}. Older counts are removed.`
      : selectedCallsViewState.reason==='loading'?'Loading selected TPS call counts for Divisions 41, 42 and 43.'
      : selectedCallsMessage(selectedCallsViewState);
    sourceDetail('Source', 'Toronto Police Service selected calls, Divisions 41, 42 and 43. These are not all calls, confirmed crimes or neighbourhood incidents.');
    sourceDetail('Source last changed',selectedCallsViewState.sourceEditedAt);
    sourceDetail('Successfully checked',selectedCallsViewState.fetchedAt);
    return;
  }
  if(state.mode==='beach'){
    if(beachPreviewState==='loading')status.textContent='Loading the historical beach samples.';
    else if(beachPreview){
      const latest=beachPreview.records.reduce((value,row)=>row.collectionDate>value?row.collectionDate:value,'0000-00-00');
      status.textContent=`Historical City samples through ${readerDate(latest)}. Not current swimming advice.`;
      sourceDetail('City sample records checked',beachPreview.retrieved_on);
      sourceDetail('Latest sample date',latest);
      status.classList.add('warning');
    }else{
      status.textContent='I could not load the historical beach samples. They are not current swimming advice.';
      status.classList.add('error');
    }
    return;
  }
  if(dineSafeStatus.className)status.classList.add(dineSafeStatus.className);
  status.textContent=dineSafeStatus.text;
  sourceDetail('Source','City of Toronto DineSafe Open Data');
  sourceDetail('Scarb.TO successful check',snapshot?.published_at);
  sourceDetail('City catalogue timestamp (source timezone unspecified)',snapshot?.source?.last_refreshed);
  sourceDetail('Meaning','The check time is not the inspection time or evidence of a new City update. Results describe the dated inspection, not current conditions.');
}
function setDineSafeStatus(text,className='') {
  dineSafeStatus={text,className};
  syncDataStatus();
}
function syncMapAccessibilityLabel(){
  const beachMode=state.mode==='beach',selectedCallsMode=state.mode==='selected-calls';
  const mapLabel=selectedCallsMode
    ?'Map background only; selected calls are not mapped individually'
    :beachMode
      ?'Map showing the beach reference point, not the individual sampling locations'
      :statusMarkerImagesAvailable
        ?'Interactive map of places with DineSafe records. Shapes and letters identify inspection outcomes alongside colour. Each outcome is written out in the matching list.'
        :'Interactive map of places with DineSafe records. Letters identify inspection outcomes alongside colour. Each outcome is written out in the matching list.';
  $('map').setAttribute('aria-label',mapLabel);
}
function syncControls() {
  $('window').value=state.days;
  $('neighbourhood').value=state.neighbourhood;
  $('search').value=state.search;
  document.querySelectorAll('.tab').forEach(b=>{let hit=b.dataset.mode===state.mode;b.classList.toggle('active',hit);b.setAttribute('aria-pressed',String(hit));});
  document.querySelectorAll('.chip').forEach(b=>{let hit=b.dataset.status===state.status;b.classList.toggle('selected',hit);b.setAttribute('aria-pressed',String(hit));});
  const beachMode=state.mode==='beach';
  const selectedCallsMode=state.mode==='selected-calls';
  $('beach-filter-note').hidden=!beachMode;
  $('selected-calls-filter-note').hidden=!selectedCallsMode;
  $('selected-calls-map-note').hidden=!selectedCallsMode;
  $('map-legend').hidden=mapUnavailable;
  document.querySelectorAll('[data-legend-mode]').forEach(item=>{
    item.hidden=item.dataset.legendMode==='dinesafe'?(beachMode||selectedCallsMode):item.dataset.legendMode==='beach'?(!beachMode||selectedCallsMode):false;
  });
  syncMapLegend();
  syncMapAccessibilityLabel();
  document.querySelectorAll('#search,#neighbourhood,#window,.outcomes button').forEach(control=>{control.disabled=beachMode||selectedCallsMode;});
  syncDataStatus();
  areaExplorer?.updateMode();
}
function syncMapLegend(){
  const button=$('map-legend-toggle'),items=$('map-legend-items');
  if(!button||!items)return;
  items.hidden=mapLegendCollapsed;
  $('map-legend').classList.toggle('collapsed',mapLegendCollapsed);
  $('map-legend').classList.toggle('marker-shape-fallback',!statusMarkerImagesAvailable);
  button.setAttribute('aria-expanded',String(!mapLegendCollapsed));
  button.setAttribute('aria-label',mapLegendCollapsed?'Show map key':'Hide map key');
  const icon=button.querySelector('span');if(icon)icon.textContent=mapLegendCollapsed?'+':'−';
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
  features=state.mode==='selected-calls'?[]:usingBeach && beachPreview ? [beachPreviewFeature(beachPreview)] : visiblePlaces.map(e=>geoFeature(e));
  map.getSource('places').setData({type:'FeatureCollection',features});
}
function performFilters() {
  rememberView();
  listLimit=80;
  if(state.mode==='selected-calls'){
    usingBeach=false;visiblePlaces=[];visibleActivity=[];usingActivity=false;
    $('results-kicker').textContent='Toronto Police Service · counts when you open this view';
    $('results-title').textContent='Police calls by division';
    $('results-caption').textContent='These are selected calls published by TPS, not all crime, police activity, or officer presence. Opening this view asks TPS/Esri for division totals only. I do not request or map individual calls or locations.';
    updateSource();renderList();areaExplorer?.sync();return;
  }
  if(state.mode==='beach'){
    usingBeach=true;visiblePlaces=[];visibleActivity=[];usingActivity=false;
    $('results-kicker').textContent='Toronto Open Data · dated samples';
    $('results-title').textContent=beachPreview?.beach_name||'Beach samples';
    $('results-caption').textContent='These water samples open another trail through the records. Here are a few records from the City catalogue to explore by date. They are historical measurements, not current swimming advice.';
    updateSource();renderList();
    return;
  }
  usingBeach=false;
  if(!snapshot?.ready){
    visiblePlaces=[];visibleActivity=[];usingActivity=false;
    $('results-kicker').textContent='Official inspections';
    $('results-title').textContent='Places to explore';
    $('results-caption').textContent='Explore the map or browse the list. Your filters work in both.';
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
  $('results-kicker').textContent=state.mode==='recent'?(usingActivity?'Added to Scarb.TO':'Latest City inspection records'):'Places with DineSafe records';
  $('results-title').textContent=state.mode==='recent'?(usingActivity?'Recent changes':'Recently inspected'):'Places to explore';
  $('results-caption').textContent=usingActivity?'This is where the records get interesting: compare them from day to day and the changes come into view. Here’s what I found in DineSafe. The inspection date may be earlier than when a record first appeared here.':
    state.mode==='recent'?'Here’s another way into the records: places with recent inspection dates. That doesn’t mean their records are new; check the City’s record for current details.':
    'Pick a place and explore its latest DineSafe inspection record with me. Each one links back to the City source.';
  updateSource();renderList();areaExplorer?.sync();
}
function renderList({focusMore = false, revealSelection = false} = {}) {
  const list=$('record-list');
  const previousFocus=beginListRedraw(list,document.activeElement,{focusMore});
  if(state.mode==='selected-calls'){
    let view=selectedCallsViewState;
    if(view.status==='available'||document.visibilityState==='hidden')view=selectedCallsClient.state();
    selectedCallsViewState=view;syncDataStatus();
    if(view.status==='available'){
      list.append(els('p','selected-calls-label',view.label));
      $('results-count').textContent=`${view.counts.reduce((sum,row)=>sum+row.count,0).toLocaleString('en-CA')} selected calls`;
      for(const row of view.counts){const item=els('div','selected-call-row');item.append(els('span','',`Division ${row.division.slice(1)}`),els('strong','',row.count.toLocaleString('en-CA')));list.append(item);}
      list.append(els('p','selected-calls-attribution','Contains information licensed under the Open Government Licence – Ontario.'));
    }else{
      $('results-count').textContent=view.reason==='loading'?'Loading':'Unavailable';
      const message=selectedCallsMessage(view);
      list.append(els('p','empty',message));list.append(els('p','selected-calls-attribution','Contains information licensed under the Open Government Licence – Ontario.'));
    }
    const source=els('a','record-source-link','See the TPS selected-calls map');source.href='https://experience.arcgis.com/experience/a22f5295933e48a5b0a4c90cd3c4cae1';source.target='_blank';source.rel='noopener noreferrer';list.append(source);
    finishListRedraw(list,previousFocus);return;
  }
  if(usingBeach){
    $('results-count').textContent=beachPreview?`${beachPreview.rows_included} sample records`:beachPreviewState==='loading'?'Loading':'Unavailable';
    if(!beachPreview){
      const message=beachPreviewState==='loading'?'Loading the historical City beach samples.':'I could not load the historical City beach samples.';
      list.append(els('p','empty',message));
      const source=els('a','record-source-link','See the City beach records');source.href='https://open.toronto.ca/dataset/toronto-beaches-water-quality/';source.target='_blank';source.rel='noopener noreferrer';list.append(source);
      finishListRedraw(list,previousFocus);return;
    }
    list.append(renderBeachSamplePreview(document,beachPreview));
    finishListRedraw(list,previousFocus);return;
  }
  if(!snapshot?.ready){const message=dineSafeLoadState==='error'?`I could not load the published records (${dineSafeLoadError}). The update history below may have more detail.`:dineSafeLoadState==='loading'?'Loading the City records checked for Scarb.TO.':'There are no checked DineSafe records here yet. Places will appear once the first set is ready.';list.append(els('p','empty',message));$('results-count').textContent=dineSafeLoadState==='error'?'Unavailable':'0 in view';finishListRedraw(list,previousFocus);return;}
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
  if(!records.length){
    list.append(els('p','empty','No places match this view. There is more to explore: try fewer filters or show all of Scarborough. Missing results do not mean nothing has happened here.'));
    const actions=els('div','empty-actions');
    const reset=els('button','empty-action','Clear filters');reset.type='button';reset.addEventListener('click',()=>$('reset').click());actions.append(reset);
    if(map){const fit=els('button','empty-action','Fit Scarborough');fit.type='button';fit.addEventListener('click',fitAll);actions.append(fit);}
    list.append(actions);finishListRedraw(list,previousFocus);return;
  }
  for(const entry of pageRecords(records,listLimit,selectedId)) {
    const card=els('div','record-card');
    card.dataset.id=entry.id;
    const button=els('button','record-item'+(entry.id===selectedId?' active':''));
    button.type='button';button.dataset.id=entry.id;button.setAttribute('aria-expanded',String(entry.id===selectedId));
    const head=els('div','record-top');head.append(els('span','record-title',entry.name));
    head.append(els('span','status-label '+outcomeClass(entry.status),entry.status));
    button.append(head,els('div','record-address',displayAddress(entry.address)||'Address unavailable'));
    const meta=els('div','record-meta');
    meta.append(els('span','inspection-date','Inspection: '+localDate(entry.inspection_date)));
    if(entry.neighbourhood)meta.append(els('span','',entry.neighbourhood));
    if(entry.event){
      const title={first_seen:'Added to Scarb.TO',new_inspection:'New inspection recorded',status_changed:`Changed from ${entry.event.previous_status||'unknown'}`} [entry.event.kind] || 'Updated';
      meta.append(els('span','',title));
      meta.append(els('span','observed-date','Added to Scarb.TO: '+publishedAt(entry.event.detected_at)));
    }
    button.append(meta);
    button.addEventListener('click',()=>selectPlace(entry.id,true));
    card.append(button);
    if(entry.id===selectedId){
      const detailId='selected-record-details';
      button.setAttribute('aria-controls',detailId);
      const detail=els('div','record-details');
      detail.id=detailId;
      detail.append(renderInspectionFindings(document,entry));
      const source=els('a','record-source-link','See the City DineSafe record');
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
  if(move&&map){neighbourhoodFitRequestId++;map.easeTo({center:[item.longitude,item.latitude],zoom:Math.max(map.getZoom(),14),duration:450});}
  updateSource();renderList({revealSelection});
}
function currentBoundaryCamera() {
  if (!councilBoundary) return SCARB_BOUNDS;
  const box=$('map').getBoundingClientRect();
  return cameraBoundsForViewport(Math.max(320,box.width),Math.max(280,box.height));
}
function invalidateNeighbourhoodFit(){neighbourhoodFitRequestId++;}
function fitAll() {invalidateNeighbourhoodFit();if(map)map.fitBounds(councilBoundary?COUNCIL_BOUNDARY_BOUNDS:SCARB_BOUNDS,{padding:councilBoundary?24:28,duration:350,maxZoom:11.2});}
function loadNeighbourhoodFitShapes(){
  if(!neighbourhoodShapesPromise){
    neighbourhoodShapesPromise=fetch('data/scarborough-neighbourhoods.geojson',{cache:'force-cache'})
      .then(response=>{
        if(!response.ok)throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then(candidate=>{
        if(candidate?.type!=='FeatureCollection'||!Array.isArray(candidate.features))throw new Error('Invalid neighbourhood geometry');
        shapes=candidate;
        return shapes;
      })
      .catch(error=>{
        console.warn('Neighbourhood fit geometry unavailable:',error?.message||error);
        return shapes;
      });
  }
  return neighbourhoodShapesPromise;
}
async function selectNeighbourhood(){
  const requestId=++neighbourhoodFitRequestId;
  const selected=state.neighbourhood;
  if(!map||!selected)return;
  const fitShapes=await loadNeighbourhoodFitShapes();
  if(requestId!==neighbourhoodFitRequestId||!map||state.neighbourhood!==selected||!['recent','all'].includes(state.mode))return;
  const matched=fitShapes.features.filter(f=>f.properties?.AREA_NAME===selected);
  const bounds=fitBoundsFromFeatures(matched);
  if(bounds)map.fitBounds([[bounds[0],bounds[1]],[bounds[2],bounds[3]]],{padding:35,maxZoom:13,duration:350});
}
function setMapUnavailable(error) {
  if(mapUnavailable)return;
  mapUnavailable=true;
  const failedMap=map;
  map=null;
  areaExplorer?.detachMap();
  try{failedMap?.remove();}catch{}
  const panel=document.querySelector('.map-panel');
  panel?.classList.add('map-unavailable');
  const fallback=$('map-fallback');
  fallback.hidden=false;
  fallback.textContent='The map could not load, but you can keep exploring. Search, filter and open the source records in the list below.';
  $('map').setAttribute('aria-hidden','true');
  $('fit').hidden=true;
  $('fit').disabled=true;
  const legend=$('map-legend');
  if(legend)legend.hidden=true;
  const hint=document.querySelector('.mobile-hint');
  if(hint)hint.textContent='The map could not load, but your filters still work on the list.';
  if(error)console.warn('Interactive map unavailable:',error?.message||error);
  performFilters();
}
async function initMap() {
  if(typeof maplibregl==='undefined'){
    setMapUnavailable();
    return;
  }
  // MapLibre 6 requires WebGL2. Probe before constructing the map so a
  // browser without WebGL2 reaches the same accessible list fallback as a
  // constructor or context-loss failure.
  try{
    const probe=document.createElement('canvas');
    if(typeof probe.getContext==='function'){
      const context=probe.getContext('webgl2');
      if(!context){setMapUnavailable(new Error('WebGL2 is unavailable'));return;}
      context.getExtension('WEBGL_lose_context')?.loseContext();
    }
  }catch(error){setMapUnavailable(error);return;}
  try{
    try{
      const boundaryResponse=await fetch('data/scarborough-council-boundary.geojson',{cache:'force-cache'});
      if(!boundaryResponse.ok)throw new Error(`HTTP ${boundaryResponse.status}`);
      const candidate=await boundaryResponse.json();
      councilBoundary=validateCouncilBoundary(candidate);
    }catch(error){console.warn('Official Scarborough boundary overlay unavailable:',error?.message||error);}
    map=new maplibregl.Map({container:'map',style:'https://tiles.openfreemap.org/styles/liberty',center:[-79.255,43.775],zoom:10.45,
      maxBounds:currentBoundaryCamera(),attributionControl:true});
    map.on('movestart',invalidateNeighbourhoodFit);
    map.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-left');
    map.getCanvas().addEventListener('webglcontextlost',event=>{event.preventDefault();setMapUnavailable(new Error('WebGL context lost'));},{once:true});
    map.on('load',()=>{
      try{
        if(!map)return;
        if(councilBoundary){
          const mask=outsideMask(councilBoundary);
          map.addSource('scarborough-mask',{type:'geojson',data:mask});
          map.addLayer({id:'scarborough-outside-mask',type:'fill',source:'scarborough-mask',paint:{'fill-color':'#edf0eb','fill-opacity':0.48}});
          map.addSource('scarborough-boundary',{type:'geojson',data:{type:'FeatureCollection',features:[councilBoundary]}});
          map.addLayer({id:'scarborough-boundary-line',type:'line',source:'scarborough-boundary',paint:{'line-color':'#2d6657','line-width':['interpolate',['linear'],['zoom'],8,1.2,12,2.5],'line-opacity':0.9}});
          const applyCameraBounds=()=>map?.setMaxBounds(currentBoundaryCamera());
          map.on('resize',applyCameraBounds);
          map.fitBounds(COUNCIL_BOUNDARY_BOUNDS,{padding:24,duration:0,maxZoom:11.2});
        }
        map.addSource('places',{type:'geojson',data:{type:'FeatureCollection',features:[]},cluster:true,clusterMaxZoom:13,clusterRadius:38});
        map.addLayer({id:'clusters',type:'circle',source:'places',filter:['has','point_count'],paint:{'circle-color':'#174d43','circle-radius':['step',['get','point_count'],18,30,23,150,29],'circle-opacity':.90,'circle-stroke-width':2,'circle-stroke-color':'#fff'}});
        map.addLayer({id:'cluster-count',type:'symbol',source:'places',filter:['has','point_count'],layout:{'text-field':['get','point_count_abbreviated'],'text-size':12},paint:{'text-color':'#fff'}});
        statusMarkerImagesAvailable=addStatusMarkerImages(map);
        syncMapLegend();
        syncMapAccessibilityLabel();
        if(statusMarkerImagesAvailable){
          map.addLayer({id:'single',type:'symbol',source:'places',filter:['!',['has','point_count']],layout:{'icon-image':['match',['get','status'],'Pass','status-pass','Conditional Pass','status-conditional','Closed','status-closed','Beach sample','status-beach','status-other'],'icon-size':['case',['get','selected'],1.15,1],'icon-allow-overlap':true,'icon-ignore-placement':true}});
        }else{
          map.addLayer({id:'single',type:'circle',source:'places',filter:['!',['has','point_count']],paint:{'circle-color':['match',['get','status'],'Pass','#318f62','Conditional Pass','#e2a03d','Closed','#c4534c','Beach sample','#506c80','#667d71'],'circle-radius':['case',['get','selected'],11,7],'circle-stroke-width':2,'circle-stroke-color':'#fff'}});
          map.addLayer({id:'single-letter',type:'symbol',source:'places',filter:['!',['has','point_count']],layout:{'text-field':['match',['get','status'],'Pass','P','Conditional Pass','C','Closed','X','Beach sample','B','?'],'text-size':9,'text-allow-overlap':true,'text-ignore-placement':true},paint:{'text-color':'#fff','text-halo-color':'#344b42','text-halo-width':0.5}});
        }
        map.on('click','clusters',e=>{const geom=e.features?.[0]?.geometry;if(geom?.type==='Point'){invalidateNeighbourhoodFit();map.easeTo({center:geom.coordinates,zoom:Math.min(map.getZoom()+2,15),duration:350});}});
        map.on('click','single',e=>{const id=String(e.features?.[0]?.properties?.id||'');if(id)selectPlace(id,false,true);});
        for(const layer of ['clusters','single']){map.on('mouseenter',layer,()=>map.getCanvas().style.cursor='pointer');map.on('mouseleave',layer,()=>map.getCanvas().style.cursor='');}
        areaExplorer?.attachMap(map);
        map.on('moveend',()=>{listLimit=80;renderList();});
        updateSource();renderList();
        if(['recent','all'].includes(state.mode)&&state.neighbourhood)void selectNeighbourhood();
      }catch(error){setMapUnavailable(error);}
    });
    map.on('error',e=>{
      const error=e?.error||e;
      const message=String(error?.message||error);
      console.warn('Map rendering issue:',message);
      if(/webgl|context lost|failed to initialize/i.test(message))setMapUnavailable(error);
    });
  }catch(error){setMapUnavailable(error);}
}
function bindControls(){
  $('map-legend-toggle').addEventListener('click',()=>{mapLegendCollapsed=!mapLegendCollapsed;syncMapLegend();});
  document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{
    const next=b.dataset.mode;
    if(next!==state.mode)invalidateNeighbourhoodFit();
    if(state.mode==='selected-calls'&&next!=='selected-calls')deactivateSelectedCalls();
    state.mode=next;
    if(next==='all')state.days='all';else if(next==='recent'&&state.days==='all')state.days='30';
    if(next==='selected-calls')selectedCallsViewState={status:'unavailable',reason:'loading',counts:[]};else save();
    syncControls();performFilters();if(next==='selected-calls')void loadSelectedCalls();
    if(next==='beach'&&map&&beachPreview)map.easeTo({center:beachPreview.coordinates,zoom:Math.max(map.getZoom(),13),duration:350});
  }));
  document.querySelectorAll('.chip').forEach(b=>b.addEventListener('click',()=>{state.status=b.dataset.status;save();syncControls();performFilters();}));
  $('window').addEventListener('change',e=>{state.days=e.target.value;save();performFilters();});
  $('neighbourhood').addEventListener('change',e=>{
    // This is an independent place filter, not a selected map polygon.
    state.areaKind='';state.areaCode='';state.neighbourhood=e.target.value;
    save();selectNeighbourhood();performFilters();areaExplorer?.sync();
  });
  $('search').addEventListener('input',e=>{state.search=e.target.value;performFilters();});
  $('reset').addEventListener('click',()=>{if(state.mode==='selected-calls')deactivateSelectedCalls();state={...DEFAULTS};selectedId=null;syncControls();fitAll();save();performFilters();});
  $('fit').addEventListener('click',fitAll);
  $('toggle-filters').addEventListener('click',()=>{
    const expanded=document.querySelector('.filters').classList.toggle('expanded');
    $('toggle-filters').setAttribute('aria-expanded',String(expanded));
    $('toggle-filters').textContent=expanded?'Hide filters':'Filters';
  });
}
async function loadSelectedCalls(){
  const visible=state.mode==='selected-calls'&&document.visibilityState!=='hidden';
  selectedCallsClient.setVisible(visible);
  if(!visible){selectedCallsViewState=selectedCallsClient.state();syncControls();return;}
  selectedCallsViewState={status:'unavailable',reason:'loading',counts:[]};syncControls();performFilters();
  const result=await selectedCallsClient.load();
  if(state.mode!=='selected-calls')return;
  if(document.visibilityState==='hidden')deactivateSelectedCalls();
  else {
    selectedCallsViewState=result;scheduleSelectedCallsExpiry(result);
  }
  syncControls();updateSource();renderList();
}
document.addEventListener('visibilitychange',()=>{
  if(state.mode!=='selected-calls')return;
  if(document.visibilityState==='hidden'){
    deactivateSelectedCalls();syncControls();performFilters();
  }else void loadSelectedCalls();
});

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
    if(!candidate.ready){setDineSafeStatus('Waiting for the first checked City records','warning');performFilters();return;}
    populateNeighbourhoods();
    const stale=isStale(candidate.published_at);
    setDineSafeStatus(stale
      ? `These food inspection records may be out of date. Last checked ${publishedAt(candidate.published_at)}. Check the City's record for anything newer.`
      : `Food inspection records checked ${publishedAt(candidate.published_at)}. These aren't live results.`,
      stale?'warning':'');
    performFilters();
  }catch(error){
    snapshot=null;dineSafeLoadState='error';dineSafeLoadError=error.message;
    setDineSafeStatus('I could not load the City records. No DineSafe results are shown.','error');
    performFilters();
  }
}
function boot() {
  bindControls();
  areaExplorer=createAreaExplorer({
    getState:()=>state, getSnapshot:()=>snapshot, getVisiblePlaces:()=>visiblePlaces,
    onSelect:area=>{
      state.areaKind=area.kind;state.areaCode=area.code;
      selectedId=null;save();syncControls();performFilters();
    },
    onClear:({overlayChange=false}={})=>{
      overlayTransition=overlayChange;
      state.areaKind='';state.areaCode='';
      selectedId=null;save();syncControls();if(overlayChange)fitAll();performFilters();
    },
    onOverlayChange:()=>{overlayTransition=false;rememberView();}
  });
  syncControls();void initMap();
  const initialize=initialAreaOverlay?areaExplorer.setOverlay(initialAreaOverlay,{restore:true}):Promise.resolve();
  void initialize.finally(()=>{overlayTransition=false;historyReady=true;rememberView({replace:true});});
  globalThis.addEventListener?.('popstate',async event=>{
    const generation=++navigationGeneration;
    restoringHistory=true;
    try{
      if(state.mode==='selected-calls')deactivateSelectedCalls();
      const view=viewFromSearch(location.search);state=view.state;selectedId=null;
      state.search=typeof event.state?.scarbSearch==='string'?event.state.scarbSearch:'';
      const requestedState=JSON.stringify(state);
      await areaExplorer.setOverlay(view.overlay,{restore:true});
      if(generation!==navigationGeneration||JSON.stringify(state)!==requestedState)return;
      save();syncControls();performFilters();fitAll();
      if(state.mode==='selected-calls')void loadSelectedCalls();
    }finally{if(generation===navigationGeneration){restoringHistory=false;overlayTransition=false;rememberView({replace:true});}}
  });
  // Each feed loads independently so an optional beach request never holds DineSafe hostage.
  void loadBeachPreview();
  void loadDineSafeSnapshot();
}
boot();
