import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdir, readFile, stat} from 'node:fs/promises';
import {extname, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
import {WARDS, NEIGHBOURHOODS} from '../docs/area-selection.mjs';

const root = resolve(fileURLToPath(new URL('../docs/', import.meta.url)));
const maplibreRoot = resolve(fileURLToPath(new URL('../node_modules/maplibre-gl/dist/', import.meta.url)));
const outputDir = resolve(fileURLToPath(new URL('../test-results/beach-browser/', import.meta.url)));
const mime = new Map([
  ['.html', 'text/html; charset=utf-8'], ['.mjs', 'text/javascript; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'], ['.css', 'text/css; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'], ['.csv', 'text/csv; charset=utf-8'],
  ['.geojson', 'application/geo+json; charset=utf-8'],
]);

test('UI source text retains intended separators and badge text', async () => {
  const [html, app] = await Promise.all([
    readFile(resolve(root, 'index.html'), 'utf8'),
    readFile(resolve(root, 'app.mjs'), 'utf8'),
  ]);
  assert.equal((html + String.fromCharCode(10) + app).includes(String.fromCharCode(0xfffd)), false);
  assert.match(html, /class="data-pill">DineSafe<\/span>/);
  assert.ok(html.includes("DineSafe Open Data</a> " + String.fromCharCode(0x00b7) + " <a"));
  assert.ok(app.includes("Toronto Open Data " + String.fromCharCode(0x00b7) + " dated samples"));
});

const snapshot = {
  schema_version: 1,
  ready: true,
  published_at: '2026-10-27T12:00:00Z',
  establishments: [
    {id: 'fixture-a', establishment_id: 'fixture-a', name: 'Fixture Cafe', address: '10 Test Road', status: 'Pass', inspection_date: '2026-10-26', longitude: -79.255, latitude: 43.775, neighbourhood: 'Agincourt'},
    {id: 'fixture-b', establishment_id: 'fixture-b', name: 'Fixture Bakery', address: '20 Sample Avenue', status: 'Conditional Pass', inspection_date: '2026-10-25', longitude: -79.29, latitude: 43.73, neighbourhood: 'Woburn'},
  {id: 'boundary-edge-fixture', establishment_id: 'boundary-edge-fixture', name: 'Boundary Edge Fixture', address: '30 Boundary Road', status: 'Pass', inspection_date: '2026-10-24', longitude: -79.344, latitude: 43.671, neighbourhood: 'Test area'},
  ],
  activity: [],
};

async function startStaticServer() {
  const server = createServer(async (request, response) => {
    const path = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
    const relative = path === '/' ? 'index.html' : path.replace(/^\/+/, '');
    const file = resolve(root, relative);
    if (file !== root && !file.startsWith(root + sep)) {
      response.writeHead(403).end();
      return;
    }
    try {
      const contents = await readFile(file);
      response.writeHead(200, {'content-type': mime.get(extname(file)) || 'application/octet-stream'});
      response.end(contents);
    } catch {
      response.writeHead(404).end('not found');
    }
  });
  await new Promise((resolveListen, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolveListen);
  });
  return {server, origin: `http://127.0.0.1:${server.address().port}`};
}

async function traceSelectedCalls(page) {
  await page.addInitScript(() => {
    window.__selectedCallsFetches = [];
    const originalFetch = window.fetch.bind(window);
    window.fetch = (...args) => {
      const url = String(args[0]);
      if (url.includes('C4S_Public_NoGO/FeatureServer/0')) window.__selectedCallsFetches.push(url);
      return originalFetch(...args);
    };
  });
}

function waitForSelectedCallsRequest(page) {
  return page.waitForRequest(request => request.url().includes('C4S_Public_NoGO/FeatureServer/0?f=json'), {timeout: 5_000})
    .catch(async error => {
      const diagnostics = await page.evaluate(() => ({
        visibility: document.visibilityState,
        tabPressed: document.querySelector('[data-mode="selected-calls"]')?.getAttribute('aria-pressed'),
        fetches: window.__selectedCallsFetches,
        status: document.querySelector('#data-status')?.textContent,
        list: document.querySelector('#record-list')?.textContent,
      }));
      throw new Error(`${error.message}; selected-calls browser state: ${JSON.stringify(diagnostics)}`);
    });
}


