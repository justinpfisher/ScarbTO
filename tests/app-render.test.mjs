import test from 'node:test';
import assert from 'node:assert/strict';

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
    this.tabs = ['recent','all'].map(mode => {
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
  createElement(tagName) { return new FakeElement(this,tagName); }
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
    this.isLoaded = false;
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
  addLayer() {}
  getSource(id) { return this.sources[id]; }
  getBounds() { return {contains:() => true}; }
  loaded() { return this.isLoaded; }
  getZoom() { return 11; }
  getCanvas() { return this.canvas; }
  easeTo() { this.emit('moveend'); }
  fitBounds() { this.emit('moveend'); }
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

async function loadApp(snapshot) {
  const document = new FakeDocument();
  let map;
  const prior = {
    document:globalThis.document,
    localStorage:globalThis.localStorage,
    fetch:globalThis.fetch,
    maplibregl:globalThis.maplibregl,
  };
  globalThis.document = document;
  globalThis.localStorage = {getItem:() => null, setItem:() => {}};
  globalThis.fetch = async url => url.includes('snapshot.json')
    ? {ok:true,json:async()=>snapshot}
    : {ok:false};
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

test('production render path handles an initial not-ready snapshot', async () => {
  const app = await loadApp(fixture(0,false));
  try {
    assert.match(app.document.getElementById('data-status').textContent,/Awaiting first validated City data import/);
    assert.equal(app.document.getElementById('data-status').classList.contains('error'),false);
    assert.match(app.document.getElementById('record-list').textContent,/No validated DineSafe snapshot/);
  } finally { await app.cleanup(); }
});

test('production render path handles zero matching records without turning into a load error', async () => {
  const app = await loadApp(fixture());
  try {
    app.document.getElementById('search').value='no matching place';
    app.document.getElementById('search').dispatch('input');
    assert.match(app.document.getElementById('record-list').textContent,/No matching places in the current map view/);
    assert.equal(app.document.getElementById('data-status').classList.contains('error'),false);
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
