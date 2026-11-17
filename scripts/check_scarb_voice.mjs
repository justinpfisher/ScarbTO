/**
 * Offline Scarb voice publication gate. Rejects drifted registered UI text,
 * missing visible wordmarks and known bypass language. This is not an
 * independent evidence check or a substitute for rendered acceptance.
 */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {SCARB_COPY, staticCopy} from '../docs/scarb-voice.mjs';

const ROOT = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const SURFACES = Object.freeze({
  'docs/index.html': ['home-title', 'home-intro', 'home-boundaries'],
  'docs/briefs/index.html': ['briefs-title', 'briefs-intro'],
  'docs/neighbourhood-page.template.html': ['neighbourhood-intro'],
  'docs/neighbourhoods/index.html': ['directory-intro'],
  'docs/community/index.html': ['community-title', 'community-intro', 'community-coverage', 'community-core'],
  'docs/community/evidence/index.html': ['evidence-title', 'evidence-intro'],
  'docs/embed/index.html': ['embed-title', 'embed-intro']
});

export function inspectMarkup(filename, markup) {
  const required = SURFACES[filename] || [];
  const found = new Map();
  const pattern = /<([a-z][a-z0-9-]*)\b([^>]*\bdata-scarb-voice="([^"]+)"[^>]*)>([^<]*)<\/\1>/g;
  for (const match of markup.matchAll(pattern)) {
    const key = match[3];
    if (found.has(key)) throw new Error('Duplicate Scarb voice key ' + key + ' in ' + filename);
    if (!Object.prototype.hasOwnProperty.call(SCARB_COPY, key)) throw new Error('Unregistered Scarb voice key ' + key);
    const fields = key === 'directory-intro' ? {COUNT: 30} :
      key === 'neighbourhood-intro' ? {NAME: '{{NAME}}'} : {};
    if (match[4] !== staticCopy(key, fields)) throw new Error('Scarb voice drift for ' + key + ' in ' + filename);
    found.set(key, true);
  }
  for (const key of required) {
    if (!found.has(key)) throw new Error('Required Scarb voice entry missing: ' + key + ' in ' + filename);
  }
  return found.size;
}

export function checkVoiceGateway(read = path => readFileSync(resolve(ROOT, path), 'utf8')) {
  let count = 0;
  for (const path of Object.keys(SURFACES)) count += inspectMarkup(path, read(path));
  const sourcePaths = [
    'docs/community-editor.mjs', 'docs/community-publishing.mjs',
    'docs/community-embed.mjs', 'docs/community-exports.mjs',
    'docs/neighbourhood-page.template.html', 'docs/community/index.html'
  ];
  const stale = [
    /previous-edition marker/i, /chosen physical page/i,
    /create a community publication from qualified records/i,
    /qualified six Scarborough wards/i, /<legend>Core coverage<\/legend>/i,
    /no new updates in the qualified records/i
  ];
  for (const path of sourcePaths) {
    const source = read(path);
    for (const phrase of stale) {
      if (phrase.test(source)) throw new Error('Untranslated house copy in ' + path + ': ' + phrase);
    }
  }
  for (const path of ['docs/community-publishing.mjs', 'docs/community-editor.mjs', 'docs/community-embed.mjs']) {
    if (!read(path).includes("from './scarb-voice.mjs'")) {
      throw new Error('Community publisher bypasses the voice gateway: ' + path);
    }
  }
  for (const path of Object.keys(SURFACES)) {
    const content = read(path);
    if (!/<a\b[^>]*href="(?:\/|https:\/\/scarb\.to\/)"[^>]*aria-label="Scarb\.TO home"/.test(content) ||
        !/<span\b[^>]*class="(?:brand-name|scarb-brand-title)"[^>]*>Scarb\.TO<\/span>/.test(content)) {
      throw new Error('Visible Scarb.TO wordmark/home link missing from ' + path);
    }
  }
  return count;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const count = checkVoiceGateway();
    console.log('Scarb voice gateway checked ' + count + ' approved copy entries and required identity surfaces.');
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
