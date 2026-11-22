import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {materializeShell} from './build_scarb_static.mjs';
import {buildPageFiles, normalizeGeneratedText} from './build_neighbourhood_pages.mjs';
import {createScarbAiResolver} from '../docs/scarb-ai-copy.mjs';
import {currentEventPackets,parseDataModule} from './scarb_current_events.mjs';
/**
 * Offline Scarb voice publication gate. Rejects drifted registered UI text,
 * missing visible wordmarks and known bypass language. This is not an
 * independent evidence check or a substitute for rendered acceptance.
 */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {SCARB_COPY, staticCopy} from '../docs/scarb-voice.mjs';
import {assertAcceptedCopyReady} from '../docs/scarb-current-copy.mjs';
import catalogue from '../docs/scarb-copy-inputs.mjs';
import expectedManifest from '../docs/scarb-copy-manifest.mjs';
import {catalogueRequests,pythonCatalogueRequests,shellCatalogueRequests,requestManifest} from './collect_scarb_ai_requests.mjs';

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
    if (match[4] !== staticCopy(key, fields).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")) throw new Error('Scarb voice drift for ' + key + ' in ' + filename);
    found.set(key, true);
  }
  for (const key of required) {
    if (!found.has(key)) throw new Error('Required Scarb voice entry missing: ' + key + ' in ' + filename);
  }
  return found.size;
}


/** Complete authored text/accessible-label inventory, including unmarked additions.
 * This is reviewed copy, not a whole-file hash: markup/layout changes remain independent.
 * Source-derived values belong to separately tested composers, never this static inventory.
 */
