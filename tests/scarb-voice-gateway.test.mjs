import test from 'node:test';
import {runInNewContext} from 'node:vm';
import assert from 'node:assert/strict';
import {SCARB_COPY, VOICE_REVISION, staticCopy, communityVoice} from '../docs/scarb-voice.mjs';
import {inspectMarkup, inspectAllMarkup, weeklyIndexShell, SURFACES} from '../scripts/check_scarb_voice.mjs';

test('2x voice has a stable approved catalogue and rejects unknown prose', () => {
  assert.equal(VOICE_REVISION, '2026-11-17-2x');
  assert.match(SCARB_COPY['home-intro'], /records/);
  assert.match(staticCopy('neighbourhood-intro', {NAME:'Highland Creek'}), /Highland Creek/);
  assert.throws(() => staticCopy('unknown'));
  assert.throws(() => staticCopy('neighbourhood-intro'));
  assert.throws(() => staticCopy('neighbourhood-intro',{NAME:'',INVENTED:'claim'}));
  assert.throws(() => staticCopy('directory-intro',{COUNT:NaN}));
  assert.throws(() => staticCopy('directory-intro',{COUNT:-1}));
  assert.throws(() => communityVoice('free-form-guess', {text:'Looks great!'}));
});

test('source-backed composition preserves outcomes, dates and non-opening limits', () => {
  const text = communityVoice('event', {
    name:'Example Café', eventKind:'first_seen', status:'Conditional Pass',
    inspected:'Tuesday, November 10, 2026', recorded:'Thursday, November 12, 2026', nearby:false
  });
  assert.match(text, /not a confirmed opening/);
  assert.match(text, /Conditional Pass/);
  assert.match(text, /Tuesday, November 10, 2026/);
  assert.doesNotMatch(text, /safe to eat|opened today|visited/i);
  assert.match(communityVoice('empty'), /no new updates/);
  assert.match(communityVoice('limitations'), /not restaurant ratings/);
});

test('errors are accurate and data counts are validated', () => {
  assert.match(staticCopy('missing-pdf-tools'), /only after finalisation succeeds/);
  assert.match(communityVoice('embed-summary', {shown:4, eligible:4, omitted:0}), /4 dated updates/);
  assert.throws(() => communityVoice('embed-summary', {shown:5, eligible:4, omitted:0}));
  assert.throws(() => communityVoice('heading', {name:''}));
});

test('marked published text must exactly match approved copy', () => {
  const sample = '<p data-scarb-voice="home-title">' + staticCopy('home-title') + '</p>';
  assert.equal(inspectMarkup('test.html', sample), 1);
  assert.throws(() => inspectMarkup('test.html', sample.replace('stories', 'items')), /drift/);
  assert.throws(() => inspectMarkup('docs/index.html', sample), /Required/);
  assert.ok(Object.keys(SURFACES).includes('docs/community/evidence/index.html'));
});


test('unmarked public text, accessibility labels and metadata cannot bypass static review',()=>{
  const markup='<meta name="description" content="Dated records"><p>Checked records</p><button aria-label="Open source">Open</button>';
  const approved={text:['Checked records','Open'],attributes:['meta:Dated records','aria-label:Open source']};
  assert.equal(inspectAllMarkup('fixture',markup,approved),4);
  for(const changed of [markup+'<p>Invented discovery</p>',markup.replace('Open source','Approve safety'),markup.replace('Dated records','Safe today'), markup+"<button title='Unreviewed'>Open</button>", markup.replace('aria-label="Open source"',"ARIA-LABEL='Unsafe claim'"), markup+"<input type='button' value='Unreviewed'>", markup+'<iframe srcdoc="unreviewed"></iframe>']) {
    assert.throws(()=>inspectAllMarkup('fixture',changed,approved),/Unreviewed public copy|reviewed producer/);
  }
});


