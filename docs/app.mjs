import {COPY_QUALIFICATION} from './scarb-current-copy.mjs';
import {currentEventCopy} from './scarb-event-copy.mjs';
import {staticCopy} from './scarb-voice.mjs';
import {readerDate, readerDateTime} from './reader-date.mjs';
import {viewFromSearch,searchFromView} from './view-state.mjs';
import {renderInspectionFindings} from './inspection-findings.mjs';
import {areaFor, areaForName} from './area-selection.mjs';
import {createAreaExplorer} from './area-explorer.mjs';
import {DEFAULTS, STATUS, filterActivity, filterEstablishments, isStale, displayAddress, cityCatalogueRefreshText, cityDineSafeRecordUrl, pageRecords, fitBoundsFromFeatures, relatedSourceRecords} from './logic.mjs';
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
let dineSafeStatus={text:staticCopy('app-01'),className:''}, dineSafeLoadState='loading', dineSafeLoadError='', beachPreviewState='loading';
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
  const sourceDetail=(label,value)=>{if(provenance&&value)provenance.append(els('p','',staticCopy('app-dynamic-01',{ VALUE0:(label), VALUE1:(value) })));};
  status.classList.remove('error','warning');
  if(state.mode==='selected-calls'){
    if(selectedCallsViewState.status==='available')status.classList.add('warning');else if(selectedCallsViewState.reason!=='loading')status.classList.add('error');
    status.textContent=selectedCallsViewState.status==='available'
      ? staticCopy('app-dynamic-02',{ VALUE0:(readerDateTime(selectedCallsViewState.sourceEditedAt)), VALUE1:(readerDateTime(selectedCallsViewState.fetchedAt)) })
      : selectedCallsViewState.reason==='loading'?staticCopy('app-02')
      : selectedCallsMessage(selectedCallsViewState);
    sourceDetail(staticCopy('app-audit-source'), staticCopy('app-03'));
    sourceDetail(staticCopy('app-04'),selectedCallsViewState.sourceEditedAt);
    sourceDetail(staticCopy('app-05'),selectedCallsViewState.fetchedAt);
    return;
  }
  if(state.mode==='beach'){
    if(beachPreviewState==='loading')status.textContent=staticCopy('app-06');
    else if(beachPreview){
      const latest=beachPreview.records.reduce((value,row)=>row.collectionDate>value?row.collectionDate:value,'0000-00-00');
      status.textContent=staticCopy('app-dynamic-03',{ VALUE0:(readerDate(latest)) });
      sourceDetail(staticCopy('app-07'),beachPreview.retrieved_on);
      sourceDetail(staticCopy('app-08'),latest);
      status.classList.add('warning');
    }else{
      status.textContent=staticCopy('app-09');
      status.classList.add('error');
    }
    return;
  }
  if(dineSafeStatus.className)status.classList.add(dineSafeStatus.className);
  status.textContent=dineSafeStatus.text;
  sourceDetail(staticCopy('app-audit-source'),staticCopy('app-10'));
  sourceDetail(staticCopy('app-11'),snapshot?.published_at);
  sourceDetail(staticCopy('app-12'),snapshot?.source?.last_refreshed);
  sourceDetail(staticCopy('app-audit-meaning'),staticCopy('app-13'));
}
function setDineSafeStatus(text,className='') {
  dineSafeStatus={text,className};
  syncDataStatus();
}
function syncMapAccessibilityLabel(){
  const beachMode=state.mode==='beach',selectedCallsMode=state.mode==='selected-calls';
  const mapLabel=selectedCallsMode
    ?staticCopy('app-14')
    :beachMode
      ?staticCopy('app-15')
      :statusMarkerImagesAvailable
        ?staticCopy('app-16')
        :staticCopy('app-17');
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
  if($('food-filters'))$('food-filters').hidden=beachMode||selectedCallsMode;
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
  button.setAttribute('aria-label',mapLegendCollapsed?staticCopy('app-audit-show-key'):staticCopy('app-audit-hide-key'));
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
    $('results-kicker').textContent=staticCopy('app-18');
    $('results-title').textContent=staticCopy('app-19');
    $('results-caption').textContent=staticCopy('app-20');
    updateSource();renderList();areaExplorer?.sync();return;
  }
  if(state.mode==='beach'){
    usingBeach=true;visiblePlaces=[];visibleActivity=[];usingActivity=false;
    $('results-kicker').textContent=staticCopy('app-21');
    $('results-title').textContent=beachPreview?.beach_name||staticCopy('app-audit-beach-label');
    $('results-caption').textContent=staticCopy('app-22');
    updateSource();renderList();
    return;
  }
  usingBeach=false;
  if(!snapshot?.ready){
    visiblePlaces=[];visibleActivity=[];usingActivity=false;
    $('results-kicker').textContent=staticCopy('app-23');
    $('results-title').textContent=staticCopy('app-24');
    $('results-caption').textContent=staticCopy('app-25');
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
  $('results-kicker').textContent=state.mode==='recent'?(usingActivity?staticCopy('app-26'):staticCopy('app-27')):staticCopy('app-28');
  $('results-title').textContent=state.mode==='recent'?(usingActivity?staticCopy('app-audit-recent'):staticCopy('app-29')):staticCopy('app-24');
  $('results-caption').textContent=usingActivity?staticCopy('app-30'):
    state.mode==='recent'?staticCopy('app-31'):
    staticCopy('app-32');
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
      $('results-count').textContent=staticCopy('app-dynamic-04',{ VALUE0:(view.counts.reduce((sum,row)=>sum+row.count,0).toLocaleString('en-CA')) });
      for(const row of view.counts){const item=els('div','selected-call-row');item.append(els('span','',staticCopy('app-dynamic-05',{ VALUE0:(row.division.slice(1)) })),els('strong','',row.count.toLocaleString('en-CA')));list.append(item);}
      list.append(els('p','selected-calls-attribution',staticCopy('app-33')));
    }else{
      $('results-count').textContent=view.reason==='loading'?staticCopy('app-audit-loading'):staticCopy('app-audit-unavailable');
      const message=selectedCallsMessage(view);
      list.append(els('p','empty',message));list.append(els('p','selected-calls-attribution',staticCopy('app-33')));
    }
    const source=els('a','record-source-link',staticCopy('app-34'));source.href='https://experience.arcgis.com/experience/a22f5295933e48a5b0a4c90cd3c4cae1';source.target='_blank';source.rel='noopener noreferrer';list.append(source);
    finishListRedraw(list,previousFocus);return;
  }
  if(usingBeach){
    $('results-count').textContent=beachPreview?staticCopy('app-dynamic-06',{ VALUE0:(beachPreview.rows_included) }):beachPreviewState==='loading'?staticCopy('app-audit-loading'):staticCopy('app-audit-unavailable');
    if(!beachPreview){
      const message=beachPreviewState==='loading'?staticCopy('app-35'):staticCopy('app-36');
      list.append(els('p','empty',message));
      const source=els('a','record-source-link',staticCopy('app-37'));source.href='https://open.toronto.ca/dataset/toronto-beaches-water-quality/';source.target='_blank';source.rel='noopener noreferrer';list.append(source);
      finishListRedraw(list,previousFocus);return;
    }
    list.append(renderBeachSamplePreview(document,beachPreview));
    finishListRedraw(list,previousFocus);return;
  }
  if(!snapshot?.ready){const message=dineSafeLoadState==='error'?staticCopy('app-dynamic-07',{ VALUE0:(dineSafeLoadError) }):dineSafeLoadState==='loading'?staticCopy('app-38'):staticCopy('app-39');list.append(els('p','empty',message));$('results-count').textContent=dineSafeLoadState==='error'?staticCopy('app-audit-unavailable'):staticCopy('app-audit-zero');finishListRedraw(list,previousFocus);return;}
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
  $('results-count').textContent=staticCopy('app-dynamic-08',{ VALUE0:(records.length.toLocaleString('en-CA')) });
  if(!records.length){
    list.append(els('p','empty',staticCopy('app-40')));
    const actions=els('div','empty-actions');
    const reset=els('button','empty-action',staticCopy('app-audit-clear'));reset.type='button';reset.addEventListener('click',()=>$('reset').click());actions.append(reset);
    if(map){const fit=els('button','empty-action',staticCopy('app-audit-fit'));fit.type='button';fit.addEventListener('click',fitAll);actions.append(fit);}
    list.append(actions);finishListRedraw(list,previousFocus);return;
  }
  for(const entry of pageRecords(records,listLimit,selectedId)) {
    const card=els('div','record-card');
    card.dataset.id=entry.id;
    const button=els('button','record-item'+(entry.id===selectedId?' active':''));
    button.type='button';button.dataset.id=entry.id;button.setAttribute('aria-expanded',String(entry.id===selectedId));
    const head=els('div','record-top');head.append(els('span','record-title',entry.name));
    head.append(els('span','status-label '+outcomeClass(entry.status),entry.status));
    button.append(head,els('div','record-address',displayAddress(entry.address)||staticCopy('app-41')));
    const meta=els('div','record-meta');
    meta.append(els('span','inspection-date',staticCopy('app-audit-inspection-prefix')+localDate(entry.inspection_date)));
    if(entry.neighbourhood)meta.append(els('span','',entry.neighbourhood));
    if(entry.event){
      const title={first_seen:staticCopy('app-26'),new_inspection:staticCopy('app-42'),status_changed:staticCopy('app-dynamic-09',{ VALUE0:(entry.event.previous_status||staticCopy('app-audit-unknown')) })} [entry.event.kind] || staticCopy('app-audit-updated');
      meta.append(els('span','',title));
      meta.append(els('span','observed-date',staticCopy('app-43')+publishedAt(entry.event.detected_at)));
      const explanation=currentEventCopy(entry.event);
      if(explanation)meta.append(els('span','event-explanation',explanation));
      else if(COPY_QUALIFICATION==='accepted-input')meta.append(els('span','event-explanation',staticCopy('event-prose-unavailable')));
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
      const related=relatedSourceRecords(snapshot.establishments,entry);
      if(related.length){
        const identity=els('details','related-source-records');
        identity.append(els('summary','', staticCopy('app-44')));
        identity.append(els('p','', staticCopy('app-45')));
        identity.append(els('p','',staticCopy('app-dynamic-10',{ VALUE0:(entry.id) })));
        for(const other of related){
          const link=els('a','record-source-link',staticCopy('app-dynamic-11',{ VALUE0:(other.name), VALUE1:(other.status), VALUE2:(localDate(other.inspection_date)), VALUE3:(other.id) }));
          link.href=cityDineSafeRecordUrl(other.id);link.target='_blank';link.rel='noopener noreferrer';identity.append(link);
        }
        detail.append(identity);
      }
      const source=els('a','record-source-link',staticCopy('app-46'));
      source.dataset.id=entry.id;source.href=cityDineSafeRecordUrl(entry.id);source.target='_blank';source.rel='noopener noreferrer';
      detail.append(source);card.append(detail);
    }
    list.append(card);
  }
  if(records.length>listLimit){
    const remaining=records.length-listLimit;
    const more=els('button','more-results',staticCopy('app-dynamic-12',{ VALUE0:(Math.min(80,remaining).toLocaleString('en-CA')) }));
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
  fallback.textContent=staticCopy('app-47');
  $('map').setAttribute('aria-hidden','true');
  $('fit').hidden=true;
  $('fit').disabled=true;
  const legend=$('map-legend');
  if(legend)legend.hidden=true;
  const hint=document.querySelector('.mobile-hint');
  if(hint)hint.textContent=staticCopy('app-48');
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
        map.on('moveend',()=>{if(state.mode==='recent'||state.mode==='all'){listLimit=80;renderList();}});
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
    $('toggle-filters').textContent=expanded?staticCopy('app-audit-hide-filters'):staticCopy('app-audit-filters');
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
    if(!candidate.ready){setDineSafeStatus(staticCopy('app-49'),'warning');performFilters();return;}
    populateNeighbourhoods();
    const stale=isStale(candidate.published_at);
    setDineSafeStatus(stale
      ? staticCopy('app-dynamic-13',{ VALUE0:(publishedAt(candidate.published_at)) })
      : staticCopy('app-dynamic-14',{ VALUE0:(publishedAt(candidate.published_at)) }),
      stale?'warning':'');
    performFilters();
  }catch(error){
    snapshot=null;dineSafeLoadState='error';dineSafeLoadError=error.message;
    setDineSafeStatus(staticCopy('app-50'),'error');
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