async function installLocalRoutes(page, origin, {snapshotStatus = 200, snapshotBody = snapshot, beachStatus = 200, beachDelayMs = 0, selectedCalls = false, selectedCallsDelayMs = 0, selectedCallsSourceAgeMs = 60_000, maplibreFailure = false, onSelectedCallsRequest = () => {}} = {}) {
  let beachResponseSent = false;
  let selectedCallsRequestIndex=0;
  const selectedCallsEditDate=Date.now()-selectedCallsSourceAgeMs;
  await page.route('**/*', async route => {
    const url = route.request().url();
    if (url.startsWith('https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0')) {
      if(!selectedCalls){await route.abort('blockedbyclient');return;}
      assert.equal(route.request().method(),'GET','the selected-calls browser client uses read-only GET requests');
      const parsed=new URL(url);
      const params=parsed.searchParams;
      const endpoint=parsed.pathname.endsWith('/FeatureServer/0');
      if(endpoint){
        assert.deepEqual([...params.keys()],['f'],'metadata requests contain only the JSON format selector');
        assert.equal(params.get('f'),'json');
      }else if(params.get('returnCountOnly')==='true'){
        assert.deepEqual([...params.keys()],['where','f','returnCountOnly'],'control requests have only bounded count parameters');
        assert.equal(params.get('where'),"DIVISION IN ('D41','D42','D43')");
        assert.equal(params.get('f'),'json');
      }else{
        assert.deepEqual([...params.keys()],['where','f','outFields','returnGeometry','groupByFieldsForStatistics','orderByFields','outStatistics'],'grouped requests have only the reviewed fields');
        assert.equal(params.get('where'),"DIVISION IN ('D41','D42','D43')");
        assert.equal(params.get('f'),'json');
        assert.equal(params.get('outFields'),'DIVISION');
        assert.equal(params.get('returnGeometry'),'false');
        assert.equal(params.get('groupByFieldsForStatistics'),'DIVISION');
        assert.equal(params.get('orderByFields'),'DIVISION');
        assert.deepEqual(JSON.parse(params.get('outStatistics')),[{statisticType:'count',onStatisticField:'OBJECTID',outStatisticFieldName:'call_count'}]);
      }
      const requestIndex=selectedCallsRequestIndex++;onSelectedCallsRequest(url,requestIndex);
      if(selectedCallsDelayMs&&requestIndex===0)await new Promise(resolveDelay=>setTimeout(resolveDelay,selectedCallsDelayMs));
      const edit=selectedCallsEditDate;
      const metadata={fields:[{name:'OBJECTID',type:'esriFieldTypeOID'},{name:'DIVISION',type:'esriFieldTypeString'}],editingInfo:{lastEditDate:edit,dataLastEditDate:edit,schemaLastEditDate:edit}};
      const body=parsed.pathname.endsWith('/FeatureServer/0')?metadata:parsed.searchParams.get('returnCountOnly')==='true'?{count:16}:{features:[{attributes:{DIVISION:'D41',call_count:7}},{attributes:{DIVISION:'D42',call_count:5}},{attributes:{DIVISION:'D43',call_count:4}}]};
      await route.fulfill({status:200,contentType:'application/json',headers:{'access-control-allow-origin':'*'},body:JSON.stringify(body)});
      return;
    }
    if (url === `${origin}/app.mjs`) {
      const response = await route.fetch();
      const source = await response.text();
      const instrumented = source.replace('map=new maplibregl.Map(', 'window.__scarbMap=map=new maplibregl.Map(');
      assert.notEqual(instrumented, source, 'test route exposes the production MapLibre instance without changing app files');
      await route.fulfill({response, body: instrumented});
      return;
    }
    if (url.startsWith(`${origin}/data/snapshot.json`)) {
      await route.fulfill({status: snapshotStatus, contentType: 'application/json', body: JSON.stringify(snapshotBody)});
      return;
    }
    if (url.startsWith(`${origin}/data/beach-sample-preview.json`)) {
      if (beachDelayMs) await new Promise(resolveDelay => setTimeout(resolveDelay, beachDelayMs));
      const body = await readFile(resolve(root, 'data/beach-sample-preview.json'), 'utf8');
      await route.fulfill({status: beachStatus, contentType: 'application/json', body});
      beachResponseSent = true;
      return;
    }
    if (url === 'https://cdn.jsdelivr.net/npm/maplibre-gl@6.4.1/dist/maplibre-gl.mjs') {
      if (maplibreFailure) {
        await route.fulfill({status: 503, contentType: 'text/plain', body: 'fixture CDN failure'});
        return;
      }
      await route.fulfill({path: resolve(maplibreRoot, 'maplibre-gl.mjs'), contentType: 'text/javascript', headers: {'access-control-allow-origin': '*'}});
      return;
    }
    if (url === 'https://cdn.jsdelivr.net/npm/maplibre-gl@6.4.1/dist/maplibre-gl-shared.mjs') {
      await route.fulfill({path: resolve(maplibreRoot, 'maplibre-gl-shared.mjs'), contentType: 'text/javascript', headers: {'access-control-allow-origin': '*'}});
      return;
    }
    if (url === 'https://cdn.jsdelivr.net/npm/maplibre-gl@6.4.1/dist/maplibre-gl-worker.mjs') {
      await route.fulfill({path: resolve(maplibreRoot, 'maplibre-gl-worker.mjs'), contentType: 'text/javascript', headers: {'access-control-allow-origin': '*'}});
      return;
    }
    if (url === 'https://cdn.jsdelivr.net/npm/maplibre-gl@6.4.1/dist/maplibre-gl.css') {
      await route.fulfill({path: resolve(maplibreRoot, 'maplibre-gl.css'), contentType: 'text/css'});
      return;
    }
    if (url === 'https://tiles.openfreemap.org/styles/liberty') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({version: 8, glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf', sources: {}, layers: [{id: 'background', type: 'background', paint: {'background-color': '#edf2ed'}}]}),
      });
      return;
    }
    if (/^https:\/\/tiles\.openfreemap\.org\/fonts\//.test(url)) {
      await route.fulfill({status: 200, contentType: 'application/x-protobuf', body: Buffer.alloc(0)});
      return;
    }
    if (url.startsWith(`${origin}/`)) {
      await route.continue();
      return;
    }
    await route.abort('blockedbyclient');
  });
  return () => beachResponseSent;
}

async function waitForMap(page) {
  await page.waitForFunction(() => window.__scarbMap?.loaded() === true, null, {timeout: 20_000});
  await page.waitForFunction(() => window.__scarbMap?.getSource('places') !== undefined, null, {timeout: 10_000});
}

