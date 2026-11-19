/** Current source-derived event manifest. Accepted outputs never supply evidence. */
import {canonical,eventRequests,sha} from './collect_scarb_ai_requests.mjs';
export function currentEventPackets(release,bindings) {
 const packets=eventRequests(release),byKey=new Map(packets.map(p=>[p.id,p]));
 return Object.entries(bindings).sort(([a],[b])=>a.localeCompare(b)).map(([id,binding])=>{
  const packet=byKey.get(binding?.key);
  if(!packet || binding.key!=='event.'+sha(id) || binding.facts!==packet.evidence[0].fact || JSON.parse(binding.facts).id!==id)throw Error('Stale or unqualified event prose binding: '+id);
  if(Object.keys(binding).sort().join(',')!=='facts,key')throw Error('Unexpected event binding fields');
  return packet;
 });
}
export function parseDataModule(source) {
 const match=source.replace(/^\uFEFF/,'').match(/^\s*(?:\/\/[^\n]*\n)*export default ([\s\S]*);\s*$/);
 if(!match)throw Error('Expected a data-only generated module');
 return JSON.parse(match[1]);
}
