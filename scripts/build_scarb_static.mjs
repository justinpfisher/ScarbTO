/** Deterministic dry-run static compiler. Exact immutable templates, no writes. */
const escape=(text,attribute)=>text.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll(attribute?'"':'\u0000','&quot;').replaceAll(attribute?"'":'\u0000','&#x27;');
export function materializeShell(record,read) {
 let result=record.source,last=record.source.length;
 for(const slot of [...record.slots].reverse()) {
  if(!Number.isSafeInteger(slot.start)||!Number.isSafeInteger(slot.end)||slot.start<0||slot.end<slot.start||slot.end>last)throw Error('Invalid static slot span');
  last=slot.start;
  let text=read(slot.id);
  if(typeof text!=='string'||!text.trim())throw Error('Missing accepted shell text');
  for(const [key,value] of Object.entries(slot.fields??{}))text=text.replaceAll('{{'+key+'}}',value);
  const placeholders=value=>JSON.stringify((value.match(/\{\{[^{}]+\}\}/g)??[]).sort());
  if(placeholders(text)!==placeholders(slot.draft))throw Error('Static source placeholders changed');
  result=result.slice(0,slot.start)+(text===slot.draft?record.source.slice(slot.start,slot.end):escape(text,slot.attribute))+result.slice(slot.end);
 }
 return result;
}
