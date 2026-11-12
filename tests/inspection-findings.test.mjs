import test from 'node:test';
import assert from 'node:assert/strict';
import {availableFindings,explainFinding} from '../docs/inspection-findings.mjs';
test('Namma finding is explained without claiming actual contamination',()=>{
  const text=explainFinding('Food premise maintained in manner permitting adverse effect on food - Sec. 7(1)(a)(iii)');
  assert.match(text,/could adversely affect/);assert.match(text,/does not establish/);
  assert.equal(explainFinding('Other finding - Sec. 7(1)(a)(iii)'),null);
});
test('all distinct source rows survive presentation, even identical wording',()=>{
  assert.equal(availableFindings({inspection_findings:[{row_id:'a',wording:'Same'},{row_id:'b',wording:'Same'},{wording:'None'}]}).length,2);
  assert.equal(availableFindings({inspection_detail:'Saved partial note'}).length,1);
});
