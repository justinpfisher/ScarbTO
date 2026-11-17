/** Authoring inputs only: catalogue copy + allowlisted qualified public events.
 * No publisher names/settings, browser storage, credentials or location lookups.
 */
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export const canonical = value => JSON.stringify(value, (_, v) => v && typeof v === 'object' && !Array.isArray(v)
  ? Object.fromEntries(Object.keys(v).sort().map(k => [k, v[k]])) : v);
export const sha = value => createHash('sha256').update(canonical(value)).digest('hex');
const requireValue = (ok, message) => { if (!ok) throw new Error(message); };
const IDS = /^[a-z0-9][a-z0-9._:-]{0,159}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const ZONED = /(?:Z|[+-]\d{2}:\d{2})$/;
const OUTCOMES = new Set(['Pass', 'Conditional Pass', 'Closed']);
const SOURCE = 'https://open.toronto.ca/dataset/dinesafe/';
const LICENCE = 'https://open.toronto.ca/open-data-licence/';

export function protect(text) {
  requireValue(typeof text === 'string' && text.length > 0 && !text.includes('{{LOCK:'), 'Invalid public copy');
  const locks = {};
  const pattern = /\{\{[A-Z][A-Z0-9_]*\}\}|https:\/\/[^\s<>]+|Open Government Licence[ –-]+Toronto|Conditional Pass|Scarb\.TO|DineSafe|Scarborough|\bPass\b|\bClosed\b|\d+(?:[.,]\d+)*/g;
  const draft = text.replace(pattern, match => {
    const key = 'VALUE_' + Object.keys(locks).length;
    locks[key] = match;
    return '{{LOCK:' + key + '}}';
  });
  return {draft, locks};
}

const STATIC = Object.freeze({
  'home-title': ['home','editorial'], 'home-intro': ['home','editorial'],
  'home-boundaries': ['source-note','editorial'], 'neighbourhood-intro': ['neighbourhood','editorial'],
  'directory-intro': ['neighbourhood','editorial'], 'community-title': ['community','editorial'],
  'community-intro': ['community','editorial'], 'community-coverage': ['source-note','editorial'],
  'community-core': ['filters','functional'], 'evidence-title': ['evidence','editorial'],
  'evidence-intro': ['evidence','editorial'], 'embed-title': ['embed','editorial'],
  'embed-intro': ['embed','editorial'], 'editor-start': ['community','functional'],
  'missing-pdf-tools': ['error','functional'], 'briefs-title': ['brief','editorial'],
  'briefs-intro': ['brief','editorial']
});

export function catalogueRequests(catalogue, classifications = STATIC) {
  return Object.entries(catalogue).sort(([a],[b]) => a.localeCompare(b, 'en')).map(([key, text]) => {
    requireValue(Object.hasOwn(classifications, key) && IDS.test('static.' + key), 'Classify new copy before sending: ' + key);
    const [surface, kind] = classifications[key];
    return {id: 'static.' + key, surface, kind, ...protect(text),
      evidence: [{id: 'house-copy.' + key, source: 'repo:docs/scarb-voice.mjs#' + key,
        sha256: sha(text), fact: text}], limits: {words: 150, characters: 1500}};
  });
}

