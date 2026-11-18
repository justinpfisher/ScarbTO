import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
import {chromium} from 'playwright';
test('directory and neighbourhood header wordmark never overlaps sibling copy',async()=>{
 const root=resolve('docs');
 const server=createServer(async(req,res)=>{try{let name=new URL(req.url,'http://localhost').pathname;if(name.endsWith('/'))name+='index.html';const path=resolve(root,'.'+name);if(!path.startsWith(root+sep))throw Error('path');res.setHeader('content-type',({'.html':'text/html','.css':'text/css','.svg':'image/svg+xml','.mjs':'text/javascript','.json':'application/json'})[extname(path)]||'application/octet-stream');res.end(await readFile(path));}catch{res.writeHead(404);res.end();}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const origin='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({channel:'chromium',headless:true});
 try{
 const page=await browser.newPage();await page.route('**/*',route=>route.request().url().startsWith(origin)?route.continue():route.abort());
 for(const route of ['/neighbourhoods/','/west-rouge/','/ionview/'])for(const width of [320,375,420,421,681,720,1363]){
  await page.setViewportSize({width,height:900});await page.goto(origin+route);await page.evaluate(()=>document.fonts.ready);
  for(const zoom of (width===1363?[1,2]:[1])){
   await page.evaluate(z=>document.body.style.zoom=String(z),zoom);
   const result=await page.evaluate(()=>{
    const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
    const wordmark=document.querySelector('.brand-lockup'),image=rect(wordmark);
    const others=[...document.querySelectorAll('.site-header > .brand-tagline,.site-header > .header-link')].map(rect);
    return {loaded:wordmark.complete&&wordmark.naturalWidth>0,overflow:document.documentElement.scrollWidth>innerWidth+1,overlap:others.some(r=>image.x<r.right&&image.right>r.x&&image.y<r.bottom&&image.bottom>r.y)};
   });
   assert.equal(result.loaded,true,route+' wordmark');assert.equal(result.overflow,false,route+' overflow '+width+'/'+zoom);assert.equal(result.overlap,false,route+' overlap '+width+'/'+zoom);
   if(process.env.HEADER_ARTIFACTS&&width===1363&&zoom===2){await mkdir(process.env.HEADER_ARTIFACTS,{recursive:true});await page.screenshot({path:resolve(process.env.HEADER_ARTIFACTS,route.replaceAll('/','_')+'-200pct.png'),fullPage:true});}
  }
 }
 }finally{await browser.close();await new Promise(r=>server.close(r));}
});
