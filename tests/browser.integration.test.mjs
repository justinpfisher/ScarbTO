import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {mkdir, readFile, stat} from 'node:fs/promises';
import {extname, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const root = resolve(fileURLToPath(new URL('../docs/', import.meta.url)));
const maplibreRoot = resolve(fileURLToPath(new URL('../node_modules/maplibre-gl/dist/', import.meta.url)));
const outputDir = resolve(fileURLToPath(new URL('../test-results/beach-browser/', import.meta.url)));
const mime = new Map([
  ['.html', 'text/html; charset=utf-8'], ['.mjs', 'text/javascript; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'], ['.css', 'text/css; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'], ['.csv', 'text/csv; charset=utf-8'],
  ['.geojson', 'application/geo+json; charset=utf-8'],
]);

const snapshot = {
  schema_version: 1,
  ready: true,
  published_at: '2026-10-27T12:00:00Z',
  establishments: [
    {id: 'fixture-a', establishment_id: 'fixture-a', name: 'Fixture Caf�', address: '10 Test Road', status: 'Pass', inspection_date: '2026-10-26', longitude: -79.255, latitude: 43.775, neighbourhood: 'Agincourt'},
    {id: 'fixture-b', establishment_id: 'fixture-b', name: 'Fixture Bakery', address: '20 Sample Avenue', status: 'Conditional Pass', inspection_date: '2026-10-25', longitude: -79.29, latitude: 43.73, neighbourhood: 'Woburn'},
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

async function installLocalRoutes(page, origin, {snapshotStatus = 200, snapshotBody = snapshot, beachStatus = 200, beachDelayMs = 0} = {}) {
  let beachResponseSent = false;
  await page.route('**/*', async route => {
    const url = route.request().url();
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
    if (url === 'https://cdn.jsdelivr.net/npm/maplibre-gl@5.24.0/dist/maplibre-gl.js') {
      await route.fulfill({path: resolve(maplibreRoot, 'maplibre-gl.js'), contentType: 'text/javascript'});
      return;
    }
    if (url === 'https://cdn.jsdelivr.net/npm/maplibre-gl@5.24.0/dist/maplibre-gl.css') {
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
  if (mobile) await page.getByRole('button', {name: 'Filters'}).click();
  await page.getByRole('button', {name: 'All establishments'}).click();
  await page.getByRole('button', {name: 'Fixture Caf�'}).waitFor();
  assert.equal(await page.getByRole('button', {name: 'Fixture Bakery'}).count(), 1, `${name}: both synthetic records are listed`);

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
    await page.setViewportSize({width, height});
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
  await beachSurvivesDineSafeError.page.waitForFunction(() => !window.__scarbMap.querySourceFeatures('places').some(feature => feature.properties.id === 'beach:10'));
  assert.deepEqual(beachSurvivesDineSafeError.pageErrors, []);

  const dineSafeSurvivesBeachError = await openScenario(browser, origin, {beachStatus: 503}, {initialMode: 'all'});
  t.after(() => dineSafeSurvivesBeachError.context.close());
  await dineSafeSurvivesBeachError.page.getByRole('button', {name: 'Fixture Caf�'}).waitFor();
  await dineSafeSurvivesBeachError.page.getByRole('button', {name: 'Fixture Bakery'}).waitFor();
  assert.deepEqual(dineSafeSurvivesBeachError.pageErrors, []);

  const readyFalse = {schema_version: 1, ready: false, published_at: null, establishments: [], activity: []};
  const switchingView = await openScenario(browser, origin, {snapshotBody: readyFalse}, {initialMode: 'beach'});
  t.after(() => switchingView.context.close());
  await switchingView.page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor();
  await switchingView.page.waitForFunction(() => window.__scarbMap.querySourceFeatures('places').some(feature => feature.properties.id === 'beach:10'));
  await switchingView.page.getByRole('button', {name: 'All establishments'}).click();
  await switchingView.page.getByText(/No validated DineSafe snapshot has been published/).waitFor();
  await switchingView.page.waitForFunction(() => !window.__scarbMap.querySourceFeatures('places').some(feature => feature.properties.id === 'beach:10'));
  assert.deepEqual(switchingView.pageErrors, []);

  const delayedBeach = await openScenario(browser, origin, {beachDelayMs: 5_000}, {initialMode: 'all'});
  t.after(() => delayedBeach.context.close());
  await delayedBeach.page.getByRole('button', {name: 'Fixture Caf�'}).waitFor({timeout: 2_000});
  assert.equal(delayedBeach.isBeachResponseSent(), false, 'DineSafe view is available while the independent beach request is still pending');
  await delayedBeach.page.getByRole('button', {name: 'Beach samples'}).click();
  await delayedBeach.page.locator('#results-title').filter({hasText: "Bluffer's Beach Park"}).waitFor({timeout: 8_000});
  assert.equal(delayedBeach.isBeachResponseSent(), true);
  assert.deepEqual(delayedBeach.pageErrors, []);
});