async function exerciseViewport(browser, origin, {name, width, height, mobile}) {
  const context = await browser.newContext({viewport: {width, height}, deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile});
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await installLocalRoutes(page, origin);
  await page.goto(origin, {waitUntil: 'networkidle'});
  await waitForMap(page);
  await page.waitForFunction(() => window.__scarbMap.getSource('scarborough-mask') && window.__scarbMap.getSource('scarborough-boundary'));
  const boundaryState=await page.evaluate(()=>{
    const map=window.__scarbMap;
    const layers=map.getStyle().layers.map(layer=>layer.id);
    const bounds=map.getBounds();
    return {
      layerOrder:['scarborough-outside-mask','scarborough-boundary-line','clusters','single'].map(id=>layers.indexOf(id)),
      camera:[[bounds.getWest(),bounds.getSouth()],[bounds.getEast(),bounds.getNorth()]],
      hasBoundarySource:Boolean(map.getSource('scarborough-boundary')),
      hasMaskSource:Boolean(map.getSource('scarborough-mask')),
      hasBoundaryLayer:Boolean(map.getLayer('scarborough-boundary-line')),
      hasMaskLayer:Boolean(map.getLayer('scarborough-outside-mask')),
    };
  });
  assert.ok(boundaryState.layerOrder.every(index=>index>=0));
  assert.ok(boundaryState.layerOrder[0]<boundaryState.layerOrder[1]&&boundaryState.layerOrder[1]<boundaryState.layerOrder[2]&&boundaryState.layerOrder[2]<boundaryState.layerOrder[3],'outside mask and boundary draw below establishment pins');
  assert.equal(await page.evaluate(()=>window.__scarbMap.getLayer('single')?.type),'symbol','individual outcomes use a shape-and-letter marker layer');
  assert.equal(await page.evaluate(()=>window.__scarbMap.hasImage('status-pass')&&window.__scarbMap.hasImage('status-conditional')&&window.__scarbMap.hasImage('status-closed')),true,'DineSafe marker images are installed before rendering');
  assert.equal(boundaryState.hasBoundarySource,true,'display uses the independent official council feature');
  assert.equal(boundaryState.hasMaskSource,true);
  assert.equal(boundaryState.hasBoundaryLayer,true);
  assert.equal(boundaryState.hasMaskLayer,true);
  assert.ok(boundaryState.camera[0][0]<=-79.3413178929128&&boundaryState.camera[0][1]<=43.6716713902779&&boundaryState.camera[1][0]>=-79.115243188678&&boundaryState.camera[1][1]>=43.8554571861712,'initial camera fits the complete official display boundary');
  if (mobile) await page.getByRole('button', {name: 'Filters'}).click();
  await page.getByRole('button', {name: 'All establishments'}).click();
  await page.getByRole('button', {name: 'Fixture Cafe'}).waitFor();
  assert.equal(await page.getByRole('button', {name: 'Fixture Bakery'}).count(), 1, `${name}: synthetic records are listed`);
  assert.equal(await page.getByRole('button', {name: 'Boundary Edge Fixture'}).count(), 1, `${name}: the display boundary does not filter the list`);

  const initialCenter = await page.evaluate(() => window.__scarbMap.getCenter().toArray());
  await page.getByRole('button', {name: 'Fixture Bakery'}).click();
  await page.waitForFunction(() => Math.abs(window.__scarbMap.getCenter().lng - -79.29) < 0.002);
  const selectedCenter = await page.evaluate(() => window.__scarbMap.getCenter().toArray());
  assert.ok(Math.abs(selectedCenter[0] - initialCenter[0]) > 0.005, `${name}: selecting a result moves the real map camera`);
  assert.equal(await page.locator('.record-item.active').getAttribute('data-id'), 'fixture-b');
  await page.evaluate(() => window.__scarbMap.easeTo({center: [-79.255, 43.775], zoom: 14, duration: 0}));
  await page.waitForFunction(() => window.__scarbMap.queryRenderedFeatures(undefined, {layers: ['single']}).some(feature => feature.properties.id === 'fixture-a'));
  await page.locator('#map').click({position: {x: Math.floor((await page.locator('#map').boundingBox()).width / 2), y: Math.floor((await page.locator('#map').boundingBox()).height / 2)}});
  assert.equal(await page.locator('.record-item.active').getAttribute('data-id'), 'fixture-a', `${name}: clicking a real rendered MapLibre marker selects its record`);

  await page.getByRole('button', {name: 'Beach samples'}).click();
  await page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor();
  await page.getByText('Latest 10 catalogue rows shown', {exact: false}).waitFor();
  assert.equal(await page.locator('#search').isDisabled(), true, `${name}: DineSafe controls are disabled in beach mode`);
  await page.waitForFunction(() => Math.abs(window.__scarbMap.getCenter().lng - -79.2252) < 0.002);
  const beachCenter = await page.evaluate(() => window.__scarbMap.getCenter().toArray());
  assert.ok(Math.abs(beachCenter[0] - selectedCenter[0]) > 0.01, `${name}: beach mode moves the real map camera`);
  assert.equal(await page.locator('.beach-sample-preview-list li').count(), 10);
  assert.match(await page.locator('.beach-sample-preview>p').first().textContent(), /not current swimming advice/i);
  assert.match(await page.locator('.beach-sample-preview>p').first().textContent(), /reference point, not sample-site coordinates/i);
  assert.match(await page.locator('.beach-sample-preview>p').first().textContent(), /Open Government Licence.*Toronto/i);
  assert.match(await page.locator('#data-status').textContent(), /Toronto sample rows checked 2026-10-27; latest sample 2026-09-16\. Not current swimming status\./);
  assert.equal(await page.locator('.beach-sample-preview a').count(), 3);
  const links = await page.locator('.beach-sample-preview a').evaluateAll(anchors => anchors.map(anchor => ({href: anchor.href, rel: anchor.rel, target: anchor.target})));
  assert.ok(links.every(link => link.target === '_blank' && link.rel.includes('noopener') && link.rel.includes('noreferrer')));
  assert.ok(links.some(link => link.href === 'https://open.toronto.ca/dataset/toronto-beaches-water-quality/'));
  assert.ok(links.some(link => link.href === 'https://open.toronto.ca/open-data-licence/'));
  assert.ok(links.some(link => link.href.includes('/swimsafe/beach-water-quality/')));

  // Verify real keyboard navigation and activation across the production tab controls.
  const recent = page.getByRole('button', {name: 'Recent activity'});
  await recent.focus();
  await page.keyboard.press('Enter');
  assert.equal(await recent.getAttribute('aria-pressed'), 'true', `${name}: browse tabs work with keyboard activation`);
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement?.textContent.trim()), 'All establishments');
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement?.textContent.trim()), 'Beach samples');
  await page.keyboard.press('Enter');
  assert.equal(await page.getByRole('button', {name: 'Beach samples'}).getAttribute('aria-pressed'), 'true');
  let sourceLinkReached = false;
  for (let index = 0; index < 20; index++) {
    if (await page.evaluate(() => document.activeElement?.matches('.beach-sample-preview a'))) {
      sourceLinkReached = true;
      break;
    }
    await page.keyboard.press('Tab');
  }
  assert.equal(sourceLinkReached, true, `${name}: source links are reachable with Tab`);

  if (!mobile) {
    await page.setViewportSize({width: 1024, height: 768});
    await page.waitForFunction(() => Math.abs(document.querySelector('#map canvas').getBoundingClientRect().width - document.querySelector('#map').clientWidth) < 2);
    await page.getByRole('button', {name: 'Show all Scarborough'}).click();
    await page.waitForFunction(() => {
      const bounds=window.__scarbMap.getBounds();
      return bounds.getWest()<=-79.3413178929128&&bounds.getSouth()<=43.6716713902779&&bounds.getEast()>=-79.115243188678&&bounds.getNorth()>=43.8554571861712;
    });
    await page.setViewportSize({width, height});
    await page.waitForFunction(() => Math.abs(document.querySelector('#map canvas').getBoundingClientRect().width - document.querySelector('#map').clientWidth) < 2);
    await page.getByRole('button', {name: 'Show all Scarborough'}).click();
    await page.waitForFunction(() => {
      const bounds=window.__scarbMap.getBounds();
      return bounds.getWest()<=-79.3413178929128&&bounds.getSouth()<=43.6716713902779&&bounds.getEast()>=-79.115243188678&&bounds.getNorth()>=43.8554571861712;
    });
  }

  const dimensions = await page.evaluate(() => ({
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    mapWidth: document.querySelector('#map canvas')?.getBoundingClientRect().width,
    mapHeight: document.querySelector('#map canvas')?.getBoundingClientRect().height,
    center: window.__scarbMap.getCenter().toArray(),
    zoom: window.__scarbMap.getZoom(),
  }));
  assert.ok(dimensions.mapWidth > 0 && dimensions.mapHeight > 0, `${name}: MapLibre rendered a real canvas`);
  assert.ok(dimensions.documentWidth <= dimensions.viewportWidth, `${name}: no horizontal page overflow`);
  assert.ok(dimensions.zoom > 0);
  if (mobile) {
    const [legend, attribution, fit] = await Promise.all([
      page.locator('.map-legend').boundingBox(),
      page.locator('.maplibregl-ctrl-attrib').boundingBox(),
      page.locator('#fit').boundingBox(),
    ]);
    assert.ok(legend && attribution && fit, `${name}: map legend, attribution, and fit control remain rendered`);
    const overlaps = legend.x < attribution.x + attribution.width && legend.x + legend.width > attribution.x
      && legend.y < attribution.y + attribution.height && legend.y + legend.height > attribution.y;
    assert.equal(overlaps, false, `${name}: legend does not cover map attribution`);
    assert.ok(fit.y + fit.height < legend.y, `${name}: fit control remains clear above the legend`);
  }
  await page.screenshot({path: resolve(outputDir, `${name}.png`), fullPage: true});
  assert.deepEqual(pageErrors, [], `${name}: no uncaught app errors`);
  await context.close();
  return dimensions;
}

async function openScenario(browser, origin, routeOptions = {}, {width = 1280, height = 900, initialMode = null} = {}) {
  const context = await browser.newContext({viewport: {width, height}});
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  if (initialMode) await page.addInitScript(mode => localStorage.setItem('scarbto-filters-v1', JSON.stringify({mode})), initialMode);
  const isBeachResponseSent = await installLocalRoutes(page, origin, routeOptions);
  await page.goto(origin, {waitUntil: 'domcontentloaded'});
  await waitForMap(page);
  return {context, page, pageErrors, isBeachResponseSent};
}

