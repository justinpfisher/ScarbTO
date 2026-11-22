/** Exact event evidence binding. No inference/network and no source mutation. */
import bindings from './scarb-event-inputs.mjs';
import {acceptedCopyOrNull} from './scarb-current-copy.mjs';
const FIELDS=['id','feed','establishment_id','name','kind','status','previous_status','inspection_date','detected_at','source_url'];
const canonical=value=>JSON.stringify(value,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
export function eventFacts(event) {
  return Object.fromEntries(FIELDS.filter(key=>event[key]!==undefined).map(key=>[key,event[key]]));
}
export function resolveEventCopy(event,currentBindings,read) {
  const binding=currentBindings[event.id];
  if(!binding)return null;
  if(canonical(eventFacts(event))!==binding.facts)return null;
  return read(binding.key);
}
export const currentEventCopy=event=>resolveEventCopy(event,bindings,acceptedCopyOrNull);