function date(value, zoned) {
  requireValue(typeof value === 'string' && (zoned ? ZONED.test(value) : DATE.test(value)), 'Invalid source date');
  requireValue(DATE.test(value.slice(0,10)) && new Date(value.slice(0,10) + 'T12:00:00Z').toISOString().slice(0,10) === value.slice(0,10), 'Invalid calendar date');
  const parsed = new Date(zoned ? value : value + 'T12:00:00Z');
  requireValue(Number.isFinite(parsed.valueOf()), 'Invalid source instant');
  if (!zoned) requireValue(parsed.toISOString().slice(0,10) === value, 'Invalid calendar date');
  return new Intl.DateTimeFormat('en-CA', {timeZone: zoned ? 'America/Toronto' : 'UTC',
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'}).format(parsed);
}

export function eventRequests(release) {
  requireValue(release?.schema_version === 1 && /^[a-f0-9]{64}$/.test(release.id) &&
    release.source_url === SOURCE && release.licence_url === LICENCE && Array.isArray(release.events), 'Use a qualified public release');
  date(release.checked_at, true);
  const seen = new Set();
  return release.events.map(event => {
    requireValue(typeof event.id === 'string' && event.id.length > 0 && !seen.has(event.id), 'Duplicate/missing event');
    seen.add(event.id);
    requireValue(typeof event.name === 'string' && event.name.length > 0 && event.name.length < 1000 &&
      event.feed === 'dinesafe' && typeof event.establishment_id === 'string' && event.establishment_id.length > 0 &&
      OUTCOMES.has(event.status) && ['first_seen','status_changed','new_inspection'].includes(event.kind) &&
      event.source_url === SOURCE && Date.parse(event.detected_at) <= Date.parse(release.checked_at), 'Invalid qualified event');
    const locks = {NAME: event.name, SOURCE: 'DineSafe', SITE: 'Scarb.TO', OUTCOME: event.status, INSPECTION_DATE: date(event.inspection_date, false),
      OBSERVED_DATE: date(event.detected_at, true),
      CAUTION: "This dated inspection result is not a restaurant rating or a guarantee of conditions today. Check the City's record for anything newer."};
    let observation = '{{LOCK:NAME}} has an inspection update.';
    if (event.kind === 'first_seen') {
      locks.NOVELTY = 'Its first appearance in these records is not a confirmed opening.';
      observation = '{{LOCK:NAME}} first appeared in the records. {{LOCK:NOVELTY}}';
    } else if (event.kind === 'status_changed') {
      requireValue(typeof event.previous_status === 'string' && event.previous_status.trim() && event.previous_status.length <= 100 && event.previous_status !== event.status, 'Missing recorded previous outcome');
      locks.PREVIOUS = event.previous_status;
      observation = '{{LOCK:NAME}} has a changed recorded result, previously {{LOCK:PREVIOUS}}.';
    }
    const draft = observation + ' {{LOCK:SOURCE}} recorded {{LOCK:OUTCOME}} for the inspection on {{LOCK:INSPECTION_DATE}}.' +
      ' {{LOCK:SITE}} first recorded this information on {{LOCK:OBSERVED_DATE}}. {{LOCK:CAUTION}}';
    // Hash the immutable public event facts, not the daily refresh time. Unchanged
    // evidence reuses its wording instead of paying to rewrite yesterday's facts.
    const facts = Object.fromEntries(['id','feed','establishment_id','name','kind','status','previous_status','inspection_date','detected_at','source_url']
      .filter(key => event[key] !== undefined).map(key => [key, event[key]]));
    return {id: 'event.' + sha(event.id), surface: 'community', kind: event.status === 'Pass' ? 'editorial' : 'safety',
      draft, locks, evidence: [{id: event.id, source: SOURCE, sha256: sha(facts), fact: canonical(facts)}],
      limits: {words: 150, characters: 1800}};
  });
}

async function main() {
  const args = process.argv.slice(2);
  const take = key => { const at = args.indexOf(key); return at < 0 ? null : args[at + 1]; };
  requireValue(args.every((x,i) => i % 2 || ['--output','--release','--release-sha256'].includes(x)) && args.length % 2 === 0,
    'Use --output FILE and optionally --release FILE --release-sha256 HASH');
  const output = take('--output');
  requireValue(output && !resolve(output).split(/[\\/]/).includes('docs'), 'Write requests outside public docs');
  const {SCARB_COPY} = await import('../docs/scarb-voice.mjs');
  let packets = catalogueRequests(SCARB_COPY);
  const file = take('--release'), expected = take('--release-sha256');
  requireValue(Boolean(file) === Boolean(expected), 'Supply release and independently qualified byte hash together');
  if (file) {
    const bytes = readFileSync(file);
    requireValue(createHash('sha256').update(bytes).digest('hex') === expected, 'Qualified release byte hash differs');
    packets = packets.concat(eventRequests(JSON.parse(bytes)));
  }
  writeFileSync(output, canonical(packets), {encoding: 'utf8', flag: 'wx'});
  console.log('Prepared ' + packets.length + ' public-copy requests. No model called; no publication changed.');
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
