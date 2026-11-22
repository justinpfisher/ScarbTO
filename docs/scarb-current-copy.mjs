/** Single accepted-copy route. No inference, network, credentials or cache writes.
 * A null input is an explicitly dormant offline draft, never publishable AI copy.
 * Current request hashes are generated from SOURCE DRAFTS/qualified facts, not
 * from accepted text. The publication check independently recomputes them.
 */
import catalogue from './scarb-copy-inputs.mjs';
import expected from './scarb-copy-manifest.mjs';
import {createScarbAiResolver} from './scarb-ai-copy.mjs';

export function createCurrentCopy(input, current) {
  const lookup=createScarbAiResolver(input,current);
  return id=>lookup(id);
}
const accepted=catalogue===null?null:createCurrentCopy(catalogue,expected);
export function currentCopy(id, sourceDraft) {
  // Offline source/fixture work may inspect drafts. The publisher explicitly
  // rejects this state; it is not an outage fallback or an accepted receipt.
  if(accepted===null)return sourceDraft;
  return accepted(id);
}
export function assertAcceptedCopyReady() {
  if(accepted===null)throw new Error('AI copy is dormant: receipt-verified accepted inputs are required before publication');
  for(const id of Object.keys(expected))accepted(id);
  return Object.keys(expected).length;
}
export const COPY_QUALIFICATION=accepted===null?'offline-draft':'accepted-input';

export function acceptedCopyOrNull(id) { return accepted!==null && Object.hasOwn(expected,id) ? accepted(id) : null; }