export function markupInventory(markup) {
  const source=markup.replace(/<!--[\s\S]*?-->|<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi,'');
  const text=[],attributes=[...markup.matchAll(/<script\b[^>]*>[\s\S]*?<\/script>/gi)].map(match=>'script:'+match[0].replaceAll('\r\n','\n'));
  for(const style of markup.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi))for(const match of style[1].matchAll(/\bcontent\s*:\s*([^;}]+)/gi))attributes.push('css-content:'+match[1].trim());
  const tokens=/<![^>]*>|<\/?([a-z][a-z0-9:-]*)\b(?:[^>"']|"[^"]*"|'[^']*')*>|([^<]+)/gi;
  let end=0;
  for(const token of source.matchAll(tokens)) {
    if(source.slice(end,token.index).trim())throw new Error('Unsupported authored HTML syntax');
    end=token.index+token[0].length;
    if(token[2]) {const value=token[2].trim().replace(/\s+/g,' ');if(value)text.push(value);continue;}
    if(!token[1] || /^<\//.test(token[0]))continue;
    const tag=token[1].toLowerCase(), attrs=new Map();
    const body=token[0].slice(token[0].indexOf(token[1])+token[1].length,-1);
    const pattern=/\s+([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
    let offset=0;
    for(const match of body.matchAll(pattern)) {
      if(body.slice(offset,match.index).trim())throw new Error('Unsupported authored attribute syntax');
      offset=match.index+match[0].length;
      const name=match[1].toLowerCase(),value=match[2]??match[3]??match[4]??'';
      if(attrs.has(name))throw new Error('Duplicate authored attribute');
      if(name==='srcdoc')throw new Error('Embedded authored HTML requires its own reviewed producer');
      attrs.set(name,value);
      if(['aria-label','aria-description','alt','title','placeholder'].includes(name) || (tag==='input' && name==='value'))attributes.push(name+':'+value);
    }
    if(body.slice(offset).trim().replace(/^\/$/,''))throw new Error('Unsupported authored attribute syntax');
    if(tag==='meta' && ['description','og:title','og:description','twitter:title','twitter:description'].includes(attrs.get('name')??attrs.get('property')))attributes.push('meta:'+(attrs.get('content')??''));
  }
  if(source.slice(end).trim())throw new Error('Unsupported trailing authored HTML');
  return {text,attributes};
}
export function inspectAllMarkup(filename, markup, approved) {
  const inventory=markupInventory(markup);
  if(!approved || JSON.stringify(inventory)!==JSON.stringify(approved))throw new Error('Unreviewed public copy in '+filename);
  return inventory.text.length+inventory.attributes.length;
}

export function weeklyIndexShell(markup, manifest) {
  const date=value=>{
    if(!/^\d{4}-\d{2}-\d{2}$/.test(value))throw new Error('Invalid archive period');
    const parsed=new Date(value+'T12:00:00Z');
    if(!Number.isFinite(parsed.valueOf()) || parsed.toISOString().slice(0,10)!==value)throw new Error('Invalid archive period');
    return new Intl.DateTimeFormat('en-CA',{month:'long',day:'numeric',year:'numeric',timeZone:'UTC'}).format(parsed);
  };
  if(manifest.schema_version!==1 || !Array.isArray(manifest.editions))throw new Error('Invalid archive registry');
  const entries=[...manifest.editions].sort((a,b)=>b.period_start.localeCompare(a.period_start));
  const expected=entries.map(item=>{
    if(item.path!==`briefs/${item.period_start}/` || !Number.isSafeInteger(item.event_count) || item.event_count<1 || !Number.isSafeInteger(item.revision) || item.revision<1)throw new Error('Invalid archive identity/count');
    return `<li><a href="/${item.path}">Food inspection updates ${date(item.period_start)}–${date(item.period_end)}</a> <span>(${item.event_count} recorded updates; revision ${item.revision})</span></li>`;
  }).join('');
  const lists=[...markup.matchAll(/<ul>([\s\S]*?)<\/ul>/g)];
  if(lists.length!==1 || lists[0][1]!==expected)throw new Error('Weekly archive copy differs from registered evidence');
  let shell=markup.replace(lists[0][0],'<ul>ARCHIVE_ROWS</ul>');
  // This is a copy contract, not a second clock-driven edition decision.
  // Normal generation owns its explicit as_of; code_only keeps the old index.
  // Validate any existing quiet-period sentence without inventing a newer one.
  const quietPattern=/<p>I have no DineSafe updates to share for ([A-Za-z]+ \d{1,2}, \d{4})\u2013([A-Za-z]+ \d{1,2}, \d{4})\.<\/p>/g;
  const quiet=[...shell.matchAll(quietPattern)];
  if(quiet.length>1)throw new Error('Duplicate Quiet-period copy');
  if(quiet.length) {
    const [whole,startText,endText]=quiet[0];
    const start=new Date(startText+' 12:00:00 GMT'),end=new Date(endText+' 12:00:00 GMT');
    if(!Number.isFinite(start.valueOf()) || !Number.isFinite(end.valueOf()) || start.getUTCDay()!==1 || end-start!==6*86400000 || date(start.toISOString().slice(0,10))!==startText || date(end.toISOString().slice(0,10))!==endText || entries.some(item=>item.period_start===start.toISOString().slice(0,10)))throw new Error('Invalid Quiet-period copy');
    shell=shell.replace(whole,'');
  }
  return shell;
}

export function isRetainedIndex(read) {
  // The existing committed release input is durable previous evidence. Compare
  // bytes, not today's voice catalogue or wall clock. This also works after a
  // later normal release persists a newer index and its archive manifest.
  const pending=spawnSync('git',['rev-parse','--verify','MERGE_HEAD'],{cwd:ROOT,encoding:'utf8',windowsHide:true});
  if(pending.error)throw pending.error;
  const revision=pending.status===0?pending.stdout.trim():'HEAD';
  const committed=path=>{
    const result=spawnSync('git',['show',revision+':'+path],{cwd:ROOT,encoding:'utf8',windowsHide:true});
    if(result.error || result.status!==0)throw Error('Committed archive evidence unavailable');
    return result.stdout.replaceAll('\r\n','\n');
  };
  const manifest=JSON.parse(committed('docs/briefs/editions.json'));
  if(manifest.schema_version!==1 || !Array.isArray(manifest.editions))throw Error('Invalid committed archive evidence');
  const paths=['docs/briefs/index.html','docs/briefs/editions.json',...manifest.editions.map(entry=>{
    if(!/^briefs\/\d{4}-\d{2}-\d{2}\/$/.test(entry.path))throw Error('Invalid committed edition path');
    return 'docs/'+entry.path+'index.html';
  })];
  return paths.every(path=>read(path).replaceAll('\r\n','\n')===committed(path));
}

export function checkVoiceGateway(read = path => readFileSync(resolve(ROOT, path), 'utf8'), {publishing=false}={}) {
  const bindings=JSON.parse(read('docs/scarb-event-inputs.json'));
  if(JSON.stringify(bindings)!==JSON.stringify(parseDataModule(read('docs/scarb-event-inputs.mjs'))))throw Error('Event input modules differ');
  const eventSource=JSON.parse(read('docs/scarb-event-source.json').replace(/^\uFEFF/,''));
  let eventPackets=[];
  if(Object.keys(bindings).length) {
    if(!eventSource || !/^[a-f0-9]{64}$/.test(eventSource.release_id) || !/^[a-f0-9]{64}$/.test(eventSource.sha256))throw Error('Missing retained qualified event evidence');
    const raw=read('docs/community-data/releases/'+eventSource.release_id+'.json').replaceAll('\r\n','\n');
    if(createHash('sha256').update(raw).digest('hex')!==eventSource.sha256)throw Error('Retained event evidence bytes changed');
    eventPackets=currentEventPackets(JSON.parse(raw),bindings);
  } else if(eventSource!==null)throw Error('Unexpected event source without accepted bindings');
  const current=requestManifest([...catalogueRequests(SCARB_COPY),...pythonCatalogueRequests(),...shellCatalogueRequests(),...eventPackets]);
  if(JSON.stringify(current)!==JSON.stringify(expectedManifest) || JSON.stringify(current)!==JSON.stringify(JSON.parse(read('docs/scarb-copy-manifest.json'))))throw new Error('Current source request manifest is stale');
  if(JSON.stringify(catalogue)!==JSON.stringify(JSON.parse(read('docs/scarb-copy-inputs.json'))))throw new Error('Browser and Python accepted inputs differ');
  if(publishing)assertAcceptedCopyReady();
  const retainedIndex=isRetainedIndex(read);
  const verifyGeneratedIndex=(historical=false)=>{
    const result=spawnSync('python',['scripts/check_scarb_brief_index.py',...(historical?['--retained']:[])],{cwd:ROOT,encoding:'utf8',windowsHide:true});
    if(result.error || result.status!==0)throw Error('Generated weekly index must match accepted renderer and issued archive evidence');
  };
  if(!retainedIndex)verifyGeneratedIndex();
  let count = 0;
  const shells=JSON.parse(read('config/scarb-static-shells.json'));
  // Every authored shell text/attribute must be covered, even after acceptance.
  // Strip only declared slots, then use the independent HTML inventory to catch
  // a newly inserted unmarked phrase outside those spans.
  for(const [path,record] of Object.entries(shells)) {
    let residual=record.source;
    for(const slot of [...record.slots].reverse())residual=residual.slice(0,slot.start)+residual.slice(slot.end);
    const inventory=markupInventory(residual);
    if(inventory.text.some(text=>/[A-Za-z]/.test(text)) || inventory.attributes.some(value=>!value.startsWith('script:')&&!value.startsWith('css-content:')&&/[A-Za-z]/.test(value.slice(value.indexOf(':')+1))))throw Error('Unregistered shell text outside accepted slots: '+path);
    const preserved=value=>value.attributes.filter(x=>x.startsWith('script:')||x.startsWith('css-content:'));
    const original=JSON.parse(read('scripts/scarb-reviewed-markup.json'))[path];
    if(JSON.stringify(preserved(inventory))!==JSON.stringify(preserved(original)))throw Error('Unreviewed inline shell producer: '+path);
  }
  const accepted=catalogue===null?null:createScarbAiResolver(catalogue,current);
  if(accepted)for(const [path,record] of Object.entries(shells)) {
    if(read(path).replaceAll('\r\n','\n')!==materializeShell(record,accepted))throw Error('Published shell differs from accepted materialization: '+path);
  }
  if(!accepted) {
    const path='docs/neighbourhoods/index.html';
    const directory=buildPageFiles().get(path);
    if(normalizeGeneratedText(read(path))!==directory)throw Error('Directory differs from its qualified generator');
  }
  const reviewed=JSON.parse(read('scripts/scarb-reviewed-markup.json'));
  for (const path of Object.keys(SURFACES)) {
    if(path==='docs/briefs/index.html' && !retainedIndex)continue;
    const markup=path==='docs/briefs/index.html' ? weeklyIndexShell(read(path),JSON.parse(read('docs/briefs/editions.json'))) : read(path);
    if(!accepted || !Object.hasOwn(shells,path)) {
      try {inspectAllMarkup(path,markup,reviewed[path]);}
      catch(error) {if(path==='docs/briefs/index.html' && retainedIndex)verifyGeneratedIndex(true);else throw error;}
    }
  }
  for (const path of Object.keys(SURFACES)) {
    // Frozen historical prose is authenticated by its retained exact bytes,
    // not falsely reinterpreted as today's accepted catalogue output.
    if(path==='docs/briefs/index.html')continue;
    count += inspectMarkup(path, read(path));
  }
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
    const hasHomeLink=/<a\b[^>]*href="(?:\/|https:\/\/scarb\.to\/)"[^>]*aria-label="Scarb\.TO home"/.test(content);
    const hasWordmark=/<span\b[^>]*class="(?:brand-name|scarb-brand-title)"[^>]*>Scarb\.TO<\/span>/.test(content);
    const retainedWeeklyWordmark=path==='docs/briefs/index.html' && retainedIndex &&
      /<img class="brand-lockup" src="\/assets\/brand\/scarbto-connected\.svg" alt="">/.test(content) &&
      /<a href="https:\/\/scarb\.to\/">Scarb\.TO home<\/a>/.test(content);
    if (!hasHomeLink || !(hasWordmark || retainedWeeklyWordmark)) {
      throw new Error('Visible Scarb.TO wordmark/home link missing from ' + path);
    }
  }
  return count;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const count = checkVoiceGateway(undefined,{publishing:process.argv.includes('--publishing')});
    console.log('Scarb voice gateway checked ' + count + ' approved copy entries and required identity surfaces.');
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