test('rendered DineSafe and beach views work across desktop and mobile', {timeout: 90_000}, async t => {
  await stat(maplibreRoot);
  await mkdir(outputDir, {recursive: true});
  const {server, origin} = await startStaticServer();
  const browser = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl']});
  t.after(async () => {
    await browser.close();
    await new Promise(resolveClose => server.close(resolveClose));
  });
  const desktop = await exerciseViewport(browser, origin, {name: 'desktop', width: 1365, height: 900, mobile: false});
  const mobile = await exerciseViewport(browser, origin, {name: 'mobile', width: 390, height: 844, mobile: true});
  assert.ok(desktop.mapWidth > mobile.mapWidth, 'desktop map viewport is wider than mobile');
  assert.ok(Math.abs(mobile.center[0] - -79.2252) < 0.002, 'mobile camera remains centered on the beach view');
});

test('independent feed failures do not suppress the other rendered view', {timeout: 60_000}, async t => {
  const {server, origin} = await startStaticServer();
  const browser = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl']});
  t.after(async () => {
    await browser.close();
    await new Promise(resolveClose => server.close(resolveClose));
  });

  const beachSurvivesDineSafeError = await openScenario(browser, origin, {snapshotStatus: 503}, {initialMode: 'beach'});
  t.after(() => beachSurvivesDineSafeError.context.close());
  await beachSurvivesDineSafeError.page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor();
  assert.equal(await beachSurvivesDineSafeError.page.locator('.beach-sample-preview-list li').count(), 10);
  assert.match(await beachSurvivesDineSafeError.page.locator('#data-status').textContent(), /Toronto sample rows checked/);
  await beachSurvivesDineSafeError.page.getByRole('button', {name: 'All establishments'}).click();
  await beachSurvivesDineSafeError.page.getByText(/Could not load the published dataset \(HTTP 503\)/).waitFor();
  assert.equal(await beachSurvivesDineSafeError.page.locator('#results-title').textContent(), 'Matching places');
  assert.equal(await beachSurvivesDineSafeError.page.locator('#results-kicker').textContent(), 'Official inspections');
  assert.equal(await beachSurvivesDineSafeError.page.locator('#results-caption').textContent(), 'Results follow the map and your filters.');
  assert.equal(await beachSurvivesDineSafeError.page.locator('#results-count').textContent(), 'Unavailable');
  await beachSurvivesDineSafeError.page.waitForFunction(() => !window.__scarbMap.querySourceFeatures('places').some(feature => feature.properties.id === 'beach:10'));
  assert.deepEqual(beachSurvivesDineSafeError.pageErrors, []);

  const dineSafeSurvivesBeachError = await openScenario(browser, origin, {beachStatus: 503}, {initialMode: 'all'});
  t.after(() => dineSafeSurvivesBeachError.context.close());
  await dineSafeSurvivesBeachError.page.getByRole('button', {name: 'Fixture Cafe'}).waitFor();
  await dineSafeSurvivesBeachError.page.getByRole('button', {name: 'Fixture Bakery'}).waitFor();
  assert.deepEqual(dineSafeSurvivesBeachError.pageErrors, []);

  const readyFalse = {schema_version: 1, ready: false, published_at: null, establishments: [], activity: []};
  const switchingView = await openScenario(browser, origin, {snapshotBody: readyFalse}, {initialMode: 'beach'});
  t.after(() => switchingView.context.close());
  await switchingView.page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor();
  await switchingView.page.waitForFunction(() => window.__scarbMap.querySourceFeatures('places').some(feature => feature.properties.id === 'beach:10'));
  await switchingView.page.getByRole('button', {name: 'All establishments'}).click();
  await switchingView.page.getByText(/No validated DineSafe snapshot has been published/).waitFor();
  assert.equal(await switchingView.page.locator('#results-title').textContent(), 'Matching places');
  assert.equal(await switchingView.page.locator('#results-kicker').textContent(), 'Official inspections');
  assert.equal(await switchingView.page.locator('#results-caption').textContent(), 'Results follow the map and your filters.');
  assert.equal(await switchingView.page.locator('#results-count').textContent(), '0 in view');
  await switchingView.page.waitForFunction(() => !window.__scarbMap.querySourceFeatures('places').some(feature => feature.properties.id === 'beach:10'));
  assert.deepEqual(switchingView.pageErrors, []);

  const rejectedSchema = {...snapshot, schema_version: 2, establishments: [{...snapshot.establishments[0], id: 'should-not-render'}]};
  const rejectedView = await openScenario(browser, origin, {snapshotBody: rejectedSchema}, {initialMode: 'beach'});
  t.after(() => rejectedView.context.close());
  await rejectedView.page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor();
  await rejectedView.page.getByRole('button', {name: 'All establishments'}).click();
  await rejectedView.page.getByText(/Could not load the published dataset \(Unsupported schema\)/).waitFor();
  assert.equal(await rejectedView.page.locator('#results-title').textContent(), 'Matching places');
  assert.equal(await rejectedView.page.locator('#results-caption').textContent(), 'Results follow the map and your filters.');
  assert.equal(await rejectedView.page.locator('.record-item[data-id="should-not-render"]').count(), 0);
  await rejectedView.page.waitForFunction(() => !window.__scarbMap.querySourceFeatures('places').some(feature => feature.properties.id === 'beach:10'));
  assert.deepEqual(rejectedView.pageErrors, []);

  const manyRecords = {
    ...snapshot,
    establishments: Array.from({length: 82}, (_, index) => ({
      id: `page-${String(index + 1).padStart(3, '0')}`,
      establishment_id: `page-${String(index + 1).padStart(3, '0')}`,
      name: `Paging Fixture ${String(index + 1).padStart(3, '0')}`,
      address: `${index + 1} Test Road`, status: 'Pass', inspection_date: '2026-10-27',
      longitude: -79.255, latitude: 43.775, neighbourhood: 'Agincourt',
    })),
  };
  const paging = await openScenario(browser, origin, {snapshotBody: manyRecords}, {initialMode: 'all'});
  t.after(() => paging.context.close());
  await paging.page.locator('.record-item[data-id="page-001"]').waitFor();
  assert.equal(await paging.page.locator('.record-item').count(), 80);
  await paging.page.getByRole('button', {name: 'Show next 2 matches'}).click();
  assert.equal(await paging.page.locator('.record-item').count(), 82);
  assert.equal(await paging.page.evaluate(() => document.activeElement?.dataset.id), 'page-081');
  assert.equal(await paging.page.locator('.record-item[data-id="page-082"]').isVisible(), true);
  assert.deepEqual(paging.pageErrors, []);

  const delayedBeach = await openScenario(browser, origin, {beachDelayMs: 5_000}, {initialMode: 'all'});
  t.after(() => delayedBeach.context.close());
  await delayedBeach.page.getByRole('button', {name: 'Fixture Cafe'}).waitFor({timeout: 2_000});
  assert.equal(delayedBeach.isBeachResponseSent(), false, 'DineSafe view is available while the independent beach request is still pending');
  await delayedBeach.page.getByRole('button', {name: 'Beach samples'}).click();
  await delayedBeach.page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor({timeout: 8_000});
  assert.equal(delayedBeach.isBeachResponseSent(), true);
  assert.deepEqual(delayedBeach.pageErrors, []);
});

