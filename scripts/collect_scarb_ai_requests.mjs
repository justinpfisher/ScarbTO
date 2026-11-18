/** Authoring inputs only: catalogue copy + allowlisted qualified public events.
 * No publisher names/settings, browser storage, credentials or location lookups.
 */
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {directoryEvidence} from './scarb_directory_evidence.mjs';

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
  const prefix=text.match(/^\s*/)[0],suffix=text.slice(prefix.length).match(/\s*$/)[0];
  const content=text.slice(prefix.length,text.length-suffix.length);
  const pattern = /\{\{[A-Z][A-Z0-9_]*\}\}|https:\/\/[^\s<>]+|Open Government Licence[ –-]+(?:Toronto|Ontario)|Conditional Pass|Scarb\.TO|DineSafe|Scarborough|\bPass\b|\bClosed\b|\d+(?:[.,]\d+)*/g;
  let draft = content.replace(pattern, match => {
    const key = 'VALUE_' + Object.keys(locks).length;
    locks[key] = match;
    return '{{LOCK:' + key + '}}';
  });
  if(prefix){locks.LAYOUT_PREFIX=prefix;draft='{{LOCK:LAYOUT_PREFIX}}'+draft;}
  if(suffix){locks.LAYOUT_SUFFIX=suffix;draft+='{{LOCK:LAYOUT_SUFFIX}}';}
  return {draft, locks};
}

const STATIC = Object.freeze(JSON.parse(readFileSync(new URL('../config/scarb-copy-classifications.json',import.meta.url),'utf8')));
const FINDING_SOURCE=Object.freeze(JSON.parse(readFileSync(new URL('../config/scarb-finding-source-drafts.json',import.meta.url),'utf8')));

export function catalogueRequests(catalogue, classifications = STATIC) {
  return Object.entries(catalogue).sort(([a],[b]) => a.localeCompare(b, 'en')).map(([key, text]) => {
    requireValue(Object.hasOwn(classifications, key) && IDS.test('static.' + key), 'Classify new copy before sending: ' + key);
    requireValue(Array.isArray(classifications[key]) && classifications[key].length === 2, "Invalid copy classification: " + key);
    const [surface, kind] = classifications[key];
    return {id: 'static.' + key, surface, kind, ...protect(text),
      evidence: [{id: 'house-copy.' + key, source: 'repo:docs/scarb-voice.mjs#' + key,
        sha256: sha(text), fact: text},...(key==='directory-intro'?directoryEvidence():[]),...(FINDING_SOURCE[key]?[{id:'official-finding.'+key,source:SOURCE,sha256:sha(FINDING_SOURCE[key]),fact:FINDING_SOURCE[key]}]:[])], limits: {words: 150, characters: 1500}};
  });
}


/** Offline input constructor only; deliberately not enrolled in main/manifest/publication.
 * A distinct evidence namespace preserves all existing house-copy and held identities.
 */
