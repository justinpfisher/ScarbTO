import {areaFor, areaMatches, councillorFor, NEIGHBOURHOODS, WARDS, validateAreaFeatures, BOUNDARY_SOURCES} from './area-selection.mjs';
import {fitBoundsFromFeatures} from './logic.mjs';

/** One geographic selection, with two optional mutually exclusive map outlines.
 * Area visibility is session-only and always begins off; selected-area filters
 * can persist, but are always accompanied by a visible Clear area chip.
 */
export function createAreaExplorer({getState, getSnapshot, getVisiblePlaces, onSelect, onClear}) {
  const el = id => document.getElementById(id);
  let map = null, overlay = 'off', token = 0, open = false, expanded = false;
  const cache = new Map();
  let displayed = null, choiceMode = null, panelStamp = '';
  let awaitingMapReady = false, fitAttempt = 0;
  const pendingGeometry = new Map();
  const LIVE_MODES = new Set(['recent', 'all']);
  const AREA_KINDS=['ward','neighbourhood'];
  const areaLayerIds=kind=>{
    const prefix=kind==='ward'?'area-region':'neighbourhood-region';
    return {source:`${prefix}s`,fill:`${prefix}-fill`,selectedFill:`${prefix}-selected-fill`,line:`${prefix}-line`,selectedLine:`${prefix}-selected-line`};
  };

  function selected() {
    const state = getState();
    return areaFor(state.areaKind,state.areaCode);
  }
  function make(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value != null) node.textContent = String(value);
    return node;
  }
  function addText(parent, tag, className, value) {
    const child=make(tag,className,value);parent.append(child);return child;
  }
  function addLink(parent, label, url) {
    const a=make('a','area-source-link',label);
    a.href=url; a.target='_blank'; a.rel='noopener noreferrer';parent.append(a);
    return a;
  }
  function section(parent, title, body) {
    const region=make('section','area-section');
    addText(region,'h4','',title);
    addText(region,'p','',body);
    parent.append(region);
    return region;
  }
  function showNote(text) {
    const note=el('area-note');
    note.hidden=!text;note.textContent=text||'';
  }
  function syncChoices() {
    const choice=el('area-choice');
    const group=el('area-choice-wrap');
    group.hidden=overlay==='off';
    if (choiceMode!==overlay) {
      choice.replaceChildren();
      const initial=make('option','','Choose an area');
      initial.value='';choice.append(initial);
      const dictionary=overlay==='ward'?WARDS:NEIGHBOURHOODS;
      if (overlay!=='off') {
        for (const [code,area] of Object.entries(dictionary).sort((a,b)=>a[1].name.localeCompare(b[1].name,'en-CA'))) {
          const label=overlay==='ward'?'Ward '+code+' — '+area.name:area.name;
          const option=make('option','',label);option.value=code;choice.append(option);
        }
      }
      choiceMode=overlay;
    }
    const area=selected();
    choice.value=area?.kind===(overlay==='ward'?'ward':'neighbourhood')?area.code:'';
  }
  function syncButtons() {
    for (const button of document.querySelectorAll('[data-area-overlay]')) {
      const pressed=button.dataset.areaOverlay===overlay;
      button.setAttribute('aria-pressed',String(pressed));
      button.classList.toggle('selected',pressed);
      button.disabled=!LIVE_MODES.has(getState().mode) && button.dataset.areaOverlay!=='off';
    }
  }
  function renderPanel() {
    const area=selected();
    const chip=el('area-selection'), panel=el('area-panel');
    chip.hidden=!area;
    if (!area) {panel.hidden=true;open=false;return;}
    const areaLabel=(area.kind==='ward'?'Ward '+area.code+' — ':'')+area.name;
    el('area-selection-name').textContent=LIVE_MODES.has(getState().mode)
      ? areaLabel : 'DineSafe area (not applied): '+areaLabel;
    panel.hidden=!open;
    if (!open) return;
    const title=el('area-title');
    title.textContent=area.kind==='ward'?'Ward '+area.code+' · '+area.name:area.name;
    const sub=el('area-subtitle');
    if (area.kind==='ward') sub.textContent='City of Toronto municipal ward · 2018 ward boundaries';
    else sub.textContent='Toronto Social Planning Neighbourhood '+area.code+' · 2022 boundaries';
    el('area-panel-expand').setAttribute('aria-expanded',String(expanded));
    el('area-panel-fit').disabled=!map;
    panel.classList.toggle('expanded',expanded);
    const stamp=[area.kind,area.code,getState().mode,getVisiblePlaces().length,getSnapshot()?.published_at].join('|');
    if (stamp===panelStamp) return;
    panelStamp=stamp;
    const content=el('area-content');
    content.replaceChildren();
    const snapshot=getSnapshot();
    const places=snapshot?.ready?snapshot.establishments.filter(place=>areaMatches(place,{areaKind:area.kind,areaCode:area.code})):null;
    const isDineSafe=LIVE_MODES.has(getState().mode);
    const matching=isDineSafe
      ? getVisiblePlaces().filter(place=>areaMatches(place,{areaKind:area.kind,areaCode:area.code})).length : null;
    const dine=section(content,'Restaurants & DineSafe',places
      ? places.length.toLocaleString('en-CA')+' establishments in the latest validated snapshot; '+(isDineSafe
        ? matching.toLocaleString('en-CA')+' currently match your DineSafe filters.'
        : 'DineSafe geographic filtering is paused while this other source is displayed.')
      : 'A validated DineSafe snapshot is unavailable. No restaurant count is shown.');
    addText(dine,'p','area-disclaimer','Latest recorded inspections, not a complete real-time restaurant inventory.');
    if (snapshot?.published_at) {
      const stamp=new Date(snapshot.published_at);
      const published=Number.isFinite(stamp.valueOf())
        ? new Intl.DateTimeFormat('en-CA',{timeZone:'America/Toronto',dateStyle:'medium',timeStyle:'short'}).format(stamp)
        : 'unavailable';
      const catalogue=typeof snapshot.source?.last_refreshed==='string' ? snapshot.source.last_refreshed : 'not supplied';
      addText(dine,'p','area-disclaimer','Scarb.TO publication: '+published+'; City catalogue timestamp: '+catalogue+' (source time zone may be unspecified).');
      if (Number.isFinite(stamp.valueOf()) && Date.now()-stamp.valueOf()>48*60*60*1000)
        addText(dine,'p','area-disclaimer','The published snapshot may be stale; verify against the City source.');
    }
    if (!LIVE_MODES.has(getState().mode)) addText(dine,'p','area-disclaimer','This area filter applies to DineSafe views, not to police division totals or historical beach samples.');
    if (area.kind==='ward') {
      const rep=councillorFor(area.code);
      const r=section(content,'City councillor',rep.name+' · '+rep.role);
      if(rep.transition) addText(r,'p','area-disclaimer',rep.transition+' is councillor-elect; term begins November 15, 2026.');
      addLink(r,'Official City profile and office contacts',rep.url);
      addText(r,'p','area-disclaimer','Officeholder information checked October 31, 2026; confirm changes with the City.');
      content.prepend(r);
    } else {
      const names=area.wards.map(code=>'Ward '+code);
      const r=section(content,'Municipal representation',names.length>1
        ? 'This neighbourhood spans '+names.join(' and ')+'. Your councillor depends on your exact address.'
        : 'This neighbourhood lies predominantly in '+names.join(', ')+'. Confirm your exact address.');
      for (const code of area.wards) {
        const rep=councillorFor(code);
        addLink(r,'Ward '+code+': '+rep.name+' · City office',rep.url);
      }
      addText(r,'p','area-disclaimer','The listed wards represent meaningful source-measured overlaps, not whole-neighbourhood containment or population shares.');
      addText(r,'p','area-disclaimer','Scarborough membership is a source-verified majority-area selection of 30 whole City neighbourhoods, not a publisher-assigned district. The DineSafe site retains establishments included by the six municipal wards.');
    }
    const ridings=section(content,'Provincial & federal representatives',
      'Their electoral boundaries differ from City wards and neighbourhoods. An area name alone cannot determine your exact MPP or MP.');
    addLink(ridings,'Find your Ontario MPP','https://www.ola.org/en/members/current');
    addLink(ridings,'Find your federal riding','https://www.elections.ca/Scripts/vis/FindED?L=e&PAGEID=20&QID=-1');
    section(content,'Historical crime',area.kind==='ward'
      ? 'No ward crime total: whole-neighbourhood TPS quarterly summaries cannot be prorated into municipal wards.'
      : 'Quarterly TPS neighbourhood summaries are not yet approved for publication. No incident locations or current crime counts are displayed.');
    const development=section(content,'Development & permits',
      'Planning applications and issued permits are separate City records. Their public Scarb.TO feed is not yet qualified; no construction claims are shown.');
    addLink(development,'City planning application information','https://www.toronto.ca/city-government/planning-development/application-information-centre/');
    const boundary=section(content,'Boundary source','Official City of Toronto geography; attribution: Open Government Licence – Toronto.');
    addLink(boundary,'Official boundary dataset',BOUNDARY_SOURCES[area.kind]);
    addLink(boundary,'Confirm your City ward by address','https://www.toronto.ca/city-government/council/members-of-council/');
  }
  function syncOutline() {
    if (!map) return;
    const area=selected();
    for(const kind of AREA_KINDS){
      const ids=areaLayerIds(kind),code=area?.kind===kind?area.code:'__no_area_selected__';
      const filter=['==',['get','AREA_SHORT_CODE'],code];
      if(map.getLayer?.(ids.selectedFill))map.setFilter(ids.selectedFill,filter);
      if(map.getLayer?.(ids.selectedLine))map.setFilter(ids.selectedLine,filter);
    }
  }
  function sync() {
    syncButtons();
    syncChoices();
    renderPanel();
    syncOutline();
  }
  function hideMapOverlay() {
    if (!map) return;
    for(const kind of AREA_KINDS){
      const ids=areaLayerIds(kind);
      for(const id of [ids.fill,ids.selectedFill,ids.line,ids.selectedLine]){
        if(map.getLayer?.(id)&&map.getLayoutProperty?.(id,'visibility')!=='none')map.setLayoutProperty(id,'visibility','none');
      }
    }
  }
  function bindAreaLayerEvents(kind, fillId){
    map.on('click',fillId,event=>{
      if(overlay!==kind||!LIVE_MODES.has(getState().mode))return;
      if(map.queryRenderedFeatures?.(event.point,{layers:['single','clusters']})?.length)return;
      const code=String(event.features?.[0]?.properties?.AREA_SHORT_CODE||'');
      select(areaFor(kind,code));
    });
    map.on('mouseenter',fillId,()=>{if(overlay===kind)map.getCanvas().style.cursor='pointer';});
    map.on('mouseleave',fillId,()=>{map.getCanvas().style.cursor='';});
  }
  function ensureOverlayLayers(kind,current){
    const ids=areaLayerIds(kind);
    if(map.getSource(ids.source))return;
    map.addSource(ids.source,{type:'geojson',data:current});
    map.addLayer({id:ids.fill,type:'fill',source:ids.source,
      paint:{'fill-color':'#5a947d','fill-opacity':0.075}},'clusters');
    map.addLayer({id:ids.selectedFill,type:'fill',source:ids.source,filter:['==',['get','AREA_SHORT_CODE'],'__no_area_selected__'],
      paint:{'fill-color':'#26775d','fill-opacity':0.30}},'clusters');
    map.addLayer({id:ids.line,type:'line',source:ids.source,
      paint:{'line-color':'#246b59','line-width':1.35,'line-opacity':0.80}},'clusters');
    map.addLayer({id:ids.selectedLine,type:'line',source:ids.source,filter:['==',['get','AREA_SHORT_CODE'],'__no_area_selected__'],
      paint:{'line-color':'#26775d','line-width':3.4,'line-opacity':0.95}},'clusters');
    bindAreaLayerEvents(kind,ids.fill);
  }
  function display() {
    if (!map) return;
    const active=LIVE_MODES.has(getState().mode) && overlay!=='off' && cache.has(overlay);
    if (!active) {
      awaitingMapReady=false;
      hideMapOverlay();
      return;
    }
    if (!map.isStyleLoaded?.() && !map.loaded?.()) {
      // MapLibre.loaded() can be temporarily false after setData or a style
      // update. Don't lose the requested selection or expose stale geometry.
      awaitingMapReady=true;
      hideMapOverlay();
      return;
    }
    awaitingMapReady=false;
    ensureOverlayLayers(overlay,cache.get(overlay));
    displayed=overlay;
    for(const kind of AREA_KINDS){
      const ids=areaLayerIds(kind),visibility=kind===overlay?'visible':'none';
      for(const id of [ids.fill,ids.selectedFill,ids.line,ids.selectedLine]){
        if(map.getLayer(id)&&map.getLayoutProperty?.(id,'visibility')!==visibility)map.setLayoutProperty(id,'visibility',visibility);
      }
    }
    syncOutline();
  }
  async function loadGeometry(kind) {
    if (cache.has(kind)) return cache.get(kind);
    if (pendingGeometry.has(kind)) return pendingGeometry.get(kind);
    const path=kind==='ward'?'scarborough-wards.geojson':'scarborough-overlay-neighbourhoods.geojson';
    const promise=(async()=>{
      const response=await fetch('data/'+path,{cache:'force-cache'});
      if(!response.ok) throw new Error('HTTP '+response.status);
      const data=validateAreaFeatures(kind,await response.json());
      cache.set(kind,data);
      return data;
    })();
    pendingGeometry.set(kind,promise);
    try { return await promise; }
    finally { pendingGeometry.delete(kind); }
  }
  async function setOverlay(next) {
    if (!['off','neighbourhood','ward'].includes(next)) return;
    if (next!=='off' && !LIVE_MODES.has(getState().mode)) {
      showNote('Boundary overlays and area filters apply only to DineSafe; division totals and beach samples use different geographies.');
      return;
    }
    const priorSelection=selected();
    const selectionCleared=next!=='off' && priorSelection && priorSelection.kind!==next;
    if(selectionCleared){open=false;expanded=false;onClear();}
    const generation=++token;
    overlay=next;showNote(selectionCleared?'The area filter was cleared because it belongs to a different boundary type. Choose a new area to filter the map and list.':'');sync();
    if (next!=='off' && !cache.has(next)) {
      try {
        await loadGeometry(next);
      } catch (error) {
        if (generation!==token) return;
        overlay='off';
        showNote(selectionCleared
          ? 'Official '+(next==='ward'?'ward':'neighbourhood')+' boundaries are unavailable. The incompatible area filter was cleared; choose another area when the boundary is available.'
          : 'Official '+(next==='ward'?'ward':'neighbourhood')+' boundaries are unavailable. Existing map and filters are unchanged.');
        console.warn('Area overlay unavailable:',error?.message||error);
        sync();display();return;
      }
    }
    if (generation!==token) return;
    display();sync();
  }
  function select(area) {
    if (!area || !areaFor(area.kind,area.code)) return;
    open=true;expanded=false;
    onSelect(area);
    sync();
    el('area-title').focus();
  }
  function attachMap(nextMap) {
    map=nextMap;
    // A requested overlay must be retried when the map finishes loading. The
    // flag makes these callbacks inert once the correct layer is installed.
    for(const event of ['styledata','idle']) {
      map.on(event,()=>{if(awaitingMapReady) display();});
    }
    display();
    sync();
  }
  function detachMap() {
    map=null;awaitingMapReady=false;displayed=null;
    sync();
  }
  async function fitArea() {
    const area=selected(), attempt=++fitAttempt;
    if (!map || !area) return;
    try {
      // An area selected through the legacy dropdown or restored from browser
      // preferences need not have its overlay enabled or loaded.
      const collection=await loadGeometry(area.kind);
      const current=selected();
      if(attempt!==fitAttempt || !map || !current || current.kind!==area.kind || current.code!==area.code) return;
      const matching=collection.features.filter(f=>f.properties.AREA_SHORT_CODE===area.code);
      const bounds=fitBoundsFromFeatures(matching);
      if(bounds) map.fitBounds([[bounds[0],bounds[1]],[bounds[2],bounds[3]]],{padding:42,maxZoom:13,duration:350});
      else showNote('The selected official area has no usable mapped boundary.');
    } catch(error) {
      if(attempt!==fitAttempt) return;
      showNote('The official boundary could not be loaded. Your area filter remains in place.');
      console.warn('Selected area boundary unavailable:',error?.message||error);
    }
  }
  function onPanelClose() {
    open=false;expanded=false;renderPanel();
    el('area-reopen').focus();
  }
  for (const button of document.querySelectorAll('[data-area-overlay]')) {
    button.addEventListener('click',()=>{void setOverlay(button.dataset.areaOverlay);});
  }
  el('area-choice').addEventListener('change',event=>{
    const area=areaFor(overlay,event.target.value);
    if(area) select(area);
  });
  el('area-clear').addEventListener('click',()=>{
    open=false;onClear();sync();
  });
  el('area-reopen').addEventListener('click',()=>{open=true;sync();});
  el('area-panel-close').addEventListener('click',onPanelClose);
  el('area-panel-expand').addEventListener('click',()=>{
    expanded=!expanded;sync();
  });
  el('area-panel-fit').addEventListener('click',fitArea);
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape' && open) onPanelClose();
  });
  sync();
  return {sync, attachMap, detachMap, updateMode:()=>{
    if (!LIVE_MODES.has(getState().mode) && overlay!=='off')
      showNote('Boundaries are hidden for this view. Police division totals and historical beach samples are not neighbourhood or ward figures.');
    else if (el('area-note').textContent.startsWith('Boundaries are hidden for this view')) showNote('');
    display();sync();
  }, setOverlay, select};
}