test('DineSafe and beach lists remain usable when WebGL is unavailable', {timeout: 60_000}, async t => {
  const {server, origin} = await startStaticServer();
  const browser = await chromium.launch({args: ['--disable-webgl', '--disable-3d-apis']});
  t.after(async () => {
    await browser.close();
    await new Promise(resolveClose => server.close(resolveClose));
  });

  const openWithoutMap = async (routeOptions = {}, mode = 'all', expectRecords = true) => {
    const context = await browser.newContext({viewport: {width: 1280, height: 900}});
    const page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.addInitScript(value => localStorage.setItem('scarbto-filters-v1', JSON.stringify({mode: value})), mode);
    await installLocalRoutes(page, origin, routeOptions);
    await page.goto(origin, {waitUntil: 'domcontentloaded'});
    await page.locator('#map-fallback:not([hidden])').waitFor();
    if(expectRecords)await page.locator('.record-item').first().waitFor();
    assert.match(await page.locator('#map-fallback').textContent(), /map unavailable.*searchable results list/i);
    assert.equal(await page.locator('#map-fallback').getAttribute('aria-live'), 'polite');
    assert.equal(await page.locator('#map').getAttribute('aria-hidden'), 'true');
    assert.equal(await page.locator('#fit').isVisible(), false, 'map-only fit control is hidden');
    assert.equal(await page.locator('#fit').isDisabled(), true, 'map-only fit control is also disabled');
    assert.equal(await page.locator('#map-legend').isVisible(), false, 'map legend is hidden without a map');
    return {context, page, pageErrors};
  };

  const feeds = await openWithoutMap();
  t.after(() => feeds.context.close());
  assert.equal(await feeds.page.locator('.record-item').count(), 3, 'DineSafe records render without map bounds');

  const cafe = feeds.page.getByRole('button', {name: 'Fixture Cafe'});
  await cafe.focus();
  await feeds.page.keyboard.press('Enter');
  assert.equal(await feeds.page.locator('.record-item.active').getAttribute('data-id'), 'fixture-a');
  const cityLink = feeds.page.locator('#selected-record-details a');
  assert.equal(await cityLink.count(), 1, 'record source link remains available without map selection');
  assert.match(await cityLink.getAttribute('href'), /toronto\.ca\/community-people\/health-wellness-care\/health-programs-advice\/food-safety\/dinesafe\/#establishment\/fixture-a/);

  await feeds.page.locator('#search').fill('Bakery');
  assert.equal(await feeds.page.locator('.record-item').count(), 1, 'search filters the list without a map');
  assert.match(await feeds.page.locator('.record-item').first().textContent(), /Fixture Bakery/);
  await feeds.page.locator('#search').fill('');
  await feeds.page.getByRole('button', {name: 'Beach samples'}).click();
  await feeds.page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor();
  assert.equal(await feeds.page.locator('.beach-sample-preview-list li').count(), 10);
  assert.equal(await feeds.page.locator('.beach-sample-preview a').count(), 3, 'beach provenance links render without map');
  await feeds.page.getByRole('button', {name: 'All establishments'}).click();
  assert.equal(await feeds.page.locator('.record-item').count(), 3, 'mode switching restores the DineSafe list');
  assert.deepEqual(feeds.pageErrors, [], 'map fallback and feed interactions produce no uncaught errors');

  const manyRecords = {
    ...snapshot,
    establishments: Array.from({length: 82}, (_, index) => ({
      id: `no-map-${String(index + 1).padStart(3, '0')}`,
      establishment_id: `no-map-${String(index + 1).padStart(3, '0')}`,
      name: `No Map Fixture ${String(index + 1).padStart(3, '0')}`,
      address: `${index + 1} Test Road`, status: 'Pass', inspection_date: '2026-10-27',
      longitude: -79.255, latitude: 43.775, neighbourhood: 'Agincourt',
    })),
  };
  const paging = await openWithoutMap({snapshotBody: manyRecords});
  t.after(() => paging.context.close());
  assert.equal(await paging.page.locator('.record-item').count(), 80);
  await paging.page.getByRole('button', {name: 'Show next 2 matches'}).click();
  assert.equal(await paging.page.locator('.record-item').count(), 82);
  assert.equal(await paging.page.evaluate(() => document.activeElement?.dataset.id), 'no-map-081');
  assert.equal(await paging.page.locator('.record-item[data-id="no-map-082"]').isVisible(), true);
  assert.deepEqual(paging.pageErrors, []);

  const rejected = {...snapshot, schema_version: 2, establishments: [{...snapshot.establishments[0], id: 'must-not-render'}]};
  const invalid = await openWithoutMap({snapshotBody: rejected}, 'all', false);
  t.after(() => invalid.context.close());
  await invalid.page.getByText(/Could not load the published dataset \(Unsupported schema\)/).waitFor();
  assert.equal(await invalid.page.locator('.record-item').count(), 0, 'unsupported payload records are not rendered');
  await invalid.page.getByRole('button', {name: 'Beach samples'}).click();
  assert.equal(await invalid.page.locator('.beach-sample-preview-list li').count(), 10);
  await invalid.page.getByRole('button', {name: 'All establishments'}).click();
  await invalid.page.getByText(/Could not load the published dataset \(Unsupported schema\)/).waitFor();
  assert.equal(await invalid.page.locator('.record-item').count(), 0, 'mode switching cannot reveal rejected data');
  assert.equal(await invalid.page.locator('[data-id="must-not-render"]').count(), 0);
  assert.deepEqual(invalid.pageErrors, []);
});

test('MapLibre module failure still boots accessible DineSafe and beach views', {timeout: 60_000}, async t => {
  const {server, origin} = await startStaticServer();
  const browser = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl']});
  t.after(async () => {
    await browser.close();
    await new Promise(resolveClose => server.close(resolveClose));
  });
  const context = await browser.newContext({viewport: {width: 1280, height: 900}});
  t.after(() => context.close());
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await installLocalRoutes(page, origin, {maplibreFailure: true});
  await page.goto(origin, {waitUntil: 'domcontentloaded'});
  await page.locator('#map-fallback:not([hidden])').waitFor();
  await page.getByRole('button', {name: 'Fixture Cafe'}).waitFor();
  assert.match(await page.locator('#map-fallback').textContent(), /map unavailable.*searchable results list/i);
  await page.getByRole('button', {name: 'Beach samples'}).click();
  await page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor();
  assert.equal(await page.locator('.beach-sample-preview-list li').count(), 10);
  assert.deepEqual(pageErrors, [], 'failed third-party module does not prevent local app/feed boot');
});


test('selected calls render only after explicit selection and clear after leaving the view at desktop and mobile sizes', {timeout:60_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  for(const viewport of [{width:1280,height:900},{width:390,height:844,isMobile:true,hasTouch:true}]){
    let requests=0;
    const context=await browser.newContext({viewport:{width:viewport.width,height:viewport.height},isMobile:Boolean(viewport.isMobile),hasTouch:Boolean(viewport.hasTouch)});
    t.after(()=>context.close());
    const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
    await traceSelectedCalls(page);
    await installLocalRoutes(page,origin,{selectedCalls:true,onSelectedCallsRequest:()=>requests++});
    await page.goto(origin,{waitUntil:'domcontentloaded'});await waitForMap(page);
    if(viewport.isMobile)await page.getByRole('button',{name:'Filters'}).click();
    assert.equal(requests,0,'the client is idle until the selected-calls view is opened');
    const firstRequest=waitForSelectedCallsRequest(page);
    await page.getByRole('button',{name:'Selected police calls'}).click();
    await firstRequest;
    await page.getByText('Division 41',{exact:true}).waitFor();
    assert.equal(requests,5,'the view uses the bounded metadata/count/group/count/metadata sequence');
    assert.match(await page.locator('#results-caption').textContent(),/not all crime, police activity, or officer presence/i);
    assert.match(await page.locator('#record-list').textContent(),/Open Government Licence.*Ontario/);
    assert.equal(await page.locator('.selected-call-row').count(),3);
    assert.equal(await page.locator('#map').getAttribute('aria-label'),'Map background only; selected calls are not mapped individually');
    assert.equal(await page.locator('#selected-calls-map-note').isVisible(),true);
    await page.getByRole('button',{name:'All establishments'}).click();
    assert.equal(await page.locator('.selected-call-row').count(),0,'leaving the view removes all counts');
    await page.getByRole('button',{name:'Selected police calls'}).click();
    assert.equal(await page.locator('.selected-call-row').count(),0,'a cooldown response cannot reveal old counts');
    assert.equal(requests,5);
    assert.deepEqual(errors,[]);
  }
});

test('selected-call mode aborts on hidden document and never renders stale counts', {timeout:60_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  let requests=0;
  const context=await browser.newContext({viewport:{width:1280,height:900}});
  t.after(()=>context.close());
  const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(()=>{let visibility='visible';Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>visibility});window.__setVisibility=value=>{visibility=value;document.dispatchEvent(new Event('visibilitychange'));};});
  await traceSelectedCalls(page);
  await installLocalRoutes(page,origin,{selectedCalls:true,selectedCallsDelayMs:3_000,onSelectedCallsRequest:()=>requests++});
  await page.goto(origin,{waitUntil:'domcontentloaded'});await waitForMap(page);
  const firstRequest=waitForSelectedCallsRequest(page);
  await page.getByRole('button',{name:'Selected police calls'}).click();
  await firstRequest;
  await page.evaluate(()=>window.__setVisibility('hidden'));
  await page.getByText(/counts are cleared while this view is hidden/i).waitFor();
  assert.equal(await page.locator('.selected-call-row').count(),0);
  await page.waitForTimeout(3_100,'allow the delayed aborted fixture response to settle before checking later request stages');
  assert.equal(requests,1,'abort prevents later request stages');
  await page.evaluate(()=>window.__setVisibility('visible'));
  await page.getByText(/selected-call counts unavailable or stale/i).waitFor();
  assert.equal(await page.locator('.selected-call-row').count(),0);
  assert.equal(requests,1,'cooldown prevents immediate retry after cancellation');
  assert.deepEqual(errors,[]);
});

