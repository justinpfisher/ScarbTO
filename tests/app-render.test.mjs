import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

class FakeElement {
  constructor(document, tagName = 'div', id = '', className = '') {
    this.ownerDocument = document;
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.className = className;
    this.dataset = {};
    this.children = [];
    this.parentElement = null;
    this.attributes = {};
    this.handlers = {};
    this.value = '';
    this.hidden = false;
    this.style = {};
    this.scrollCalls = [];
    this.classList = {
      contains: name => this.className.split(/\s+/).filter(Boolean).includes(name),
      add: name => { if (!this.classList.contains(name)) this.className = `${this.className} ${name}`.trim(); },
      remove: name => { this.className = this.className.split(/\s+/).filter(item => item && item !== name).join(' '); },
      toggle: (name, force) => {
        const add = force === undefined ? !this.classList.contains(name) : Boolean(force);
        if (add) this.classList.add(name); else this.classList.remove(name);
        return add;
      },
    };
  }
  set textContent(value) { this.replaceChildren(); this._text = String(value); }
  get textContent() { return (this._text || '') + this.children.map(child => child.textContent).join(''); }
  append(...nodes) {
    for (const node of nodes) {
      if (node.parentElement) node.parentElement.children = node.parentElement.children.filter(child => child !== node);
      node.parentElement = this;
      this.children.push(node);
    }
  }
  replaceChildren(...nodes) {
    for (const child of this.children) child.parentElement = null;
    this.children = [];
    this._text = '';
    this.append(...nodes);
  }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(type, callback) { (this.handlers[type] ||= []).push(callback); }
  click() {
    this.ownerDocument.activeElement = this;
    for (const callback of this.handlers.click || []) callback({target:this});
  }
  dispatch(type, event = {}) {
    for (const callback of this.handlers[type] || []) callback({target:this,...event});
  }
  focus(options) { this.ownerDocument.activeElement = this; this.focusOptions = options; }
  scrollIntoView(options) { this.scrollCalls.push(options); }
  contains(element) { return this === element || this.children.some(child => child.contains(element)); }
  querySelectorAll(selector) {
    const className = selector.startsWith('.') ? selector.slice(1) : null;
    return this.children.flatMap(child => [
      ...(className && child.classList.contains(className) ? [child] : []),
      ...child.querySelectorAll(selector),
    ]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

class FakeDocument {
  constructor() {
    this.elements = new Map();
    this.activeElement = null;
    this.visibilityState='visible';
    this.documentHandlers={};
    this.addEventListener=(type,callback)=>{(this.documentHandlers[type] ||= []).push(callback);};
    this.dispatch=(type)=>{for(const callback of this.documentHandlers[type]||[])callback();};
    this.tabs = ['recent','all','beach','selected-calls'].map(mode => {
      const button = new FakeElement(this,'button','','tab');
      button.dataset.mode = mode;
      return button;
    });
    this.chips = ['all','Pass','Conditional Pass','Closed'].map(status => {
      const button = new FakeElement(this,'button','','chip');
      button.dataset.status = status;
      return button;
    });
    this.filters = new FakeElement(this,'aside','','filters');
  }
  getElementById(id) {
    if (!this.elements.has(id)) this.elements.set(id,new FakeElement(this,'div',id,id === 'record-list' ? 'record-list' : ''));
    return this.elements.get(id);
  }
  createElement(tagName) {
    const element=new FakeElement(this,tagName);
    if(String(tagName).toLowerCase()==='canvas')element.getContext=type=>type==='2d'&&this.canvas2dEnabled!==false?{
      clearRect(){},beginPath(){},arc(){},moveTo(){},lineTo(){},closePath(){},rect(){},fill(){},stroke(){},fillText(){},
      getImageData:(_x,_y,width,height)=>({width,height,data:new Uint8ClampedArray(width*height*4)}),
    }:type==='webgl2'?{getExtension:()=>({loseContext(){}})}:null;
    return element;
  }
  querySelectorAll(selector) {
    if (selector === '.tab') return this.tabs;
    if (selector === '.chip') return this.chips;
    return [];
  }
  querySelector(selector) { return selector === '.filters' ? this.filters : null; }
}

class FakeMap {
  constructor(document) {
    this.document = document;
    this.handlers = Object.create(null);
    this.sources = Object.create(null);
    this.layers = Object.create(null);
    this.images = Object.create(null);
    this.isLoaded = false;
    this.fitBoundsCalls = [];
    this.easeToCalls = [];
    this.canvas = new FakeElement(document,'div','','map-canvas');
    this.canvas.style = {};
  }
  on(event, layerOrCallback, callback) {
    const key = typeof layerOrCallback === 'string' ? `${event}:${layerOrCallback}` : event;
    this.handlers[key] = typeof layerOrCallback === 'function' ? layerOrCallback : callback;
  }
  emit(event) { this.handlers[event]?.(); }
  emitLayer(event, layer, payload) {
    this.document.activeElement = this.canvas;
    this.handlers[`${event}:${layer}`]?.(payload);
  }
  addControl() {}
  addSource(id) { this.sources[id] = {setData(data) { this.data = data; }}; }
  addImage(id,image,options) { this.images[id]={image,options}; }
  addLayer(layer) { this.layers[layer.id]=layer; }
  getSource(id) { return this.sources[id]; }
  getBounds() { return {contains:() => true}; }
  loaded() { return this.isLoaded; }
  getZoom() { return 11; }
  getCanvas() { return this.canvas; }
  easeTo(...args) { this.easeToCalls.push(args); this.emit('movestart'); this.emit('moveend'); }
  fitBounds(...args) { this.fitBoundsCalls.push(args); this.emit('movestart'); this.emit('moveend'); }
  load() { this.isLoaded = true; this.emit('load'); }
}

function fixture(count = 1, ready = true) {
  return {
    schema_version:1,
    ready,
    published_at:'2026-10-27T00:00:00Z',
    establishments:Array.from({length:count},(_,index)=>({
      id:`entry-${String(index).padStart(3,'0')}`,
      name:`Place ${String(index).padStart(3,'0')}`,
      address:`${index} Synthetic Road`,
      type:'Synthetic inspection detail',
      status:'Pass',
      inspection_date:'2026-10-26',
      latitude:43.7 + index / 10000,
      longitude:-79.2 - index / 10000,
      neighbourhood:'Synthetic Area',
    })),
    activity:[],
  };
}

async function loadApp(snapshot,{selectedFetch,neighbourhoodFetch} = {}) {
  const document = new FakeDocument();
  let map;
  const prior = {
    document:globalThis.document,
    localStorage:globalThis.localStorage,
    fetch:globalThis.fetch,
    maplibregl:globalThis.maplibregl,
  };
  globalThis.document = document;
  globalThis.localStorage = {
    getItem:key => key === 'scarbto-filters-v1'
      ? JSON.stringify({mode:'all',status:'all',days:'all',neighbourhood:''})
      : null,
    setItem:() => {},
  };
  const ordinaryFetch=async url => url.includes('snapshot.json')
    ? {ok:true,json:async()=>snapshot}
    : String(url).includes('scarborough-neighbourhoods.geojson')&&neighbourhoodFetch
      ? neighbourhoodFetch(url)
      : {ok:false,status:404};
  globalThis.fetch=async (url,init)=>String(url).includes('C4S_Public_NoGO')&&selectedFetch
    ? selectedFetch(url,init)
    : ordinaryFetch(url,init);
  globalThis.maplibregl = {Map:class extends FakeMap {constructor(){super(document);map=this;}},NavigationControl:class{}};
  await import(`../docs/app.mjs?render-test=${Math.random()}`);
  await new Promise(resolve => setTimeout(resolve,0));
  return {
    document,
    map,
    async cleanup() {
      for (const [key,value] of Object.entries(prior)) {
        if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
      }
    },
  };
}

test('resident copy keeps the selected tagline and explains observed-date limits', async () => {
  const html=await readFile(new URL('../docs/index.html',import.meta.url),'utf8');
  assert.match(html,/Scarborough\. I looked into it\./);
  assert.match(html,/<p class="intro-tagline">Scarborough\. I looked into it\.<\/p>/);
  assert.match(html,/I’m an AI-assisted guide[\s\S]*I’m independent of the City of Toronto; I work from public sources, not visits or interviews/);
  assert.match(html,/A DineSafe result describes the inspection on the date shown, not conditions today/);
  assert.match(html,/Check the City’s record for anything newer/);
});

test('homepage uses the connected-contour lockup with a standalone mobile mark', async () => {
  const [html,css,lockup,mark] = await Promise.all([
    readFile(new URL('../docs/index.html',import.meta.url),'utf8'),
    readFile(new URL('../docs/styles.css',import.meta.url),'utf8'),
    readFile(new URL('../docs/assets/brand/scarbto-connected.svg',import.meta.url),'utf8'),
    readFile(new URL('../docs/assets/brand/scarbto-mark.svg',import.meta.url),'utf8'),
  ]);
  assert.match(html,/<source media="\(max-width: 420px\)" srcset="\.\/assets\/brand\/scarbto-mark\.svg">/);
  assert.match(html,/<img class="brand-lockup" src="\.\/assets\/brand\/scarbto-connected\.svg" alt="Scarb\.TO, with the three-line wave and cliff mark">/);
  assert.match(css,/\.brand-lockup\{display:block;width:min\(304px,45vw\);height:auto\}/);
  assert.match(css,/@media\(max-width:420px\)\{\.brand-lockup\{width:64px\}\}/);
  assert.match(lockup,/<title id="title">Scarb\.TO, with a three-line wave and cliff mark<\/title>/);
  assert.match(lockup,/<desc id="desc">Three rising lines[\s\S]*not an official City mark or a map of the coastline\.<\/desc>/);
  assert.match(mark,/<title id="mark-title">Lake &amp; Land three-line wave and cliff mark<\/title>/);
});

test('Scarb footer keeps source, licence, boundary, attribution, and freshness meanings', async () => {
  const html=await readFile(new URL('../docs/index.html',import.meta.url),'utf8');
  const footer=html.match(/<footer id="about">([\s\S]*?)<\/footer>/)?.[1];
  assert.ok(footer,'about footer remains present');
  assert.equal((footer.match(/<div>/g)||[]).length,4,'footer keeps its four readable content rows');
  for (const href of [
    'https://open.toronto.ca/dataset/dinesafe/',
    'https://open.toronto.ca/open-data-licence/',
    'data/establishments.csv',
    'https://github.com/justinpfisher/ScarbTO/actions',
    'https://open.toronto.ca/dataset/neighbourhoods/',
    'https://open.toronto.ca/dataset/city-wards/',
    'https://open.toronto.ca/dataset/community-council-boundaries/',
  ]) assert.ok(footer.includes(`href="${href}"`),`retains ${href}`);
  for (const text of [
    'City of Toronto DineSafe Open Data','Open Government Licence - Toronto',
    'effective April 2022','effective December 2018','cross ward lines',
    'not electoral address lookups','visual reference; it doesn\'t filter records',
    'OpenFreeMap and OpenStreetMap contributors in its attribution control','compare successfully collected DineSafe records',
    'An inspection may be older than the date its record first appears here',
  ]) assert.ok(footer.includes(text),`retains meaning: ${text}`);
});

test('recent DineSafe captions distinguish detected changes from inspection dates', async () => {
  const snapshot=fixture();
  const torontoDate=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/Toronto',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).map(part=>[part.type,part.value]));
  snapshot.activity=[{
    id:'event-001',kind:'new_inspection',feed:'dinesafe',establishment_id:'entry-000',
    name:'Place 000',address:'0 Synthetic Road',neighbourhood:'Synthetic Area',
    inspection_date:'2026-10-26',detected_at:`${torontoDate.year}-${torontoDate.month}-${torontoDate.day}T17:00:00Z`,status:'Pass',
    previous_status:'Pass',latitude:43.7,longitude:-79.2,
  }];
  const app=await loadApp(snapshot);
  try {
    assert.equal(app.document.getElementById('results-caption').textContent,
      'Pick a place and explore its latest DineSafe inspection record with me. Each one links back to the City source.');
    app.document.tabs.find(tab=>tab.dataset.mode==='recent').click();
    assert.equal(app.document.getElementById('results-caption').textContent,
      'This is where the records get interesting: compare them from day to day and the changes come into view. Here’s what I found in DineSafe. The inspection date may be earlier than when a record first appeared here.');
    assert.match(app.document.getElementById('record-list').textContent,/Inspection: Monday, October 26, 2026/);
    assert.match(app.document.getElementById('record-list').textContent,/Added to Scarb\.TO:/);
  } finally { await app.cleanup(); }
});

test('inspection-only recent view does not imply a newly published record', async () => {
  const snapshot=fixture();
  const app=await loadApp(snapshot);
  try {
    app.document.tabs.find(tab=>tab.dataset.mode==='recent').click();
    assert.equal(app.document.getElementById('results-caption').textContent,
      'Here’s another way into the records: places with recent inspection dates. That doesn’t mean their records are new; check the City’s record for current details.');
  } finally { await app.cleanup(); }
});

test('DineSafe renders before optional neighbourhood-fit geometry and loads it once on selection', async () => {
  const geometry={type:'FeatureCollection',features:[{
    type:'Feature',properties:{AREA_NAME:'Synthetic Area'},
    geometry:{type:'Polygon',coordinates:[[[-79.3,43.6],[-79.1,43.6],[-79.1,43.8],[-79.3,43.8],[-79.3,43.6]]]},
  }]};
  let requests=0,resolveGeometry;
  const snapshot=fixture(2);
  snapshot.establishments[1].neighbourhood='Other Area';
  const app=await loadApp(snapshot,{neighbourhoodFetch:()=>{
    requests++;
    return new Promise(resolve=>{resolveGeometry=()=>resolve({ok:true,json:async()=>geometry});});
  }});
  try {
    const list=app.document.getElementById('record-list');
    assert.equal(list.querySelectorAll('.record-item').length,2,'the first DineSafe rows render without waiting for geometry');
    assert.equal(requests,0,'startup does not request map-fit-only neighbourhood geometry');
    app.map.load();
    const neighbourhood=app.document.getElementById('neighbourhood');
    neighbourhood.value='Synthetic Area';
    neighbourhood.dispatch('change');
    assert.equal(requests,1,'the first legacy neighbourhood selection starts the optional request');
    assert.equal(list.querySelectorAll('.record-item').length,1,'the list remains available while map-fit geometry is pending');
    assert.equal(list.querySelector('.record-item').dataset.id,'entry-000','the neighborhood filter is applied before optional map geometry arrives');
    resolveGeometry();
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(app.map.fitBoundsCalls.length,1,'the selected neighbourhood is fitted after geometry arrives');
    neighbourhood.dispatch('change');
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(requests,1,'the successful geometry response is cached for later selections');
    assert.equal(app.map.fitBoundsCalls.length,2);
  } finally { await app.cleanup(); }
});

test('pending neighbourhood fit cannot move the map after switching modes', async () => {
  let resolveGeometry;
  const geometry={type:'FeatureCollection',features:[{
    type:'Feature',properties:{AREA_NAME:'Synthetic Area'},
    geometry:{type:'Polygon',coordinates:[[[-79.3,43.6],[-79.1,43.6],[-79.1,43.8],[-79.3,43.8],[-79.3,43.6]]]},
  }]};
  const app=await loadApp(fixture(),{neighbourhoodFetch:()=>new Promise(resolve=>{
    resolveGeometry=()=>resolve({ok:true,json:async()=>geometry});
  })});
  try {
    app.map.load();
    const select=app.document.getElementById('neighbourhood');
    select.value='Synthetic Area';select.dispatch('change');
    assert.equal(app.map.fitBoundsCalls.length,0);
    app.document.tabs.find(tab=>tab.dataset.mode==='beach').click();
    resolveGeometry();
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(app.map.fitBoundsCalls.length,0,'a response from the abandoned DineSafe fit does not move the Beach camera');
    assert.equal(app.document.getElementById('results-title').textContent,'Beach samples');
  } finally { await app.cleanup(); }
});

test('pending neighbourhood fit cannot override a later Fit Scarborough action', async () => {
  let resolveGeometry;
  const geometry={type:'FeatureCollection',features:[{
    type:'Feature',properties:{AREA_NAME:'Synthetic Area'},
    geometry:{type:'Polygon',coordinates:[[[-79.3,43.6],[-79.1,43.6],[-79.1,43.8],[-79.3,43.8],[-79.3,43.6]]]},
  }]};
  const app=await loadApp(fixture(),{neighbourhoodFetch:()=>new Promise(resolve=>{
    resolveGeometry=()=>resolve({ok:true,json:async()=>geometry});
  })});
  try {
    app.map.load();
    const select=app.document.getElementById('neighbourhood');
    select.value='Synthetic Area';select.dispatch('change');
    app.document.getElementById('fit').click();
    assert.equal(app.map.fitBoundsCalls.length,1,'Fit Scarborough applies the later camera request immediately');
    resolveGeometry();
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(app.map.fitBoundsCalls.length,1,'late neighborhood geometry cannot override Fit Scarborough');
  } finally { await app.cleanup(); }
});

test('pending neighbourhood fit cannot override result-selection camera movement', async () => {
  let resolveGeometry;
  const geometry={type:'FeatureCollection',features:[{
    type:'Feature',properties:{AREA_NAME:'Synthetic Area'},
    geometry:{type:'Polygon',coordinates:[[[-79.3,43.6],[-79.1,43.6],[-79.1,43.8],[-79.3,43.8],[-79.3,43.6]]]},
  }]};
  const app=await loadApp(fixture(),{neighbourhoodFetch:()=>new Promise(resolve=>{
    resolveGeometry=()=>resolve({ok:true,json:async()=>geometry});
  })});
  try {
    app.map.load();
    const select=app.document.getElementById('neighbourhood');
    select.value='Synthetic Area';select.dispatch('change');
    app.document.getElementById('record-list').querySelector('.record-item').click();
    assert.equal(app.map.easeToCalls.length,1,'selecting a result requests its camera position');
    resolveGeometry();
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(app.map.fitBoundsCalls.length,0,'late neighborhood geometry cannot override the selected result camera');
  } finally { await app.cleanup(); }
});

test('pending neighbourhood fit yields to direct map camera movement', async () => {
  let resolveGeometry;
  const geometry={type:'FeatureCollection',features:[{
    type:'Feature',properties:{AREA_NAME:'Synthetic Area'},
    geometry:{type:'Polygon',coordinates:[[[-79.3,43.6],[-79.1,43.6],[-79.1,43.8],[-79.3,43.8],[-79.3,43.6]]]},
  }]};
  const app=await loadApp(fixture(),{neighbourhoodFetch:()=>new Promise(resolve=>{
    resolveGeometry=()=>resolve({ok:true,json:async()=>geometry});
  })});
  try {
    app.map.load();
    const select=app.document.getElementById('neighbourhood');
    select.value='Synthetic Area';select.dispatch('change');
    app.map.emit('movestart');
    resolveGeometry();
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(app.map.fitBoundsCalls.length,0,'new map movement supersedes the pending fit');
  } finally { await app.cleanup(); }
});

test('neighbourhood geometry failure leaves DineSafe selection usable without repeated requests', async () => {
  let requests=0;
  const snapshot=fixture(2);
  snapshot.establishments[1].neighbourhood='Other Area';
  const app=await loadApp(snapshot,{neighbourhoodFetch:async()=>{requests++;return {ok:false,status:503};}});
  try {
    app.map.load();
    const select=app.document.getElementById('neighbourhood');
    select.value='Synthetic Area';
    select.dispatch('change');
    await new Promise(resolve=>setTimeout(resolve,0));
    select.dispatch('change');
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(requests,1,'a failed optional geometry request is cached rather than repeatedly retried');
    assert.equal(app.document.getElementById('record-list').querySelectorAll('.record-item').length,1);
    assert.equal(app.document.getElementById('record-list').querySelector('.record-item').dataset.id,'entry-000','the DineSafe filter remains active when map geometry cannot be loaded');
    assert.equal(app.map.fitBoundsCalls.length,0,'a failed request leaves the current map camera alone');
  } finally { await app.cleanup(); }
});

test('production render path handles an initial not-ready snapshot', async () => {
  const app = await loadApp(fixture(0,false));
  try {
    assert.match(app.document.getElementById('data-status').textContent,/Waiting for the first checked City records/);
    assert.equal(app.document.getElementById('data-status').classList.contains('error'),false);
    assert.match(app.document.getElementById('record-list').textContent,/There are no checked DineSafe records here yet/);
  } finally { await app.cleanup(); }
});

test('production render path handles zero matching records without turning into a load error', async () => {
  const app = await loadApp(fixture());
  try {
    app.document.getElementById('search').value='no matching place';
    app.document.getElementById('search').dispatch('input');
    assert.match(app.document.getElementById('record-list').textContent,/No places match this view/);
    assert.ok(app.document.getElementById('record-list').querySelector('.empty-actions'));
    app.document.getElementById('record-list').querySelector('.empty-action').click();
    assert.equal(app.document.getElementById('record-list').querySelectorAll('.record-item').length,1,'empty-state action clears filters and recovers results');
    assert.equal(app.document.getElementById('data-status').classList.contains('error'),false);
  } finally { await app.cleanup(); }
});

test('production DineSafe details clean legacy addresses and label upstream catalogue time', async () => {
  const snapshot=fixture();
  snapshot.published_at=new Date().toISOString();
  snapshot.source={last_refreshed:'2026-10-27 08:17:32.765401'};
  snapshot.establishments[0].address='0 Synthetic Road None M1V 1V1';
  snapshot.establishments[0].type='';
  snapshot.establishments[0].inspection_detail='City finding';
  const app=await loadApp(snapshot);
  try {
    app.map.load();
    const status=app.document.getElementById('data-status').textContent;
    assert.match(status,/Last checked/);
    assert.match(status,/City catalogue date: Tuesday, October 27, 2026/);
    const list=app.document.getElementById('record-list');
    const row=list.querySelector('.record-item');
    assert.match(row.textContent,/0 Synthetic Road M1V 1V1/);
    assert.doesNotMatch(row.textContent,/ None /);
    row.click();
    assert.match(list.textContent,/City inspection note: City finding/);
  } finally { await app.cleanup(); }
});

test('production detail view suppresses literal None and keeps establishment category distinct', async () => {
  const snapshot=fixture();
  snapshot.establishments[0].inspection_detail='None';
  snapshot.establishments[0].type='Cafe';
  let app=await loadApp(snapshot);
  try {
    app.map.load();
    app.document.tabs.find(tab=>tab.dataset.mode==='all').click();
    app.map.emitLayer('click','single',{features:[{properties:{id:snapshot.establishments[0].id}}]});
    const details=app.document.getElementById('record-list').querySelector('.record-details').textContent;
    assert.match(details,/City category: Cafe/);
    assert.doesNotMatch(details,/None/);
    await app.cleanup();
    snapshot.establishments[0].type='None';
    app=await loadApp(snapshot);
    app.map.load();app.document.tabs.find(tab=>tab.dataset.mode==='all').click();app.map.emitLayer('click','single',{features:[{properties:{id:snapshot.establishments[0].id}}]});
    const noDetails=app.document.getElementById('record-list').querySelector('.record-details').textContent;
    assert.match(noDetails,/The City record has no further detail here/);
    assert.doesNotMatch(noDetails,/None/);
  } finally { await app.cleanup(); }
});

test('DineSafe map markers encode outcomes by shape and letter while retaining map selection', async () => {
  const snapshot=fixture(4);
  snapshot.establishments[0].status='Pass';
  snapshot.establishments[1].status='Conditional Pass';
  snapshot.establishments[2].status='Closed';
  snapshot.establishments[3].status='Beach sample';
  const app=await loadApp(snapshot);
  try {
    app.map.load();
    const layer=app.map.layers.single;
    assert.equal(layer.type,'symbol');
    assert.deepEqual(Object.keys(app.map.images).sort(),['status-beach','status-closed','status-conditional','status-other','status-pass']);
    assert.deepEqual(layer.layout['icon-image'],['match',['get','status'],'Pass','status-pass','Conditional Pass','status-conditional','Closed','status-closed','Beach sample','status-beach','status-other']);
    assert.equal(app.map.images['status-conditional'].options.pixelRatio,2);
    app.document.tabs.find(tab=>tab.dataset.mode==='all').click();
    app.map.emitLayer('click','single',{features:[{properties:{id:snapshot.establishments[2].id}}]});
    assert.equal(app.map.sources.places.data.features.find(feature=>feature.properties.id===snapshot.establishments[2].id).properties.selected,true,'the existing map click path marks the same record selected');

    const html=await readFile(new URL('../docs/index.html',import.meta.url),'utf8');
    const css=await readFile(new URL('../docs/styles.css',import.meta.url),'utf8');
    assert.match(app.document.getElementById('map').attributes['aria-label'],/Shapes and letters identify inspection outcomes alongside colour/i,'runtime control updates retain the accessible marker description');
    assert.match(html,/Marker shapes and letters show the outcome as well as colour/);
    assert.ok(css.includes(".dot.pass::after{content:'P'}"));
    assert.ok(css.includes(".dot.conditional::after{content:'C'}"));
    assert.ok(css.includes(".dot.closed::after{content:'X'}"));
    assert.match(css,/\.map-legend-items \.dot\.conditional\{[^}]*border-radius:0/,'the conditional legend symbol is a triangle, not a circle-triangle overlap');
    assert.match(css,/\.dot\.beach::after\{[^}]*display:inline-block;transform:rotate\(-45deg\)/,'the beach letter remains upright inside its diamond');
  } finally { await app.cleanup(); }
});

test('marker image fallback keeps letter-coded circles and describes their actual encoding', async () => {
  const app=await loadApp(fixture());
  try {
    app.document.canvas2dEnabled=false;
    app.map.load();
    assert.equal(app.map.layers.single.type,'circle');
    assert.equal(app.map.layers['single-letter'].type,'symbol');
    assert.deepEqual(app.map.layers['single-letter'].layout['text-field'],['match',['get','status'],'Pass','P','Conditional Pass','C','Closed','X','Beach sample','B','?']);
    assert.equal(app.document.getElementById('map-legend').classList.contains('marker-shape-fallback'),true);
    assert.match(app.document.getElementById('map').attributes['aria-label'],/Letters identify inspection outcomes alongside colour/);
    const css=await readFile(new URL('../docs/styles.css',import.meta.url),'utf8');
    assert.match(css,/marker-shape-fallback \.dot\.conditional\{background:#e2a03d\}/,'fallback legend matches the fallback map colour');
    assert.match(css,/marker-shape-fallback \.dot\.closed\{background:#c4534c\}/,'fallback Closed legend matches the fallback map colour');
    assert.match(css,/marker-shape-fallback \.dot\.beach\{background:#506c80\}/,'fallback beach legend uses the fallback circle colour');
  } finally { await app.cleanup(); }
});

test('production list paging, record selection, and map redraw preserve focus and reveal selection', async () => {
  const app = await loadApp(fixture(200));
  try {
    app.map.load();
    const list=app.document.getElementById('record-list');
    assert.equal(list.querySelectorAll('.record-item').length,80);
    list.querySelector('.more-results').click();
    const pageButtons=list.querySelectorAll('.record-item');
    assert.equal(pageButtons.length,160);
    assert.equal(app.document.activeElement.dataset.id,'entry-080');

    pageButtons[4].click();
    assert.equal(app.document.activeElement.dataset.id,'entry-004');
    assert.equal(app.document.activeElement.attributes['aria-expanded'],'true');
    assert.ok(list.querySelector('.record-source-link'));

    const focusedId=app.document.activeElement.dataset.id;
    app.document.activeElement=list.querySelector('.record-source-link');
    const priorSourceId=app.document.activeElement.dataset.id;
    app.map.emit('moveend');
    assert.equal(app.document.activeElement.classList.contains('record-source-link'),true);
    assert.equal(app.document.activeElement.dataset.id,priorSourceId);
    assert.equal(focusedId,'entry-004');

    app.map.emitLayer('click','single',{features:[{properties:{id:'entry-199'}}]});
    const selectedCard=list.querySelectorAll('.record-card').find(card=>card.dataset.id==='entry-199');
    assert.ok(selectedCard);
    assert.deepEqual(selectedCard.scrollCalls,[{block:'nearest'}]);
    assert.equal(app.document.activeElement,app.map.canvas);
  } finally { await app.cleanup(); }
});

function selectedTransport({stale=false,delayFirst=false}={}) {
  const edit=Date.now()-(stale?31:5)*60_000;
  let calls=0, firstSignal=null;
  const response=(payload)=>({ok:true,status:200,url:'',redirected:false,headers:{get:()=> 'application/json'},json:async()=>payload,text:async()=>JSON.stringify(payload)});
  const fields=[{name:'OBJECTID',type:'esriFieldTypeOID'},{name:'DIVISION',type:'esriFieldTypeString'}];
  const metadata={fields,editingInfo:{lastEditDate:edit,dataLastEditDate:edit,schemaLastEditDate:edit}};
  const fetchImpl=async(url,init)=>{
    calls++; if(!firstSignal)firstSignal=init.signal;
    if(init.signal.aborted)throw new Error('aborted');
    if(delayFirst&&calls===1)return new Promise((resolve,reject)=>{
      const onAbort=()=>reject(new Error('aborted'));
      init.signal.addEventListener('abort',onAbort,{once:true});
      setTimeout(()=>{init.signal.removeEventListener('abort',onAbort);resolve(response(metadata));},1000);
    });
    const parsed=new URL(url);
    if(parsed.pathname.endsWith('/FeatureServer/0'))return response(metadata);
    if(parsed.searchParams.get('returnCountOnly')==='true')return response({count:16});
    return response({features:[{attributes:{DIVISION:'D41',call_count:7}},{attributes:{DIVISION:'D42',call_count:5}},{attributes:{DIVISION:'D43',call_count:4}}]});
  };
  return {fetchImpl,get calls(){return calls;},get firstSignal(){return firstSignal;}};
}

test('selected-calls mode fetches only on explicit view selection and clears counts on exit', async () => {
  const transport=selectedTransport();
  const app=await loadApp(fixture(),{selectedFetch:transport.fetchImpl});
  try {
    app.map.load();
    assert.equal(transport.calls,0);
    app.document.tabs.find(tab=>tab.dataset.mode==='selected-calls').click();
    await new Promise(resolve=>setTimeout(resolve,0));
    const list=app.document.getElementById('record-list');
    assert.match(list.textContent,/Selected calls published by TPS/);
    assert.match(list.textContent,/Division 41/);
    assert.match(list.textContent,/Division 42/);
    assert.match(list.textContent,/Division 43/);
    assert.match(app.document.getElementById('results-caption').textContent,/not all crime, police activity, or officer presence/i);
    assert.equal(list.querySelectorAll('.selected-call-row').length,3);
    assert.equal(transport.calls,5);
    assert.deepEqual(app.map.sources.places.data.features,[]);
    app.document.tabs.find(tab=>tab.dataset.mode==='all').click();
    assert.doesNotMatch(list.textContent,/Division 41/);
    app.document.tabs.find(tab=>tab.dataset.mode==='selected-calls').click();
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(list.querySelectorAll('.selected-call-row').length,0);
    assert.match(list.textContent,/cannot verify fresh selected-call counts/i);
    assert.equal(transport.calls,5);
  } finally { await app.cleanup(); }
});

test('stale selected-call source response renders unavailable without counts', async () => {
  const transport=selectedTransport({stale:true});
  const app=await loadApp(fixture(),{selectedFetch:transport.fetchImpl});
  try {
    app.document.tabs.find(tab=>tab.dataset.mode==='selected-calls').click();
    await new Promise(resolve=>setTimeout(resolve,0));
    const list=app.document.getElementById('record-list');
    assert.equal(list.querySelectorAll('.selected-call-row').length,0);
    assert.match(list.textContent,/cannot verify fresh selected-call counts/i);
    assert.equal(transport.calls,1);
  } finally { await app.cleanup(); }
});

test('hiding selected-calls view aborts its in-flight request and discards counts', async () => {
  const transport=selectedTransport({delayFirst:true});
  const app=await loadApp(fixture(),{selectedFetch:transport.fetchImpl});
  try {
    app.document.tabs.find(tab=>tab.dataset.mode==='selected-calls').click();
    await new Promise(resolve=>setTimeout(resolve,0));
    app.document.visibilityState='hidden';
    app.document.dispatch('visibilitychange');
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(transport.firstSignal.aborted,true);
    assert.equal(app.document.getElementById('record-list').querySelectorAll('.selected-call-row').length,0);
  } finally { await app.cleanup(); }
});

test('resetting selected calls aborts its request and clears its expiry lifecycle', async () => {
  const transport=selectedTransport({delayFirst:true});
  const app=await loadApp(fixture(),{selectedFetch:transport.fetchImpl});
  try {
    app.document.tabs.find(tab=>tab.dataset.mode==='selected-calls').click();
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(transport.firstSignal.aborted,false);
    app.document.getElementById('reset').click();
    assert.equal(transport.firstSignal.aborted,true);
    assert.match(app.document.getElementById('record-list').textContent,/Place 000/);
    assert.equal(app.document.getElementById('record-list').querySelectorAll('.selected-call-row').length,0);
  } finally { await app.cleanup(); }
});

test('MapLibre production and test pins use a patched, lockfile-matched release', async () => {
  const [packageJson, lockJson, html, browserTests] = await Promise.all([
    readFile(new URL('../package.json', import.meta.url), 'utf8').then(JSON.parse),
    readFile(new URL('../package-lock.json', import.meta.url), 'utf8').then(JSON.parse),
    readFile(new URL('../docs/index.html', import.meta.url), 'utf8'),
    readFile(new URL('./browser.integration.test.mjs', import.meta.url), 'utf8'),
  ]);
  const version = packageJson.devDependencies['maplibre-gl'];
  const [major, minor, patch] = version.split('.').map(Number);
  const patched = major > 6 || (major === 6 && (minor > 4 || (minor === 4 && patch >= 1)));
  assert.ok(patched, `MapLibre ${version} predates the 6.4.1 sanitizer fix`);
  assert.equal(lockJson.packages['node_modules/maplibre-gl'].version, version);
  for (const extension of ['mjs', 'css']) {
    assert.ok(html.includes(`maplibre-gl@${version}/dist/maplibre-gl.${extension}`));
    assert.ok(browserTests.includes(`maplibre-gl@${version}/dist/maplibre-gl.${extension}`));
  }
});
