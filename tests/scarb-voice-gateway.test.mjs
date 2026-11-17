import test from 'node:test';
import assert from 'node:assert/strict';
import {SCARB_COPY, VOICE_REVISION, staticCopy, communityVoice} from '../docs/scarb-voice.mjs';
import {inspectMarkup, SURFACES} from '../scripts/check_scarb_voice.mjs';

test('2x voice has a stable approved catalogue and rejects unknown prose', () => {
  assert.equal(VOICE_REVISION, '2026-11-17-2x');
  assert.match(SCARB_COPY['home-intro'], /records/);
  assert.match(staticCopy('neighbourhood-intro', {NAME:'Highland Creek'}), /Highland Creek/);
  assert.throws(() => staticCopy('unknown'));
  assert.throws(() => staticCopy('neighbourhood-intro'));
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