export function retainedIonviewRequest(sourceBytes) {
  const pins = {"research/phase1b-csi/fixtures/official-source-contract/scarbto-neighbourhood158-source-contract-2026-10-27.json":"0f16bf16cde47f382f21003050a978251f71c258581746d64c9a8c9f5ae8564e","docs/area-selection.mjs":["7f6ac42ebe9c174d28f02d97244267b2baa9efd6f538bd98cecb4d57bcc18313","b1616d798b2d9867e9e37cd880a5d2cbd3e12398312afa4b5ca86bdadebc9e33"],"docs/community-data/releases/887085d7e735b7e9f8484013abe2fa0193ae812f421cc9bca3b16f17003e4655.json":"2c6e46f138d569d5a4033330a2c55cdc50dc1d4228dee5f8706c59b663a8e923","docs/community-data/boundaries/9412f1c2737d7b0165867c7e6a38dd5e7549b834d0184cb9923c4241a85dd3f7.json":"9412f1c2737d7b0165867c7e6a38dd5e7549b834d0184cb9923c4241a85dd3f7","docs/data/scarborough-neighbourhoods.geojson":"f649e4df4c6033081ba4dcd40a610ee275e80891e6fc695ec3d4fdda1772d288"};
  requireValue(sourceBytes && Object.keys(sourceBytes).sort().join('|')===Object.keys(pins).sort().join('|'), 'Exact retained geography source set required');
  // The code mapping has two exact byte pins: Git LF and its Windows CRLF checkout.
  // Source-data artifacts remain single-pin; no arbitrary normalization is accepted.
  for (const [path,hash] of Object.entries(pins)) {
    requireValue(Buffer.isBuffer(sourceBytes[path]) && [hash].flat().includes(createHash('sha256').update(sourceBytes[path]).digest('hex')),'Retained geography evidence changed: '+path);
  }
  // Exact byte identities bind the previously reconciled source projection, not
  // an arbitrary caller-supplied geographic claim or a replacement scientific review.
  const packet = {"draft":"Here is a map detail worth following: {{LOCK:NAME}} overlaps wards {{LOCK:WARD_A}} and {{LOCK:WARD_B}}. {{LOCK:LIMIT}}","evidence":[{"fact":"{\"basis\":\"retained City-source native EPSG:2952 intersection contract; each listed overlap exceeds existing one-percent display threshold\",\"city_code\":\"125\",\"contract_created_at\":\"2026-10-27T17:56:20.174497+00:00\",\"coverage_note\":\"Only records inside the qualified six Scarborough wards are included. City neighbourhoods can cross those wards; this is not necessarily a whole-neighbourhood total.\",\"licence\":\"https://open.toronto.ca/open-data-licence/\",\"name\":\"Ionview\",\"neighbourhood_source\":\"https://open.toronto.ca/dataset/neighbourhoods/\",\"relation\":\"positive_area_overlap\",\"ward_codes\":[\"20\",\"21\"]}","id":"retained-geography.125","sha256":"c0a1d07ba470efdecdfbe7fde3fd6b4ed531d002699836dfcb1f9a716f00b2cd","source":"repo:research/phase1b-csi/fixtures/official-source-contract/scarbto-neighbourhood158-source-contract-2026-10-27.json#spatial_crosswalk/125"}],"id":"geography.home-ionview-boundaries","kind":"editorial","limits":{"characters":1800,"words":150},"locks":{"LIMIT":"Only records inside the qualified six Scarborough wards are included. City neighbourhoods can cross those wards; this is not necessarily a whole-neighbourhood total.","NAME":"Ionview","WARD_A":"20","WARD_B":"21"},"surface":"home"};
  return packet;
}

export function pythonCatalogueRequests() {
  const drafts=JSON.parse(readFileSync(new URL('../config/scarb-python-copy-drafts.json',import.meta.url),'utf8'));
  const classifications=JSON.parse(readFileSync(new URL('../config/scarb-python-copy-classifications.json',import.meta.url),'utf8'));
  return catalogueRequests(drafts,classifications).map(packet=>({...packet,id:packet.id.replace(/^static\./,'python.'),evidence:packet.evidence.map(e=>({...e,id:e.id.replace('house-copy.','python-copy.'),source:e.source.replace('repo:docs/scarb-voice.mjs#','repo:config/scarb-python-copy-drafts.json#')}))}));
}
export function shellCatalogueRequests() {
  const drafts=JSON.parse(readFileSync(new URL('../config/scarb-shell-copy-drafts.json',import.meta.url),'utf8'));
  const classifications=JSON.parse(readFileSync(new URL('../config/scarb-shell-copy-classifications.json',import.meta.url),'utf8'));
  return catalogueRequests(drafts,classifications).map(packet=>({...packet,id:packet.id.replace(/^static\./,'shell.'),evidence:packet.evidence.map(e=>({...e,id:e.id.replace('house-copy.','shell-copy.'),source:e.source.replace('repo:docs/scarb-voice.mjs#','repo:config/scarb-shell-copy-drafts.json#')}))}));
}
export function requestManifest(packets) {
  const result={};for(const packet of packets){requireValue(!Object.hasOwn(result,packet.id),'Duplicate current request');result[packet.id]=sha(packet);}return result;
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
  let packets = [...catalogueRequests(SCARB_COPY),...pythonCatalogueRequests(),...shellCatalogueRequests()];
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
