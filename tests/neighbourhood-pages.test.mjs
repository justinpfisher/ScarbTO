import test from 'node:test';
import assert from 'node:assert/strict';
import {NEIGHBOURHOODS} from '../docs/area-selection.mjs';
import {buildPageFiles,normalizeGeneratedText,renderAliasPage,renderAreaPage} from '../scripts/build_neighbourhood_pages.mjs';
import {neighbourhoodPagePath,slugForName} from '../docs/neighbourhood-routes.mjs';
import {readFileSync} from 'node:fs';
import {initializePageActions} from '../docs/neighbourhood-page-actions.mjs';
import {installAreaPrint} from '../docs/neighbourhood-page.mjs';

test('the qualified 30 neighbourhood IDs generate unique canonical pages and the West Rouge alias',()=>{
  const pages=buildPageFiles();
  assert.equal(Object.keys(NEIGHBOURHOODS).length,30);
  assert.equal(pages.size,32);
  assert.equal(pages.get('docs/west-rouge/index.html').includes('data-area-code="143"'),true);
  assert.equal(neighbourhoodPagePath('143'),'/west-rouge/');
  assert.equal(neighbourhoodPagePath('999'),null);
  assert.equal(pages.get('docs/westrouge/index.html').includes('href="/west-rouge/"'),true);
  assert.equal(new Set([...pages.keys()].map(path=>path.split('/')[1])).size,32);
  const directory=pages.get('docs/neighbourhoods/index.html');
  for(const area of Object.values(NEIGHBOURHOODS))assert.ok(directory.includes(`href="/${slugForName(area.name)}/"`));
});

test('slugging is stable for punctuation and HTML template content is escaped',()=>{
  assert.equal(slugForName("L'Amoreaux West"),'l-amoreaux-west');
  assert.equal(slugForName('Wexford/Maryvale'),'wexford-maryvale');
  assert.match(renderAreaPage('<title>{{NAME}}</title><main data-area-code="{{CODE}}"><link href="/{{SLUG}}/">','1',{name:'<unsafe>'}),/&lt;unsafe&gt;/);
});

test('generated-page comparison normalizes Windows checkout line endings',()=>{
  assert.equal(normalizeGeneratedText('first\r\nsecond\r\n'),'first\nsecond\n');
});