test('stale upstream selected-call response never renders aggregate values', {timeout:60_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  const context=await browser.newContext({viewport:{width:1280,height:900}});t.after(()=>context.close());
  const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
  await traceSelectedCalls(page);
  await installLocalRoutes(page,origin,{selectedCalls:true,selectedCallsSourceAgeMs:31*60_000});
  await page.goto(origin,{waitUntil:'domcontentloaded'});await waitForMap(page);
  const firstRequest=waitForSelectedCallsRequest(page);
  await page.getByRole('button',{name:'Selected police calls'}).click();
  await firstRequest;
  await page.getByText(/selected-call counts unavailable or stale/i).waitFor();
  assert.equal(await page.locator('.selected-call-row').count(),0);
  assert.deepEqual(errors,[]);
});

test('rendered selected-call counts disappear at the upstream freshness deadline', {timeout:60_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  const context=await browser.newContext({viewport:{width:1280,height:900}});t.after(()=>context.close());
  const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
  await traceSelectedCalls(page);
  await installLocalRoutes(page,origin,{selectedCalls:true,selectedCallsSourceAgeMs:30*60_000-2_000});
  await page.goto(origin,{waitUntil:'domcontentloaded'});await waitForMap(page);
  const firstRequest=waitForSelectedCallsRequest(page);
  await page.getByRole('button',{name:'Selected police calls'}).click();
  await firstRequest;
  await page.getByText('Division 41',{exact:true}).waitFor();
  await page.getByText(/selected-call counts unavailable or stale/i).waitFor({timeout:10_000});
  assert.equal(await page.locator('.selected-call-row').count(),0);
  assert.deepEqual(errors,[]);
});

test('reselecting the active selected-calls tab does not extend the absolute freshness deadline', {timeout:60_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  const context=await browser.newContext({viewport:{width:1280,height:900}});t.after(()=>context.close());
  const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
  await traceSelectedCalls(page);
  await installLocalRoutes(page,origin,{selectedCalls:true,selectedCallsSourceAgeMs:30*60_000-4_000});
  await page.goto(origin,{waitUntil:'domcontentloaded'});await waitForMap(page);
  const tab=page.getByRole('button',{name:'Selected police calls'});
  const firstRequest=waitForSelectedCallsRequest(page);
  await tab.click();await firstRequest;await page.getByText('Division 41',{exact:true}).waitFor();
  await page.waitForTimeout(1_500);
  await tab.click();
  await page.getByText(/selected-call counts unavailable or stale/i).waitFor({timeout:3_200});
  assert.equal(await page.locator('.selected-call-row').count(),0);
  assert.deepEqual(errors,[]);
});

test('resetting during a selected-call request aborts it and prevents late rendering', {timeout:60_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  let requests=0;
  const context=await browser.newContext({viewport:{width:1280,height:900}});t.after(()=>context.close());
  const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
  await traceSelectedCalls(page);
  await installLocalRoutes(page,origin,{selectedCalls:true,selectedCallsDelayMs:3_000,onSelectedCallsRequest:()=>requests++});
  await page.goto(origin,{waitUntil:'domcontentloaded'});await waitForMap(page);
  const firstRequest=waitForSelectedCallsRequest(page);
  await page.getByRole('button',{name:'Selected police calls'}).click();
  await firstRequest;
  await page.getByRole('button',{name:'Reset filters'}).click();
  await page.waitForTimeout(3_200);
  assert.equal(requests,1,'reset aborts the active first stage');
  assert.equal(await page.locator('.selected-call-row').count(),0,'a late response cannot repopulate calls after reset');
  assert.match(await page.locator('#results-title').textContent(),/Recently inspected/);
  assert.deepEqual(errors,[]);
});



