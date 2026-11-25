import {createServer} from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
let pdfBytes=null;const root=resolve('docs'),out=process.env.COMMUNITY_ARTIFACTS||resolve('test-results/community');await mkdir(out,{recursive:true});
const server=createServer(async(req,res)=>{try{if(req.url==='/proof.pdf'&&pdfBytes){res.setHeader('Content-Type','application/pdf');res.end(pdfBytes);return;}let name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(name.endsWith('/'))name+='index.html';const path=resolve(root,'.'+name);if(!path.startsWith(root+sep))throw Error();const body=await readFile(path);res.setHeader('Content-Type',({'.mjs':'text/javascript','.js':'text/javascript','.html':'text/html','.css':'text/css','.json':'application/json','.ttf':'font/ttf'})[extname(path)]||'application/octet-stream');res.end(body);}catch{res.writeHead(404);res.end('Missing');}});
await new Promise(r=>server.listen(8871,'127.0.0.1',r));
const host=createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end('<!doctype html><title>Independent origin</title><iframe title="Scarb updates" src="http://127.0.0.1:8871/embed'+(req.url||'/')+'" width="360" height="700"></iframe>');});await new Promise(r=>host.listen(8872,'127.0.0.1',r));
const browser=await chromium.launch({channel:'chromium',headless:true,args:['--no-sandbox']});
try{
 const page=await browser.newPage({viewport:{width:1200,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8871/community/');await page.locator('#settings').waitFor({state:'visible'});await page.locator('#core').getByRole('checkbox',{name:'Golfdale-Cedarbrae-Woburn',exact:true}).check();await page.locator('#width').fill('210');await page.locator('#height').fill('297');await page.getByRole('button',{name:'Make a print proof',exact:true}).click();await page.locator('#proof-section').waitFor({state:'visible'});

 const latestUrl=await page.locator('#embed-link').getAttribute('href');
 const latestQuery=new URL(latestUrl).search;
 assert.equal(new URL(latestUrl).searchParams.get('view'),'latest');
 assert.equal(await page.locator('#publication-view').inputValue(),'latest');
 await page.locator('#proof').getByRole('link',{name:/See the City inspection record for/}).first().waitFor();
 assert.equal(await page.locator('#finalise').isVisible(),false);
 assert.equal(await page.evaluate(()=>localStorage.getItem('scarb-community-finalised')),null);
 const latestPdf=page.waitForEvent('download');
 await page.locator('#pdf').click();
 await (await latestPdf).saveAs(out+'/latest-snapshot.pdf');
 assert.ok((await readFile(out+'/latest-snapshot.pdf')).includes(Buffer.from('#establishment/')));
 const fit = (await page.locator('#proof').innerText()).match(/I could fit (\d+) of (\d+) places on this page\./);
 assert.ok(fit);
 const total = Number(fit[2]);
 async function checkLatestTextDownload(surface, filename) {
  const pending=surface.waitForEvent('download');
  await surface.locator('#text').click();
  const result=await pending;
  assert.equal(result.suggestedFilename(),'scarb-community-copy.txt');
  const target=out+'/'+filename;
  await result.saveAs(target);
  const contents=await readFile(target,'utf8');
  const included=(contents.match(/^See the City record: /gm)||[]).length;
  const omitted=total-included;
  assert.ok(included>0 && omitted>=0);
  const notices=contents.split('\n').filter(line=>line.includes('shown in this text version.'));
  const expected=omitted===1 ? '1 more place isn\u2019t shown in this text version.' :
    omitted+' more places aren\u2019t shown in this text version.';
  assert.deepEqual(notices,omitted ? [expected+' See all '+total+' on Scarb.TO.'] : []);
  if(omitted){
   assert.ok(contents.lastIndexOf('See the City record: ')<contents.indexOf(expected));
   assert.ok(contents.indexOf(expected)<contents.indexOf('City of Toronto DineSafe: '));
  }
  assert.doesNotMatch(await surface.locator('#proof').innerText(),/shown in this text version\./);
  return included;
 }
 assert.equal(await checkLatestTextDownload(page,'latest-measured.txt'),Number(fit[1]));
 const textOnly=await browser.newPage({viewport:{width:390,height:844}});
 try{
  await textOnly.route('**/assets/community/DMSans.ttf',route=>route.abort());
  await textOnly.goto('http://127.0.0.1:8871/community/');
  await textOnly.locator('#settings').waitFor({state:'visible'});
  await textOnly.locator('#core').getByRole('checkbox',{name:'Golfdale-Cedarbrae-Woburn',exact:true}).check();
  await textOnly.locator('#words').fill('150');
  await textOnly.getByRole('button',{name:'Make a print proof',exact:true}).click();
  await textOnly.locator('#proof-section').waitFor({state:'visible'});
  assert.equal(await textOnly.locator('#pdf').isDisabled(),true);
  assert.equal(await textOnly.locator('#png').isDisabled(),true);
  assert.doesNotMatch(await textOnly.locator('#proof').innerText(),/I could fit/);
  assert.ok(await checkLatestTextDownload(textOnly,'latest-text-only.txt')<total);
 }finally{await textOnly.close();}
 await page.locator('#publication-view').selectOption('changes');
 // Use A5 and a matching copy budget for the receipt and its revision. The independent A4 export below still checks 300 dpi.
 const receiptWords='180';
 await page.locator('#width').fill('148');
 await page.locator('#height').fill('210');
 await page.locator('#words').fill(receiptWords);
 await page.getByRole('button',{name:'Make a print proof',exact:true}).click();
 await page.locator('#proof-section').waitFor({state:'visible'});
 const custom=await page.evaluate(async()=>{
  const {composeEdition,validateProfile,selectCoverage}=await import('/community-publishing.mjs');const {prepareOutputs}=await import('/community-exports.mjs');
  const latest=await(await fetch('/community-data/latest.json')).json(),registry=await(await fetch('/community-data/boundaries/'+latest.boundary_version+'.json')).json(),release=await(await fetch('/community-data/releases/'+latest.release_id+'.json')).json();
  const id=latest.areas.find(x=>x.kind==='custom').id;const profile=validateProfile({schema_version:1,name:'Council-area editorial coverage',core:[id,latest.areas[0].id],nearby:[id],topics:['dinesafe'],include_snapshot:true,limits:{words:350,scope:'panel'},layout:{width_mm:210,height_mm:297,margin_mm:8,grayscale:true}},registry);
  const edition=composeEdition({profile,registry,release,start:release.history_start,end:release.checked_at,generatedAt:release.checked_at});const selected=selectCoverage(release.events,profile,registry);if(new Set(selected.map(x=>x.record.id)).size!==selected.length)throw Error('Duplicate event');if(!edition.included_event_ids.length)throw Error('Expected actual event coverage');
  const outputs=await prepareOutputs(edition);const encode=async b=>{let s='';for(const n of new Uint8Array(await b.arrayBuffer()))s+=String.fromCharCode(n);return btoa(s);};return {pdf:await encode(outputs.pdf),png:await encode(outputs.png),count:edition.counts.panel.words,eligible:edition.candidate_event_ids.length,included:edition.included_event_ids.length};
 });assert.ok(custom.count<=350);assert.ok(custom.eligible>=custom.included);await writeFile(out+'/custom-grayscale.pdf',Buffer.from(custom.pdf,'base64'));await writeFile(out+'/custom-grayscale.png',Buffer.from(custom.png,'base64'));
 const exported=await page.evaluate(async()=>{
  const {prepareOutputs,attributedMap}=await import('/community-exports.mjs');const {composeEdition,validateProfile}=await import('/community-publishing.mjs');
  const latest=await (await fetch('/community-data/latest.json')).json();const registry=await(await fetch('/community-data/boundaries/'+latest.boundary_version+'.json')).json();const release=await(await fetch('/community-data/releases/'+latest.release_id+'.json')).json();
  const profile=validateProfile({schema_version:1,name:'Café neighbourhood',core:[latest.areas[0].id],nearby:[],topics:['dinesafe'],limits:{words:150},layout:{width_mm:210,height_mm:297}},registry);
  const edition=composeEdition({profile,registry,release,start:release.history_start,end:release.checked_at,generatedAt:release.checked_at});const outputs=await prepareOutputs(edition);
  const encode=async blob=>{let s='';for(const b of new Uint8Array(await blob.arrayBuffer()))s+=String.fromCharCode(b);return btoa(s);};
  const image=document.createElement('img');image.id='exported-image';image.src=URL.createObjectURL(outputs.png);image.style.width='210mm';document.body.append(image);await image.decode();
  return {pdf:await encode(outputs.pdf),png:await encode(outputs.png),map:await encode(attributedMap(edition)),pixels:outputs.pixels};
 });
 const pdf=Buffer.from(exported.pdf,'base64'),png=Buffer.from(exported.png,'base64');assert.equal(pdf.subarray(0,5).toString(),'%PDF-');assert.ok(pdf.includes(Buffer.from('/FontFile2')));assert.equal(png.readUInt32BE(16),2480);assert.equal(png.readUInt32BE(20),3508);
 let pos=8,physical=false;while(pos<png.length){const n=png.readUInt32BE(pos),type=png.subarray(pos+4,pos+8).toString();if(type==='pHYs'){assert.equal(png.readUInt32BE(pos+8),11811);assert.equal(png.readUInt32BE(pos+12),11811);physical=true;}pos+=n+12;}assert.ok(physical);
 await writeFile(out+'/proof.pdf',pdf);await writeFile(out+'/proof.png',png);await writeFile(out+'/map.svg',Buffer.from(exported.map,'base64'));await page.locator('#exported-image').screenshot({path:out+'/proof-render.png'});pdfBytes=pdf;const pdfPage=await browser.newPage();await pdfPage.goto('http://127.0.0.1:8871/proof.pdf');await pdfPage.waitForTimeout(1500);await pdfPage.screenshot({path:out+'/actual-pdf.png'});await pdfPage.close();
 const embed=await page.locator('#embed-link').getAttribute('href');const query=new URL(embed).search;
 assert.equal(await page.evaluate(()=>localStorage.getItem('scarb-community-finalised')),null);
 await page.locator('#words').fill('3');await page.getByRole('button',{name:'Make a print proof',exact:true}).click();await page.locator('#status').filter({hasText:/limit/}).waitFor();assert.equal(await page.locator('#proof-section').isVisible(),false);
 await page.locator('#words').fill(receiptWords);await page.getByRole('button',{name:'Make a print proof',exact:true}).click();
 const receiptDownload=page.waitForEvent('download');await page.locator('#finalise').click();const receiptFile=await receiptDownload;await receiptFile.saveAs(out+'/edition.json');await page.locator('#status').filter({hasText:/Finalised on this device/}).waitFor();
 const receipt=JSON.parse(await readFile(out+'/edition.json','utf8'));assert.equal(receipt.state,'finalised');assert.ok(receipt.outputs.pdf.sha256);assert.equal(receipt.profile.layout.width_mm,148);assert.equal(receipt.profile.layout.height_mm,210);assert.ok(receipt.included_event_ids.length>0);
 await page.reload();await page.locator('#settings').waitFor({state:'visible'});assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('scarb-community-finalised')).content_hash),receipt.content_hash);
 await page.getByRole('button',{name:'Make a print proof',exact:true}).click();assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('scarb-community-finalised')).content_hash),receipt.content_hash);
 await page.locator('#correction').check();await page.locator('#explanation').fill('Corrected the coverage label; source facts unchanged.');await page.locator('#name').fill('Our corrected neighbourhood');await page.getByRole('button',{name:'Make a print proof',exact:true}).click();await page.locator('#proof-section').waitFor({state:'visible'});
 const revisionDownload=page.waitForEvent('download');await page.locator('#finalise').click();await (await revisionDownload).saveAs(out+'/revision.json');await page.locator('#status').filter({hasText:/Finalised on this device/}).waitFor();const revision=JSON.parse(await readFile(out+'/revision.json','utf8'));assert.equal(revision.revision,2);assert.equal(revision.original.content_hash,receipt.content_hash);assert.equal(revision.edition_id,receipt.edition_id);assert.deepEqual(revision.source_cutoffs,receipt.source_cutoffs);assert.deepEqual(revision.included_event_ids,receipt.included_event_ids);
 await page.goto('http://127.0.0.1:8871/community/evidence/?release='+receipt.release_id);await page.locator('#receipt').setInputFiles(out+'/edition.json');await page.getByRole('button',{name:'Download original pdf',exact:true}).waitFor();const recoveredDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Download original pdf',exact:true}).click();await (await recoveredDownload).saveAs(out+'/recovered.pdf');assert.deepEqual(await readFile(out+'/recovered.pdf'),Buffer.from(receipt.outputs.pdf.content,'base64'));
 await page.setViewportSize({width:375,height:812});await page.goto('http://127.0.0.1:8871/community/');await page.locator('#settings').waitFor({state:'visible'});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.screenshot({path:out+'/mobile.png',fullPage:true});
 await page.locator('#import').setInputFiles(out+'/edition.json');await page.locator('#status').filter({hasText:/cut-off restored/}).waitFor();await page.locator('#name').fill('Interrupted proof');assert.equal(await page.locator('#proof-section').isVisible(),false);
 const tampered={...receipt,copy:receipt.copy+' changed'};await page.locator('#import').setInputFiles({name:'changed.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(tampered))});await page.locator('#status').filter({hasText:/changed since it was finalised/}).waitFor();
 const unavailable=await browser.newPage();await unavailable.route('**/community-data/**',route=>route.abort());await unavailable.goto('http://127.0.0.1:8871/community/');await unavailable.waitForFunction(message=>document.getElementById('status')?.firstChild?.textContent===message,"I can’t show the inspection records right now. You can still check the City’s DineSafe site.");assert.equal(await unavailable.locator('#settings').isVisible(),false);await unavailable.close();
 const noScript=await browser.newPage({javaScriptEnabled:false});await noScript.goto('http://127.0.0.1:8871/community/');assert.equal(await noScript.getByRole('link',{name:'Read the existing weekly briefs instead.'}).isVisible(),true);await noScript.close();

 await page.setViewportSize({width:1200,height:900});
 await page.goto('http://127.0.0.1:8872/'+latestQuery);
 const latestFrame=page.frameLocator('iframe');
 await latestFrame.getByRole('heading',{name:'Last inspection on record'}).waitFor();
 const latestRows=latestFrame.locator('#latest-rows li');
 await latestRows.first().waitFor();
 const firstPage=await latestRows.count();
 assert.ok(firstPage>0&&firstPage<=20);
 const more=latestFrame.getByRole('button',{name:'Show more places'});
 if(await more.isVisible()){
  await more.click();
  assert.ok(await latestRows.count()>firstPage);
 }
 await page.goto('http://127.0.0.1:8872/'+query);const frame=page.frameLocator('iframe');await frame.getByRole('heading').waitFor();await frame.locator('#status').filter({hasText:/updates shown|no successfully checked/}).waitFor();assert.equal(await frame.getByRole('link',{name:'Official DineSafe source'}).count(),1);await page.screenshot({path:out+'/cross-origin.png'});assert.deepEqual(errors,[]);
 console.log(JSON.stringify({passed:true,pdf_bytes:pdf.length,png_bytes:png.length,dimensions:exported.pixels,cross_origin:true,artifacts:out}));
}catch(error){
 const pageStatus=await Promise.all(browser.contexts().flatMap(context=>context.pages()).map(async page=>({
   url:page.url(),
   status:await page.locator('#status').textContent({timeout:500}).catch(()=>null),
 })));
 console.error(JSON.stringify({firstFailurePageStatus:pageStatus}));
 throw error;
}finally{await browser.close();await new Promise(r=>server.close(r));await new Promise(r=>host.close(r));}
