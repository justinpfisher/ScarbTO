/** Shared, deterministic publishing rules. No network, storage, DOM or mutable globals. */
import {readerDate} from './reader-date.mjs';
export const VERSION = 1;
export const SOURCE = 'https://open.toronto.ca/dataset/dinesafe/';
export const LICENCE = 'https://open.toronto.ca/open-data-licence/';
export const COUNT_RULE = 'Words are whitespace-separated tokens. Characters are Unicode code points, including spaces, punctuation and LF newlines; text is NFC-normalised. Editorial counts include heading, body and qualifications. Panel counts also include sources.';
const fail = message => { throw new TypeError(message); };
const plain = value => value && typeof value === 'object' && !Array.isArray(value);
export const canonical = value => JSON.stringify(value, (_, v) => plain(v) ? Object.fromEntries(Object.keys(v).sort().map(k => [k,v[k]])) : v);
export async function digest(value) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(typeof value === 'string' ? value : canonical(value))))].map(b=>b.toString(16).padStart(2,'0')).join('');
}
export function counts(text) {
  text=String(text).replace(/\r\n?/g,'\n').normalize('NFC');
  return {words:text.trim()?text.trim().split(/\s+/u).length:0,characters:[...text].length};
}
function instant(value) {
  if(typeof value!=='string'||!/(?:Z|[+-]\d\d:\d\d)$/.test(value)||!Number.isFinite(Date.parse(value))) fail('Use an exact timestamp with a time zone.');
  return Date.parse(value);
}
function text(value,max=200) {
  if(typeof value!=='string'||!value.trim()||value.length>max||/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(value)) fail('A name or label is missing or invalid.');
  return value.trim().normalize('NFC');
}
function limit(value) {
  if(value==null) return null;
  if(!Number.isInteger(value)||value<1||value>100000) fail('Choose a positive copy limit.');
  return value;
}
export function validateProfile(input, registry) {
  if(!plain(input)||input.schema_version!==VERSION) fail('This settings file is not supported.');
  const allowed=new Set(['schema_version','name','core','nearby','topics','limits','layout','association','distribution','include_snapshot']);
  if(Object.keys(input).some(k=>!allowed.has(k))) fail('These settings include unsupported fields.');
  function areas(values) {
    if(!Array.isArray(values)||values.length>40) fail('Choose up to 40 verified areas.');
    return [...new Set(values)].sort().map(key=>{
      if(typeof key!=='string'||!registry[key]||registry[key].verification!=='verified') fail('One selected boundary has not been verified.');
      return key;
    });
  }
  const core=areas(input.core),nearby=areas(input.nearby||[]).filter(id=>!core.includes(id));
  if(core.length+nearby.length>40) fail('Choose no more than 40 combined core and nearby areas.');
  if(!core.length) fail('Choose at least one core area.');
  if(!Array.isArray(input.topics)||input.topics.some(t=>!['dinesafe'].includes(t))||!input.topics.length) fail('Only qualified food inspection updates are available for publishing.');
  const l=input.layout||{}, width=Number(l.width_mm),height=Number(l.height_mm),margin=Number(l.margin_mm??8);
  if(![width,height,margin].every(Number.isFinite)||width<80||width>420||height<80||height>594||margin<5||margin>20||width<=margin*2||height<=margin*2) fail('Choose a supported physical page size and margin.');
  const limits=input.limits||{};
  if(!['editorial','panel'].includes(limits.scope||'editorial')) fail('Choose editorial or whole-panel limits.');
  return {schema_version:VERSION,name:text(input.name),core,nearby,topics:['dinesafe'],include_snapshot:Boolean(input.include_snapshot),limits:{words:limit(limits.words),characters:limit(limits.characters),scope:limits.scope||'editorial'},layout:{width_mm:width,height_mm:height,margin_mm:margin,grayscale:Boolean(l.grayscale)},association:input.association?text(input.association):null,distribution:input.distribution?text(input.distribution):null};
}
function onSegment(p,a,b) {
  const cross=(p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]);
  return Math.abs(cross)<1e-12&&p[0]>=Math.min(a[0],b[0])-1e-12&&p[0]<=Math.max(a[0],b[0])+1e-12&&p[1]>=Math.min(a[1],b[1])-1e-12&&p[1]<=Math.max(a[1],b[1])+1e-12;
}
function ringLocation(p,ring) {
  let inside=false;
  for(let i=1;i<ring.length;i++) {
    const a=ring[i-1],b=ring[i];
    if(onSegment(p,a,b)) return 0;
    if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]) inside=!inside;
  }
  return inside?1:-1;
}
/** Edges, including hole edges, are included; hole interiors excluded. */
export function pointInGeometry(point,geometry) {
  if(!Array.isArray(point)||point.length!==2||!point.every(Number.isFinite)) return false;
  const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
  return polygons.some(rings=>{
    const outer=ringLocation(point,rings[0]);
    if(outer<0) return false;
    if(outer===0) return true;
    for(const hole of rings.slice(1)) {const location=ringLocation(point,hole);if(location===0)return true;if(location>0)return false;}
    return true;
  });
}
export function validateGeometry(geometry) {
  if(!geometry||!['Polygon','MultiPolygon'].includes(geometry.type)) fail('Choose Polygon or MultiPolygon geometry.');
  const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
  if(!Array.isArray(polygons)||!polygons.length||polygons.length>100) fail('Boundary polygons are missing.');
  if(polygons.reduce((n,rings)=>n+(Array.isArray(rings)?rings.reduce((m,r)=>m+(Array.isArray(r)?r.length:50001),0):50001),0)>50000) fail('This boundary is too large for the publishing tool.');
  const orient=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
  const intersects=(a,b,c,d)=>orient(a,b,c)*orient(a,b,d)<0&&orient(c,d,a)*orient(c,d,b)<0||onSegment(a,c,d)||onSegment(b,c,d)||onSegment(c,a,b)||onSegment(d,a,b);
  const ringsIntersect=(a,b)=>a.slice(1).some((p,i)=>b.slice(1).some((q,j)=>intersects(a[i],p,b[j],q)));
  let vertices=0;
  for(const rings of polygons) {
    if(!Array.isArray(rings)||!rings.length) fail('Boundary rings are missing.');
    for(const ring of rings) {
      if(!Array.isArray(ring)||ring.length<4||canonical(ring[0])!==canonical(ring.at(-1))) fail('Boundary rings must be closed.');
      let area=0;
      for(let i=0;i<ring.length;i++) {
        const p=ring[i];vertices++;
        if(!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite)||p[0]<-79.6||p[0]>-79||p[1]<43.5||p[1]>44) fail('Boundary coordinates must be longitude, latitude near Scarborough.');
        if(i) {const a=ring[i-1];area+=a[0]*p[1]-p[0]*a[1];}
      }
      if(Math.abs(area)<1e-12) fail('A boundary ring has no area.');
      // Proper crossings and repeated non-adjacent vertices reject self-intersections.
      const orient=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
      for(let i=1;i<ring.length;i++) for(let j=i+2;j<ring.length;j++) {
        if(i===1&&j===ring.length-1) continue;
        const a=ring[i-1],b=ring[i],c=ring[j-1],d=ring[j];
        if(orient(a,b,c)*orient(a,b,d)<0&&orient(c,d,a)*orient(c,d,b)<0||onSegment(a,c,d)||onSegment(b,c,d)) fail('A boundary ring crosses itself.');
      }
    }
    for(let i=1;i<rings.length;i++) {
      const hole=rings[i];
      if(hole.some(p=>ringLocation(p,rings[0])!==1)||ringsIntersect(hole,rings[0])) fail('A hole must sit wholly inside its polygon.');
      for(let j=1;j<i;j++) if(ringsIntersect(hole,rings[j])||ringLocation(hole[0],rings[j])>=0||ringLocation(rings[j][0],hole)>=0) fail('Boundary holes must not overlap.');
    }
  }
  for(let i=0;i<polygons.length;i++) for(let j=0;j<i;j++) {
    // Disjoint multipart interiors: conservative validation rejects touching components too.
    if(ringsIntersect(polygons[i][0],polygons[j][0])||pointInGeometry(polygons[i][0][0],{type:'Polygon',coordinates:polygons[j]})||pointInGeometry(polygons[j][0][0],{type:'Polygon',coordinates:polygons[i]})) fail('Multipart boundaries must have disjoint components.');
  }
  return geometry;
}
export function selectCoverage(records,profile,registry) {
  const selected=new Map();
  for(const record of records) {
    if(!record.id) fail('A source record is missing its identity.');
    const point=[record.longitude,record.latitude];
    const core=profile.core.filter(id=>pointInGeometry(point,registry[id].geometry));
    const nearby=profile.nearby.filter(id=>pointInGeometry(point,registry[id].geometry));
    if(core.length||nearby.length) {
      if(selected.has(record.id)&&canonical(selected.get(record.id).record)!==canonical(record)) fail('Conflicting source records share one identity.');
      selected.set(record.id,{record,coverage:core.length?'core':'nearby',areas:core.length?core:nearby});
    }
  }
  return [...selected.values()].sort((a,b)=>a.record.id.localeCompare(b.record.id));
}
function fits(copy,footer,limits) {
  const n=counts(limits.scope==='panel'?copy+'\n\n'+footer:copy);
  return (!limits.words||n.words<=limits.words)&&(!limits.characters||n.characters<=limits.characters);
}
function eventCopy(event,coverage) {
  const prefix=coverage==='nearby'?'Nearby: ':'';
  const novelty=event.kind==='first_seen'?'added to the records I checked (not a confirmed opening)':event.kind==='status_changed'?`a recorded change from ${event.previous_status} to ${event.status}`:'an inspection update';
  return `${prefix}${event.name}: ${novelty}. DineSafe recorded ${event.status} for the inspection on ${readerDate(event.inspection_date)}. I first recorded this information on ${readerDate(event.detected_at)}.`;
}
/** Draft generation never changes a previous receipt or advances a saved watermark. */
export function composeEdition({profile,registry,release,start,end,previous=null,generatedAt,correctionOf=null}) {
  const endMs=instant(end), generatedMs=instant(generatedAt);
  const previousEnd=previous?.state==='finalised'?previous.source_cutoffs?.dinesafe:null;
  start=start||previousEnd;
  const startMs=instant(start);
  const firstAtBeginning=correctionOf?correctionOf.requested_period.start_inclusive:!previous&&startMs===instant(release.history_start);
  if(startMs>endMs||(startMs===endMs&&!firstAtBeginning)||endMs>generatedMs) fail('Choose a reporting end after the start, not in the future.');
  if(startMs<instant(release.history_start)) fail('That period starts before the retained change history.');
  const checked=instant(release.checked_at);
  if(!release.id||release.source_url!==SOURCE||!Array.isArray(release.events)) fail('The qualified source release is unavailable.');
  const cutoff=new Date(Math.min(endMs,checked)).toISOString();
  if(instant(cutoff)<startMs||(instant(cutoff)===startMs&&!firstAtBeginning)) fail('I have no newer successful source check for that reporting period.');
  const selected=selectCoverage(release.events,profile,registry);
  const priorIds=correctionOf?.previously_included_event_ids||previous?.publication_included_event_ids||previous?.included_event_ids||[];
  const already=new Set(priorIds);
  const eligible=selected.filter(({record:e})=>(instant(e.detected_at)>startMs||(firstAtBeginning&&instant(e.detected_at)===startMs))&&instant(e.detected_at)<=instant(cutoff)&&!already.has(e.id));
  const candidates=(correctionOf?eligible.filter(x=>correctionOf.candidate_event_ids.includes(x.record.id)):eligible).sort((a,b)=>instant(b.record.detected_at)-instant(a.record.detected_at)||a.record.id.localeCompare(b.record.id));
  const changed=previous&&canonical(previous.profile)!==canonical(profile);
  const warnings=[...[...new Set([...profile.core,...profile.nearby].map(id=>registry[id].coverage_note).filter(Boolean))],`These dated inspection results are not restaurant ratings or a guarantee of conditions today. Check the official DineSafe record for anything newer.`, ...(generatedMs-checked>72*3600000?[`I couldn't check for anything newer than ${readerDate(release.checked_at)}. This edition does not cover later information.`]:[]), ...(changed?['The coverage or settings changed since the previous edition, so this is not a like-for-like comparison.']:[])];
  const heading=`Food inspection updates for ${profile.name}`;
  const period=`Information added ${firstAtBeginning?'from':'after'} ${readerDate(start)} through ${readerDate(cutoff)}. Original inspection dates appear beside each result.`;
  const footer=`Edition revision 1. Information cut-off: ${readerDate(cutoff)}.\nCity of Toronto DineSafe: ${SOURCE}\nOpen Government Licence - Toronto: ${LICENCE}\nInformation checked ${readerDate(release.checked_at)}. Evidence: https://scarb.to/community/evidence/?release=${release.id}\nPrepared with Scarb.TO. Keep the downloaded receipt with this edition.`;
  const paragraphs=[]; const included=[]; const omissions=[];
  const render=()=>[heading,period,...paragraphs,...warnings].join('\n\n');
  if(!fits(render(),footer,profile.limits)) fail('This limit cannot fit the reporting dates and essential qualifications. Increase the space or copy limit.');
  for(const item of candidates) {
    paragraphs.push(eventCopy(item.record,item.coverage));
    if(fits(render(),footer,profile.limits)) included.push(item.record.id);
    else {paragraphs.pop();omissions.push({id:item.record.id,reason:'space'});}
  }
  const snapshot=profile.include_snapshot?selectCoverage(release.records||[],profile,registry):[];
  let snapshotIncluded=false;
  if(profile.include_snapshot){paragraphs.push(`For context: this selection contains ${snapshot.length} qualified DineSafe establishment records as checked on ${readerDate(release.checked_at)}. This is a dated snapshot, not a count of events during the reporting period or necessarily distinct businesses.`);if(fits(render(),footer,profile.limits))snapshotIncluded=true;else{paragraphs.pop();omissions.push({id:'snapshot',reason:'space'});}}
  if(!candidates.length) paragraphs.push('I found no new updates in the qualified records checked for this selection and period. That does not mean nothing happened.');
  if(candidates.length&&!included.length) fail('This limit leaves no room for one complete update. Increase it rather than dropping the qualifications.');
  if(!fits(render(),footer,profile.limits)) fail('The no-update explanation needs a larger copy limit.');
  const copy=render().normalize('NFC');
  return {schema_version:VERSION,state:'draft',revision:1,generated_at:generatedAt,profile:structuredClone(profile),boundaries:Object.fromEntries([...profile.core,...profile.nearby].map(id=>[id,structuredClone(registry[id])])),requested_period:{start,end,start_inclusive:firstAtBeginning},source_cutoffs:{dinesafe:cutoff},release_id:release.id,evidence:structuredClone(release),snapshot_record_ids:snapshotIncluded?snapshot.map(x=>x.record.id):[],previously_included_event_ids:[...priorIds],publication_included_event_ids:[...new Set([...priorIds,...(correctionOf?.publication_included_event_ids||[]),...included])],candidate_event_ids:candidates.map(x=>x.record.id),included_event_ids:included,omissions,copy,footer,counts:{editorial:counts(copy),sources:counts(footer),panel:counts(copy+'\n\n'+footer)},composition_version:VERSION};
}
export async function finaliseEdition(draft) {
  if(draft.state!=='draft') fail('Only a reviewed draft can be finalised.');
  const result=structuredClone(draft);
  result.state='finalised';result.content_hash=await digest({...result,content_hash:undefined});
  result.edition_id=result.content_hash.slice(0,24);
  return result;
}
export async function verifyReceipt(receipt) {
  if(!plain(receipt)||receipt.schema_version!==VERSION||receipt.state!=='finalised') fail('Choose a finalised edition receipt.');
  const {content_hash,edition_id,revision_id,...content}=receipt;
  if(content_hash!==await digest(content)||(receipt.revision===1?edition_id!==content_hash.slice(0,24):revision_id!==content_hash.slice(0,24))) fail('This receipt has changed since it was finalised. Keep the original and create an explained revision.');
  if(receipt.revision>1) { if(receipt.revision>10||!receipt.original||receipt.revision!==receipt.original.revision+1||receipt.edition_id!==receipt.original.edition_id||!receipt.correction_explanation) fail('This correction does not preserve its original edition.'); await verifyReceipt(receipt.original); }
  return receipt;
}

/** Corrections preserve all earlier copy and evidence; hashes are integrity, not authentication. */
export async function reviseEdition(original,draft,explanation) {
  await verifyReceipt(original);
  if(draft.state!=='draft'||original.revision>=10) fail('Create a draft and retain the original before making a correction.');
  const result={...structuredClone(draft),state:'finalised',revision:original.revision+1,original_generated_at:original.original_generated_at||original.generated_at,revised_at:draft.generated_at,original:structuredClone(original),correction_explanation:text(explanation,1000)};
  result.content_hash=await digest(result);
  result.edition_id=original.edition_id;result.revision_id=result.content_hash.slice(0,24);
  return result;
}
