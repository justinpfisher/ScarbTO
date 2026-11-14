import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {extname, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const root = resolve(fileURLToPath(new URL('../docs/', import.meta.url)));
const mime = new Map([
  ['.html', 'text/html; charset=utf-8'], ['.css', 'text/css; charset=utf-8'],
  ['.svg', 'image/svg+xml'],
]);

async function startServer() {
  const server = createServer(async (request, response) => {
    const url = new URL(request.url, 'http://127.0.0.1');
    const relative = url.pathname === '/' ? 'index.html' : decodeURIComponent(url.pathname).replace(/^\/+/, '');
    const file = resolve(root, relative);
    if (file !== root && !file.startsWith(root + sep)) {
      response.writeHead(403).end();
      return;
    }
    try {
      const body = await readFile(file);
      response.writeHead(200, {'content-type': mime.get(extname(file)) || 'application/octet-stream'}).end(body);
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

async function pageAt(browser, origin, path, width) {
  const page = await browser.newPage({viewport: {width, height: 900}});
  await page.route('**/*', route => route.request().url().startsWith(origin)
    ? route.continue()
    : route.abort('blockedbyclient'));
  await page.goto(origin + path, {waitUntil: 'domcontentloaded'});
  return page;
}

test('home branding selects the approved asset at and above 420px', async () => {
  const {server, origin} = await startServer();
  const browser = await chromium.launch({headless: true});
  try {
    for (const [width, expected] of [[420, 'scarbto-mark.svg'], [421, 'scarbto-connected.svg']]) {
      const page = await pageAt(browser, origin, '/', width);
      const brand = await page.locator('.identity').evaluate(async link => {
        const image = link.querySelector('img');
        await image.decode();
        return {
          name: link.getAttribute('aria-label'),
          alt: image.getAttribute('alt'),
          href: link.getAttribute('href'),
          source: new URL(image.currentSrc).pathname.split('/').at(-1),
          naturalWidth: image.naturalWidth,
        };
      });
      assert.equal(brand.name, 'Scarb.TO home');
      assert.equal(brand.alt, '');
      assert.equal(brand.href, '/');
      assert.equal(brand.source, expected);
      assert.ok(brand.naturalWidth > 0);
      const taglineDisplay = await page.locator('.intro-tagline').evaluate(el => getComputedStyle(el).display);
      assert.equal(taglineDisplay === 'none', width > 420);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      assert.equal(overflow, false, `horizontal overflow at ${width}px`);
      await page.close();
    }
  } finally {
    await browser.close();
    await new Promise(resolveClose => server.close(resolveClose));
  }
});

test('neighbourhood sharing page keeps branding accessible and print controls hidden', async () => {
  const {server, origin} = await startServer();
  const browser = await chromium.launch({headless: true});
  try {
    for (const [width, expected] of [[420, 'scarbto-mark-light.svg'], [421, 'scarbto-connected-light.svg']]) {
      const page = await pageAt(browser, origin, '/west-rouge/index.html', width);
      const brand = await page.locator('.brand').evaluate(async link => {
        const image = link.querySelector('img');
        await image.decode();
        return {
          name: link.getAttribute('aria-label'),
          alt: image.getAttribute('alt'),
          source: new URL(image.currentSrc).pathname.split('/').at(-1),
          width: image.naturalWidth,
        };
      });
      assert.equal(brand.name, 'Scarb.TO home');
      assert.equal(brand.alt, '');
      assert.equal(brand.source, expected);
      assert.ok(brand.width > 0);
      const tagline = await page.locator('.brand-tagline').evaluate(el => getComputedStyle(el).display);
      assert.equal(tagline === 'none', width > 420);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      assert.equal(overflow, false, `horizontal overflow at ${width}px`);
      await page.emulateMedia({media: 'print'});
      assert.equal(await page.locator('.print-brand').evaluate(el => getComputedStyle(el).display), 'block');
      assert.equal(await page.locator('#share-page').evaluate(el => getComputedStyle(el).display), 'none');
      assert.equal(await page.locator('#print-page').evaluate(el => getComputedStyle(el).display), 'none');
      assert.equal(await page.locator('.site-header').evaluate(el => getComputedStyle(el).display), 'flex');
      const printLogoWidth = await page.locator('.print-brand img').evaluate(async img => {
        await img.decode();
        return img.naturalWidth;
      });
      assert.ok(printLogoWidth > 0);
      await page.close();
    }
  } finally {
    await browser.close();
    await new Promise(resolveClose => server.close(resolveClose));
  }
});