test('browse-mode tabs stay fully visible at desktop and narrow widths', {timeout:60_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  const context=await browser.newContext({viewport:{width:1280,height:900}});
  t.after(()=>context.close());
  const page=await context.newPage(),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await installLocalRoutes(page,origin,{});
  await page.goto(origin,{waitUntil:'domcontentloaded'});
  await waitForMap(page);
  for(const width of [1280,1024,960,950,800,390]){
    await page.setViewportSize({width,height:900});
    const filterToggle=page.locator('#toggle-filters');
    if(width<=950&&await filterToggle.isVisible()&&await filterToggle.getAttribute('aria-expanded')!=='true')await filterToggle.click();
    await page.waitForTimeout(50);
    const metrics=await page.locator('.view-tabs').evaluate(tabs=>{
      const container=tabs.getBoundingClientRect();
      return {
        clientWidth:tabs.clientWidth,
        scrollWidth:tabs.scrollWidth,
        buttons:[...tabs.querySelectorAll('.tab')].map(button=>{
          const rect=button.getBoundingClientRect();
          return {
            label:button.textContent.trim(),
            left:rect.left,
            right:rect.right,
            top:rect.top,
            bottom:rect.bottom,
            clientWidth:button.clientWidth,
            scrollWidth:button.scrollWidth,
            clientHeight:button.clientHeight,
            scrollHeight:button.scrollHeight,
            containerLeft:container.left,
            containerRight:container.right
          };
        })
      };
    });
    assert.ok(metrics.scrollWidth<=metrics.clientWidth+1, `mode tab container overflows at ${width}px: ${JSON.stringify(metrics)}`);
    assert.equal(metrics.buttons.length,4);
    for(const button of metrics.buttons){
      assert.ok(button.left>=button.containerLeft-1 && button.right<=button.containerRight+1, `${button.label} clips horizontally at ${width}px`);
      assert.ok(button.scrollWidth<=button.clientWidth+1, `${button.label} text clips at ${width}px`);
      assert.ok(button.scrollHeight<=button.clientHeight+1, `${button.label} clips vertically at ${width}px`);
    }
  }
  assert.deepEqual(errors,[]);
});


function areaOverlayFixture(kind) {
  const dictionary=kind==='ward'?WARDS:NEIGHBOURHOODS;
  return {type:'FeatureCollection',features:Object.entries(dictionary).map(([code,area],i)=>{
    const lon=-79.32+(i%6)*0.025,lat=43.70+Math.floor(i/6)*0.021;
    return {type:'Feature',properties:{AREA_SHORT_CODE:code,AREA_NAME:area.name},
      geometry:{type:'Polygon',coordinates:[[[lon,lat],[lon+.018,lat],[lon+.018,lat+.018],[lon,lat+.018],[lon,lat]]]}};
  })};
}

test('optional ward and neighbourhood overlays share one area filter and preserve camera and state', {timeout:90_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  const context=await browser.newContext({viewport:{width:1280,height:900}});
  t.after(()=>context.close());
  const page=await context.newPage(),errors=[];
  let stage='setup';
  page.on('pageerror',err=>errors.push(stage+': '+(err.stack||err.message)));
  const areaSnapshot={...snapshot,establishments:[
    {...snapshot.establishments[0],neighbourhood:'Ionview',ward:'Scarborough Southwest'},
    {...snapshot.establishments[1],neighbourhood:'Oakridge',ward:'Scarborough Southwest'},
    {...snapshot.establishments[2],neighbourhood:'West Hill',ward:'Scarborough Centre'}
  ]};
  await installLocalRoutes(page,origin,{snapshotBody:areaSnapshot});
  await page.route('**/data/scarborough-wards.geojson',route=>route.fulfill({contentType:'application/geo+json',body:JSON.stringify(areaOverlayFixture('ward'))}));
  await page.route('**/data/scarborough-overlay-neighbourhoods.geojson',route=>route.fulfill({contentType:'application/geo+json',body:JSON.stringify(areaOverlayFixture('neighbourhood'))}));
  stage='initial navigation';
  await page.goto(origin,{waitUntil:'domcontentloaded'});
  await waitForMap(page);
  stage='map ready';
  await page.getByRole('button',{name:'All establishments'}).click();
  assert.equal(await page.locator('#area-selection').isVisible(),false);
  assert.equal(await page.locator('[data-area-overlay="off"]').getAttribute('aria-pressed'),'true');
  assert.equal(await page.evaluate(()=>Boolean(window.__scarbMap.getSource('area-regions'))),false,'no overlay resources rendered by default');
  // Simulate a slow MapLibre style while the official polygon request arrives.
  await page.evaluate(()=>{
    const map=window.__scarbMap;
    window.__overlayOriginalLoaded=map.loaded;
    window.__overlayOriginalStyleLoaded=map.isStyleLoaded;
    map.loaded=()=>false;map.isStyleLoaded=()=>false;
  });
  const wardResponse=page.waitForResponse(response=>response.url().includes('scarborough-wards.geojson'));
  stage='loading ward overlay';
  await page.locator('[data-area-overlay="ward"]').click();
  await wardResponse;
  await page.waitForTimeout(120);
  assert.equal(await page.evaluate(()=>Boolean(window.__scarbMap.getLayer('area-region-fill'))),false,'loading style does not pretend overlay was drawn');
  await page.evaluate(()=>{
    const map=window.__scarbMap;
    map.loaded=window.__overlayOriginalLoaded;
    map.isStyleLoaded=window.__overlayOriginalStyleLoaded;
    map.triggerRepaint();
  });
  stage='ward overlay visible';
  await page.waitForFunction(()=>Boolean(window.__scarbMap.getLayer('area-region-fill')),'overlay eventually appears on readiness');
  await page.locator('#area-choice').selectOption('20');
  await page.waitForFunction(()=>document.querySelectorAll('#record-list .record-item').length===2);
  assert.equal(await page.evaluate(()=>document.activeElement?.id),'area-title','area selection moves keyboard focus to the panel heading');
  assert.match(await page.locator('#area-panel').textContent(),/Parthi Kandavel/);
  assert.equal(await page.locator('#area-panel').evaluate(node=>node.closest('.results')!==null),true,'desktop area details stay with the results column');
  stage='switching from ward to neighbourhood';
  await page.locator('[data-area-overlay="neighbourhood"]').click();
  await page.waitForFunction(()=>document.querySelector('[data-area-overlay="neighbourhood"]').getAttribute('aria-pressed')==='true');
  assert.equal(await page.locator('#record-list .record-item').count(),3,'switching boundary type clears an incompatible ward filter');
  assert.equal(await page.locator('#area-selection').isVisible(),false);
  await page.locator('#area-choice').selectOption('125');
  await page.waitForFunction(()=>document.querySelectorAll('#record-list .record-item').length===1);
  assert.equal(await page.locator('#area-note').isVisible(),false,'successful selection clears the obsolete boundary-switch notice');
  assert.match(await page.locator('#area-selection-name').textContent(),/Ionview/);
  assert.match(await page.locator('#area-panel').textContent(),/Ward 20 and Ward 21/);
  await page.getByRole('button',{name:'Selected police calls'}).click();
  stage='selected calls with area panel';
  await page.waitForFunction(()=>document.querySelector('#area-selection-name')?.textContent.includes('not applied'));
  assert.match(await page.locator('#area-panel').textContent(),/geographic filtering is paused/i);
  await page.getByRole('button',{name:'All establishments'}).click();
  await page.locator('[data-area-overlay="off"]').click();
  stage='hiding overlay';
  assert.equal(await page.locator('#record-list .record-item').count(),1,'hiding outlines retains geographic selection');
  const hidden=await page.evaluate(()=>window.__scarbMap.getLayoutProperty('area-region-fill','visibility'));
  assert.equal(hidden,'none');
  await page.reload({waitUntil:'domcontentloaded'});
  stage='reload with persistent selection';
  await waitForMap(page);
  assert.equal(await page.locator('[data-area-overlay="off"]').getAttribute('aria-pressed'),'true','outlines off on every page load');
  assert.match(await page.locator('#area-selection-name').textContent(),/Ionview/,'persistent area filter has a visible chip');
  assert.equal(await page.evaluate(()=>Boolean(window.__scarbMap.getSource('area-regions'))),false,'restored selection does not silently enable outlines');
  await page.locator('#area-reopen').click();
  const zoomBefore=await page.evaluate(()=>window.__scarbMap.getZoom());
  await page.locator('#area-panel-fit').click();
  await page.waitForFunction(before=>window.__scarbMap.getZoom()>before+0.3,zoomBefore,{timeout:5000});
  assert.equal(await page.locator('[data-area-overlay="off"]').getAttribute('aria-pressed'),'true','fit selected boundary without enabling overlay');
  const centerAtClear=await page.evaluate(()=>window.__scarbMap.getCenter().toArray());
  await page.locator('#area-clear').click();
  stage='clearing selection';
  await page.waitForFunction(()=>document.querySelectorAll('#record-list .record-item').length===3);
  assert.equal(await page.locator('#area-selection').isVisible(),false);
  const centerAfter=await page.evaluate(()=>window.__scarbMap.getCenter().toArray());
  assert.ok(centerAtClear.every((v,i)=>Math.abs(v-centerAfter[i])<.02),'clear preserves map location even after inspecting area geometry');
  assert.deepEqual(errors,[],errors.join('\n\n'));
});

