import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import expected from '../docs/scarb-copy-manifest.mjs';
import {directoryEvidence} from '../scripts/scarb_directory_evidence.mjs';
import {catalogueRequests,sha} from '../scripts/collect_scarb_ai_requests.mjs';
import {SCARB_COPY,renderStaticCopy} from '../docs/scarb-voice.mjs';
import {NEIGHBOURHOODS} from '../docs/area-selection.mjs';
import {slugForName} from '../docs/neighbourhood-routes.mjs';
import {checkVoiceGateway} from '../scripts/check_scarb_voice.mjs';
import {materializeShell} from '../scripts/build_scarb_static.mjs';
import {buildPageFiles} from '../scripts/build_neighbourhood_pages.mjs';
const bytes=readFileSync(new URL('../research/phase1b-csi/fixtures/official-source-contract/scarbto-neighbourhood158-source-contract-2026-10-27.json',import.meta.url));
test('directory production slot retains count and independently pinned evidence',()=>{
 const packet=catalogueRequests(SCARB_COPY).find(x=>x.id==='static.directory-intro');
 assert.equal(sha(packet),'850f969b52836daefced3ddb9392ed7d192ff20a43e89229a462a8d1015149c9');
 assert.equal(expected[packet.id],sha(packet));
 const evidence=packet.evidence.find(x=>x.id==='directory.retained-selection');
 assert.equal(evidence.sha256,shaBytes(evidence.fact));
 const fact=JSON.parse(evidence.fact);assert.equal(fact.qualified_directory_count,30);
 assert.equal(fact.publisher_supplied_membership_attribute,false);
 assert.ok(Object.values(packet.locks).includes('{{COUNT}}'));
 assert.match(renderStaticCopy('directory-intro',{COUNT:30}),/There are 30 pages here/);
 const files=buildPageFiles();assert.equal(files.size,32);
 const directory=files.get('docs/neighbourhoods/index.html');
 assert.equal(shaBytes(directory),'5cc913d2fe1f41306180c9e6c1c166ec6c3d71df16c8bda20770688a80932760');
 const links=Array.from(directory.matchAll(/<li><a href="(\/[a-z0-9-]+\/)">/g),match=>match[1]);
 assert.equal(links.length,30);
 assert.deepEqual(new Set(links),new Set(Object.values(NEIGHBOURHOODS).map(area=>'/'+slugForName(area.name)+'/')));
 for(const link of links)assert.ok(files.has('docs'+link+'index.html'));
 assert.match(directory,/official list of Scarborough neighbourhoods/);

 const shell=JSON.parse(readFileSync(new URL('../config/scarb-static-shells.json',import.meta.url),'utf8'))['docs/neighbourhoods/index.html'];
 const drafts=Object.fromEntries(shell.slots.map(slot=>[slot.id,slot.draft]));
 assert.equal(materializeShell(shell,id=>id===packet.id?SCARB_COPY['directory-intro']:drafts[id]),directory);
});
const shaBytes=s=>createHash('sha256').update(s).digest('hex');
test('changed source bytes rejected',()=>assert.throws(()=>directoryEvidence(Buffer.concat([bytes,Buffer.from(' ')])),/source changed/));
test('missing selection rejected',()=>{const areas={...NEIGHBOURHOODS};delete areas['116'];assert.throws(()=>directoryEvidence(bytes,areas),/selection changed/);});
test('additional selection rejected',()=>assert.throws(()=>directoryEvidence(bytes,{...NEIGHBOURHOODS,'999':{name:'invented'}}),/selection changed/));
test('renamed selection rejected',()=>assert.throws(()=>directoryEvidence(bytes,{...NEIGHBOURHOODS,'116':{name:'invented'}}),/name changed/));
test('directory route substitution fails the offline gateway',()=>{
 const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
 assert.throws(()=>checkVoiceGateway(path=>path==='docs/neighbourhoods/index.html'
  ?read(path).replace('href="/agincourt-north/"','href="/malvern-west/"'):read(path)),/Directory differs/);
});
test('accepted writer cannot remove COUNT',()=>assert.throws(()=>renderStaticCopy('directory-intro',{COUNT:30},()=> 'Thirty pages.'),/placeholders/));