test('the generated West Rouge route and alias match their reusable source template',()=>{
  const template=readFileSync(new URL('../docs/neighbourhood-page.template.html',import.meta.url),'utf8');
  const pages=buildPageFiles(NEIGHBOURHOODS,template);
  assert.equal(pages.get('docs/west-rouge/index.html').includes('<h1 id="page-title">West Rouge</h1>'),true);
  assert.match(pages.get('docs/west-rouge/index.html'),/Let's explore West Rouge/);
  assert.match(pages.get('docs/west-rouge/index.html'),/I match each DineSafe record's source coordinates to the City's neighbourhood boundaries/);
  assert.match(pages.get('docs/west-rouge/index.html'),/not a neighbourhood label supplied by DineSafe/);
  assert.match(pages.get('docs/west-rouge/index.html'),/not a confirmed count of distinct businesses/);
  assert.match(pages.get('docs/west-rouge/index.html'),/neighbourhood boundaries and ward boundaries don't always line up/);
  assert.match(renderAliasPage('westrouge','west-rouge'),/location\.replace\("\/west-rouge\/"\+location\.search\+location\.hash\)/);
});

test('generated pages expose canonical share metadata, print actions, and reuse guidance',()=>{
  const pages=buildPageFiles();
  const page=pages.get('docs/west-rouge/index.html');
  assert.match(page,/<meta property="og:title" content="West Rouge \| Scarb\.TO">/);
  assert.match(page,/<meta property="og:url" content="https:\/\/scarb\.to\/west-rouge\/">/);
  assert.match(page,/<button class="secondary-button" id="share-page" type="button">Share this neighbourhood<\/button>/);
  assert.match(page,/<button class="secondary-button" id="print-page" type="button">Print this page<\/button>/);
  assert.match(page,/Sharing the data\? Check the City's source and licence terms first/);
  assert.match(page,/Results describe the inspection on the date shown, not current safety/);
  assert.match(page,/That gap doesn't mean nothing has happened/);
  assert.match(page,/Don't use them to decide whether to swim today/);
  assert.match(page,/AI-assisted guide to public records, not an official City service or a first-hand reporter/);
  assert.match(page,/https:\/\/open.toronto.ca\/open-data-licence\//);
  const css=readFileSync(new URL('../docs/neighbourhood-page.css',import.meta.url),'utf8');
  assert.match(css,/@media print\{/);
  assert.match(css,/\.page-actions,\.page-action-status,\.primary-link,#show-more\{display:none!important\}/);
});

test('page share and print actions use the canonical URL and accessible status',async()=>{
  const handlers={};const status={textContent:''};const shareButton={addEventListener:(name,fn)=>handlers.share=fn};const printButton={addEventListener:(name,fn)=>handlers.print=fn};
  const doc={title:'West Rouge | Scarb.TO',getElementById:id=>({'share-page':shareButton,'print-page':printButton,'page-action-status':status}[id]),querySelector:()=>({href:'https://scarb.to/west-rouge/'})};
  let shared;let printed=0;
  initializePageActions(doc,{share:async value=>{shared=value;}},{location:{href:'https://scarb.to/west-rouge/?tracking=1'},print:()=>printed++});
  await handlers.share();
  assert.deepEqual(shared,{title:'West Rouge | Scarb.TO',url:'https://scarb.to/west-rouge/'});
  assert.equal(status.textContent,'Sharing options opened.');
  handlers.print();assert.equal(printed,1);
});

test('page share action copies canonical URL when native sharing is unavailable',async()=>{
  const handlers={};const status={textContent:''};const shareButton={addEventListener:(name,fn)=>handlers.share=fn};const printButton={addEventListener:()=>{}};
  const doc={title:'West Rouge | Scarb.TO',getElementById:id=>({'share-page':shareButton,'print-page':printButton,'page-action-status':status}[id]),querySelector:()=>({href:'https://scarb.to/west-rouge/'})};
  let copied='';
  initializePageActions(doc,{clipboard:{writeText:async value=>{copied=value;}}},{location:{href:'https://scarb.to/west-rouge/'},print:()=>{}});
  await handlers.share();
  assert.equal(copied,'https://scarb.to/west-rouge/');
  assert.equal(status.textContent,'Neighbourhood link copied.');
});

test('checked-in neighborhood pages match the reusable template output',()=>{
  const template=readFileSync(new URL('../docs/neighbourhood-page.template.html',import.meta.url),'utf8');
  const pages=buildPageFiles(NEIGHBOURHOODS,template);
  for(const [relative,expected] of pages){
    const actual=readFileSync(new URL(`../${relative}`,import.meta.url),'utf8');
    assert.equal(normalizeGeneratedText(actual),normalizeGeneratedText(expected),`${relative} is stale; regenerate with scripts/build_neighbourhood_pages.mjs`);
  }
});

test('printing includes records after the first 20 and restores original expanded state after cancellation or completion',()=>{
  const handlers={},original=Array.from({length:20},(_,id)=>({id,open:id===2}));
  const summary={textContent:'Showing 20 of 25'},showMore={hidden:false};let focused=false;
  const focus={isConnected:true,focus:()=>{focused=true;}};
  const list={childNodes:original,replaceChildren(...nodes){this.childNodes=nodes;},querySelectorAll(){return this.childNodes;}};
  installAreaPrint({windowRef:{addEventListener:(name,fn)=>{handlers[name]=fn;}},documentRef:{activeElement:focus},list,summary,showMore,
    renderAll:()=>{list.childNodes=Array.from({length:25},(_,id)=>({id,open:false}));summary.textContent='Showing 25 of 25';showMore.hidden=true;}});
  handlers.beforeprint();handlers.beforeprint();
  assert.equal(list.childNodes.length,25);assert.equal(list.childNodes[24].id,24);
  assert.ok(list.childNodes.every(row=>row.open));
  handlers.afterprint();handlers.afterprint();
  assert.deepEqual(list.childNodes,original);assert.equal(list.childNodes[2],original[2]);
  assert.equal(list.childNodes[2].open,true);assert.equal(list.childNodes[1].open,false);
  assert.equal(summary.textContent,'Showing 20 of 25');assert.equal(showMore.hidden,false);assert.equal(focused,true);
  handlers.beforeprint();handlers.afterprint();assert.deepEqual(list.childNodes,original);
});
