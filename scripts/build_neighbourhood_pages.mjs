import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {NEIGHBOURHOODS} from '../docs/area-selection.mjs';
import {slugForName} from '../docs/neighbourhood-routes.mjs';

const REPO_ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const TEMPLATE_PATH=path.join(REPO_ROOT,'docs','neighbourhood-page.template.html');
export const ROUTE_ALIASES=Object.freeze({'westrouge':'143'});

const esc=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
export function renderAreaPage(template,code,area){
  const slug=slugForName(area.name);
  const out=template.replaceAll('{{CODE}}',esc(code)).replaceAll('{{NAME}}',esc(area.name)).replaceAll('{{SLUG}}',slug);
  if(/\{\{[^}]+\}\}/.test(out))throw new Error(`Unresolved page template field for ${slug}`);
  return out;
}

export function renderAliasPage(alias,canonicalSlug){
  const destination=`/${canonicalSlug}/`;
  return `<!doctype html>\n<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="canonical" href="https://scarb.to${destination}"><meta http-equiv="refresh" content="0;url=${destination}"><title>Scarb.TO neighbourhood page</title></head><body><p>Looking for this neighbourhood? Its page is over here. <a href="${destination}">Continue to ${esc(canonicalSlug.replaceAll('-',' '))}</a>.</p><script>location.replace(${JSON.stringify(destination)}+location.search+location.hash);</script></body></html>\n`;
}

export function normalizeGeneratedText(value){
  return String(value).replace(/\r\n/g,'\n');
}

export function buildPageFiles(areas=NEIGHBOURHOODS,template=readFileSync(TEMPLATE_PATH,'utf8')){
  const files=new Map(),slugs=new Set();
  for(const [code,area] of Object.entries(areas)){
    const slug=slugForName(area.name);
    if(slugs.has(slug))throw new Error(`Duplicate neighbourhood route: ${slug}`);
    slugs.add(slug);
    files.set(`docs/${slug}/index.html`,renderAreaPage(template,code,area));
  }
  for(const [alias,code] of Object.entries(ROUTE_ALIASES)){
    const area=areas[String(code)];
    if(!area)throw new Error(`Alias ${alias} has no qualified neighbourhood code ${code}`);
    const slug=slugForName(area.name);
    if(slugs.has(alias))throw new Error(`Alias collides with a canonical route: ${alias}`);
    files.set(`docs/${alias}/index.html`,renderAliasPage(alias,slug));
  }
  const links=Object.values(areas).sort((a,b)=>a.name.localeCompare(b.name,'en-CA')).map(area=>`<li><a href="/${slugForName(area.name)}/">${esc(area.name)}</a></li>`).join('\n');
  files.set('docs/neighbourhoods/index.html',`<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Explore neighbourhoods | Scarb.TO</title><meta name="description" content="Explore Scarborough neighbourhood pages, source-linked food inspection records and area boundaries."><link rel="canonical" href="https://scarb.to/neighbourhoods/"><link rel="stylesheet" href="../neighbourhood-page.css"></head><body><div class="page-shell"><header class="site-header"><a class="brand" href="/">Scarb.TO home</a><a class="header-link" href="/briefs/">Weekly briefs</a></header><main><h1>Explore the neighbourhoods</h1><p>There is so much to explore! Choose one of the ${Object.keys(areas).length} neighbourhoods in this map selection to open its source-linked records and boundary view.</p><ul class="neighbourhood-directory">${links}</ul><p class="source-note">These pages follow the City's neighbourhood boundaries, not association or newspaper coverage. Scarb.TO matches source coordinates to those boundaries; a record's location can be imperfect. Different source IDs stay separate.</p><p><a href="https://open.toronto.ca/dataset/neighbourhoods/">City of Toronto neighbourhood boundaries</a>, under the <a href="https://open.toronto.ca/open-data-licence/">Open Government Licence - Toronto</a>.</p></main><footer><p>Scarb.TO is an independent, AI-assisted guide to public records, not an official City service. Inspection results describe their recorded date, not conditions today.</p></footer></div></body></html>
`);
  return files;
}

export function runBuild({check=false,root=REPO_ROOT}={}){
  const files=buildPageFiles();let mismatches=0;
  for(const [relative,content] of files){
    const target=path.join(root,...relative.split('/'));
    if(check){
      let current='';try{current=readFileSync(target,'utf8');}catch{}
      if(normalizeGeneratedText(current)!==normalizeGeneratedText(content)){console.error(`Generated neighbourhood page is missing or stale: ${relative}`);mismatches++;}
    }else{
      mkdirSync(path.dirname(target),{recursive:true});writeFileSync(target,content,'utf8');
    }
  }
  if(check&&mismatches)throw new Error(`${mismatches} generated neighbourhood page(s) need updating`);
  return {count:files.size,mismatches};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const check=process.argv.includes('--check');
  try{const result=runBuild({check});console.log(`${check?'Verified':'Generated'} ${result.count} neighbourhood routes.`);}
  catch(error){console.error(error.message);process.exitCode=1;}
}
