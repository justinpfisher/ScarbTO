import test from 'node:test';
import assert from 'node:assert/strict';
import {NEIGHBOURHOODS} from '../docs/area-selection.mjs';
import {buildPageFiles,renderAliasPage,renderAreaPage} from '../scripts/build_neighbourhood_pages.mjs';
import {neighbourhoodPagePath,slugForName} from '../docs/neighbourhood-routes.mjs';
import {readFileSync} from 'node:fs';

test('the qualified 30 neighbourhood IDs generate unique canonical pages and the West Rouge alias',()=>{
  const pages=buildPageFiles();
  assert.equal(Object.keys(NEIGHBOURHOODS).length,30);
  assert.equal(pages.size,31);
  assert.equal(pages.get('docs/west-rouge/index.html').includes('data-area-code="143"'),true);
  assert.equal(neighbourhoodPagePath('143'),'/west-rouge/');
  assert.equal(neighbourhoodPagePath('999'),null);
  assert.equal(pages.get('docs/westrouge/index.html').includes('href="/west-rouge/"'),true);
  assert.equal(new Set([...pages.keys()].map(path=>path.split('/')[1])).size,31);
});

test('slugging is stable for punctuation and HTML template content is escaped',()=>{
  assert.equal(slugForName("L'Amoreaux West"),'l-amoreaux-west');
  assert.equal(slugForName('Wexford/Maryvale'),'wexford-maryvale');
  assert.match(renderAreaPage('<title>{{NAME}}</title><main data-area-code="{{CODE}}"><link href="/{{SLUG}}/">','1',{name:'<unsafe>'}),/&lt;unsafe&gt;/);
});

test('the generated West Rouge route and alias match their reusable source template',()=>{
  const template=readFileSync(new URL('../docs/neighbourhood-page.template.html',import.meta.url),'utf8');
  const pages=buildPageFiles(NEIGHBOURHOODS,template);
  assert.equal(pages.get('docs/west-rouge/index.html').includes('<h1 id="page-title">West Rouge</h1>'),true);
  assert.match(renderAliasPage('westrouge','west-rouge'),/location\.replace\("\/west-rouge\/"\+location\.search\+location\.hash\)/);
});

test('checked-in neighborhood pages match the reusable template output',()=>{
  const template=readFileSync(new URL('../docs/neighbourhood-page.template.html',import.meta.url),'utf8');
  const pages=buildPageFiles(NEIGHBOURHOODS,template);
  for(const [relative,expected] of pages){
    const actual=readFileSync(new URL(`../${relative}`,import.meta.url),'utf8');
    assert.equal(actual,expected,`${relative} is stale; regenerate with scripts/build_neighbourhood_pages.mjs`);
  }
});