test('map key collapses accessibly and shows only the active dataset symbols', {timeout:90_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  t.after(()=>context.close());
  const page=await context.newPage();
  await installLocalRoutes(page,origin);
  await page.goto(origin,{waitUntil:'domcontentloaded'});
  await waitForMap(page);
  const toggle=page.locator('#map-legend-toggle'),items=page.locator('#map-legend-items');
  assert.equal(await toggle.getAttribute('aria-expanded'),'false','phone map key starts compact');
  await toggle.focus();
  assert.equal(await page.evaluate(()=>document.activeElement?.id),'map-legend-toggle','map key is keyboard focusable');
  await page.keyboard.press('Enter');
  assert.equal(await toggle.getAttribute('aria-expanded'),'true');
  assert.equal(await page.locator('[data-legend-mode="dinesafe"]').first().isVisible(),true);
  const filterToggle=page.locator('#toggle-filters');
  if(await filterToggle.isVisible()&&await filterToggle.getAttribute('aria-expanded')!=='true')await filterToggle.click();
  await page.getByRole('button',{name:'Beach samples'}).click();
  assert.equal(await page.locator('[data-legend-mode="dinesafe"]').first().isVisible(),false);
  assert.equal(await page.locator('[data-legend-mode="beach"]').isVisible(),true);
  assert.equal(await items.getAttribute('hidden'),null,'the key remains available and is filtered to the active source');
});

test('recent cards distinguish City inspection date from Scarb.TO first-observed date', {timeout:90_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  const context=await browser.newContext({viewport:{width:1280,height:900}});
  t.after(()=>context.close());
  const page=await context.newPage();
  await page.clock.install({time:new Date('2026-11-01T12:00:00-05:00')});
  const dated={...snapshot,activity:[{id:'event-a',feed:'dinesafe',kind:'new_inspection',establishment_id:'fixture-a',inspection_date:'2026-10-26',detected_at:'2026-10-31T15:46:44+00:00',status:'Pass',latitude:43.775,longitude:-79.255}]};
  await installLocalRoutes(page,origin,{snapshotBody:dated});
  await page.goto(origin,{waitUntil:'domcontentloaded'});
  await waitForMap(page);
  const row=page.locator('.record-item').first();
  assert.match(await row.textContent(),/Inspection: Oct 26, 2026/);
  assert.match(await row.textContent(),/First observed by Scarb\.TO: Oct 31, 2026/);
});

test('mobile area panel is closeable and the selected-area chip remains usable without the panel', {timeout:90_000}, async t=>{
  const {server,origin}=await startStaticServer();
  const browser=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl']});
  t.after(async()=>{await browser.close();await new Promise(resolveClose=>server.close(resolveClose));});
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2});
  t.after(()=>context.close());
  const page=await context.newPage(),errors=[];
  page.on('pageerror',err=>errors.push(err.message));
  await installLocalRoutes(page,origin,{snapshotBody:{...snapshot,establishments:[
    {...snapshot.establishments[0],neighbourhood:'Ionview',ward:'Scarborough Centre'},
    {...snapshot.establishments[1],neighbourhood:'Oakridge',ward:'Scarborough Southwest'}
  ]}});
  await page.route('**/data/scarborough-overlay-neighbourhoods.geojson',route=>route.fulfill({contentType:'application/geo+json',body:JSON.stringify(areaOverlayFixture('neighbourhood'))}));
  await page.goto(origin,{waitUntil:'domcontentloaded'});
  await waitForMap(page);
  const toggle=page.locator('#toggle-filters');
  if(await toggle.isVisible() && await toggle.getAttribute('aria-expanded')!=='true')await toggle.click();
  await page.getByRole('button',{name:'All establishments'}).click();
  await page.locator('[data-area-overlay="neighbourhood"]').click();
  await page.locator('#area-choice').selectOption('125');
  const panel=page.locator('#area-panel');
  await panel.waitFor({state:'visible'});
  const size=await panel.evaluate(e=>({height:e.getBoundingClientRect().height,width:e.getBoundingClientRect().width}));
  assert.ok(size.width<=390 && size.height<=844*0.60,'mobile bottom sheet fits a phone viewport');
  assert.equal(await page.evaluate(()=>document.activeElement?.id),'area-title','opening the mobile area panel focuses its heading');
  await page.locator('#area-panel-close').click();
  assert.equal(await panel.isVisible(),false);
  assert.equal(await page.evaluate(()=>document.activeElement?.id),'area-reopen','closing the mobile panel returns focus to its reopen control');
  assert.equal(await page.locator('#area-selection').isVisible(),true);
  await page.locator('#area-reopen').click();
  assert.equal(await panel.isVisible(),true);
  await page.locator('#area-panel-expand').click();
  assert.equal(await page.locator('#area-panel-expand').getAttribute('aria-expanded'),'true');
  await page.keyboard.press('Escape');
  assert.equal(await panel.isVisible(),false);
  await page.locator('#area-clear').click();
  assert.equal(await page.locator('#area-selection').isVisible(),false);
  assert.deepEqual(errors,[]);
});
