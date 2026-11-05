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
  return `<!doctype html>\n<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="canonical" href="https://scarb.to${destination}"><meta http-equiv="refresh" content="0;url=${destination}"><title>Scarb.TO neighbourhood page</title></head><body><p>This neighbourhood page has moved. <a href="${destination}">Continue to ${esc(canonicalSlug.replaceAll('-',' '))}</a>.</p><script>location.replace(${JSON.stringify(destination)}+location.search+location.hash);</script></body></html>\n`;
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
