/** Offline renderer/policy readback only. Never fetch TPS counts. */
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {SCARB_COPY} from '../docs/scarb-voice.mjs';
import {selectedCallsMessage,selectedCallsPolicy} from '../docs/selected-calls.mjs';
import {catalogueRequests,canonical,protect,sha} from './collect_scarb_ai_requests.mjs';
const need=(x,m)=>{if(!x)throw Error(m);};
const raw=readFileSync(new URL('../docs/selected-calls.mjs',import.meta.url));
const sourceHash=createHash('sha256').update(raw).digest('hex');
need(['3be2e3bebbda9d57ac55cad86f998b14380ae9807ca4b7b421b88a9629232a4a','d8c7cc9c4ecaa0697745a982898326492c8bf4436d7304996d1ca3aa13dee545'].includes(sourceHash),'Reviewed selected-calls behavior changed');
const reasons=['loading','not loaded','view hidden','source data is stale','source data expired','cached counts expired','source request timed out','request cancelled','refresh cooldown active','source changed during request','clock changed; refresh required','source timestamp invalid','source verification failed','source response unavailable','source data unavailable'];
const packets=catalogueRequests(SCARB_COPY).filter(p=>p.id.startsWith('static.selected-calls-'));
need(packets.length===20,'Selected-calls family changed');
need(selectedCallsPolicy.maxUpstreamAgeMs===30*60000 && selectedCallsPolicy.maxLocalAgeMs===10*60000 && selectedCallsPolicy.timeoutMs===8000 && selectedCallsPolicy.minAttemptIntervalMs===5*60000,'Freshness policy changed');
const contexts={};
for(const p of packets){
 const key=p.id.slice(7),n=Number(key.slice(-2)),text=SCARB_COPY[key];
 need(n>=1&&n<=20&&canonical(protect(text))===canonical({draft:p.draft,locks:p.locks}),'Exact copy/locks changed');
 need(p.evidence.length===1&&p.evidence[0].sha256===sha(text)&&p.evidence[0].fact===text,'Exact source evidence changed');
 let usage;
 if(n===2){need(selectedCallsMessage({status:'available'})===text,'Available label mismatch');usage='available selected division counts label';}
 else if(n>=3&&n<=17){usage=reasons[n-3];need(selectedCallsMessage({status:'unavailable',reason:usage})===text,'Reason renderer mismatch');}
 else if(n===18){usage='unknown local reason fallback';need(selectedCallsMessage({reason:'unrecognized synthetic reason'})===text,'Fallback mismatch');}
 else {usage=({1:'unavailable and successful response label',19:'successful response licence attribution',20:'successful response selected-call limitations'})[n];need(raw.toString('utf8').includes("staticCopy('"+key+"')"),'Missing renderer consumer');}
 // Numbers in copy must agree with actual policy, not merely with the draft.
 const limit=({6:30,7:30,8:10,9:8,11:5})[n];if(limit)need(p.locks.VALUE_0===String(limit),'Copy limit disagrees with policy');
 contexts[p.id]={path:'docs/selected-calls.mjs',source_sha256:sourceHash,usage,policy:selectedCallsPolicy,locks:p.locks,source_evidence_sha256:p.evidence[0].sha256,meaning:'Local selected-call UI state only, never actual counts or a new source finding. Preserve selected divisions, time limits, trigger/reason, removal of stale/hidden counts and official licence. Never equate selected calls with all crime, activity or officer presence. No humour in safety/error notices.'};
}
process.stdout.write(canonical(contexts));