test('weekly index validates dynamic rows and quiet dates rather than freezing a past edition list',()=>{
  const edition={path:'briefs/2026-11-02/',period_start:'2026-11-02',period_end:'2026-11-08',event_count:115,revision:4};
  const manifest={schema_version:1,editions:[edition]};
  const rows='<ul><li><a href="/briefs/2026-11-02/">Food inspection updates November 2, 2026–November 8, 2026</a> <span>(115 recorded updates; revision 4)</span></li></ul>';
  assert.equal(weeklyIndexShell(rows,manifest,{published_at:'2026-11-13T17:50:39Z'}),'<ul>ARCHIVE_ROWS</ul>');
  assert.throws(()=>weeklyIndexShell(rows.replace('115','116'),manifest,{published_at:'2026-11-13T17:50:39Z'}),/registered evidence/);
  const quiet='<p>I have no DineSafe updates to share for November 9, 2026–November 15, 2026.</p>';
  assert.equal(weeklyIndexShell(quiet+rows,manifest,{published_at:'2026-11-17T17:00:00Z'}),'<ul>ARCHIVE_ROWS</ul>');
  // Crossing Toronto Monday or retaining an older index must not infer a new week.
  assert.equal(weeklyIndexShell(quiet+rows,manifest,{published_at:'2026-11-15T23:59:59Z'}),'<ul>ARCHIVE_ROWS</ul>');
  assert.throws(()=>weeklyIndexShell(quiet.replace('November 9','November 10')+rows,manifest,{published_at:'2026-11-17T17:00:00Z'}),/Quiet-period/);
});


// The locked parser is already installed for the existing trusted browser job.
// This check never runs in the dependency-free publisher.
import {readFileSync} from 'node:fs';
import {checkSourceGateway, sourceInventory, inspectSource} from '../scripts/check_scarb_voice_source.mjs';
test('runtime source barrier rejects unregistered literals and public sink bypasses',()=>{
  assert.ok(checkSourceGateway()>0);
  for(const filename of ['app','community-editor','community-exports','community-evidence','community-embed','beach-history','selected-calls']) {
    const path='docs/'+filename+'.mjs',source=readFileSync(path,'utf8'),approved=sourceInventory(path,source);
    for(const addition of ['\nconst unregisteredCopy="Invented public finding";', '\ndocument.title="Invented public finding";', '\ndocument.body.setAttribute("aria-label","Invented public finding");', '\nnew Blob(["Invented PDF copy"]);']) {
      assert.throws(()=>inspectSource(path,source+addition,approved),/Unreviewed voice producer/);
    }
  }
  const source='const checked = staticCopy("home-title"); document.title = checked;';
  const approved=sourceInventory('fixture.mjs',source);
  // A known catalogue value at an unrelated sink or a changed data binding is
  // not made acceptable merely by keeping an unused gateway import.
  assert.throws(()=>inspectSource('fixture.mjs',source.replace('document.title = checked','document.title = externalClaim'),approved));
  assert.throws(()=>inspectSource('fixture.mjs',source+'document.body.textContent = checked;',approved));
});


test('producer contracts reject later assignment and same-literal helper transformations',()=>{
  for(const [source,changed] of [
    ['let label="Known label";label=label.trim();document.title=label;', 'let label="Known label";label=label.split("").reverse().join("");document.title=label;'],
    ['function label(value){return value;}function render(value){document.title=label(value);}', 'function label(value){return value.split("").reverse().join("");}function render(value){document.title=label(value);}'],
    ['function render(event){const count=event.count;document.title=staticCopy("count",{COUNT:count});}', 'function render(event){const count=event.count+1;document.title=staticCopy("count",{COUNT:count});}']
  ]) {
    const output=code=>{const document={};runInNewContext(code+(code.includes('function render(event)')?'render({count:4});':code.includes('function render(value)')?'render(\"Known label\");':''),{document,staticCopy:(_,fields)=>String(fields.COUNT)});return document.title;};
    assert.notEqual(output(source),output(changed));
    assert.throws(()=>inspectSource('fixture.mjs',changed,sourceInventory('fixture.mjs',source)),/Unreviewed/);
  }
});
