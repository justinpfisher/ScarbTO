/** Exact local effective finding map readback. No generation, data pull or writes. */
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {canonical,catalogueRequests,protect,sha} from './collect_scarb_ai_requests.mjs';
const root=new URL('../',import.meta.url);
const read=p=>readFileSync(new URL(p,root),'utf8');
const need=(ok,msg)=>{if(!ok)throw new Error(msg);};
const source=read('docs/scarb-voice.mjs');
let instrumented=source;
for(const name of ['scarb-current-copy.mjs','inspection-translations.mjs']){
 const clause="from './"+name+"'";need(instrumented.split(clause).length===2,'Exact local import changed');
 instrumented=instrumented.replace(clause,'from '+JSON.stringify(new URL('docs/'+name,root).href));
}
// Export existing lexical values without changing their initialization or behavior.
const effective=await import('data:text/javascript;base64,'+Buffer.from(instrumented+'\nexport {translations,findingAcceptedKeys,findingDraft};').toString('base64'));
const sources=JSON.parse(read('config/scarb-finding-source-drafts.json'));
const packets=new Map(catalogueRequests(effective.SCARB_COPY).map(p=>[p.id,p]));
need(Object.keys(sources).length===90 && effective.translations.size===90 && effective.findingAcceptedKeys.size===90,'Exact finding coverage changed');
need(effective.findingDraft('translation',{wording:'unrecognized synthetic finding'})===null && effective.findingVoice('translation',{wording:'unrecognized synthetic finding'})===null,'Unknown wording fallback changed');
const paths=['docs/scarb-voice.mjs','docs/inspection-translations.mjs','config/scarb-finding-source-drafts.json'];
const source_sha256=Object.fromEntries(paths.map(p=>[p,createHash('sha256').update(readFileSync(new URL(p,root))).digest('hex')]));
const contexts={};
for(const [key,official] of Object.entries(sources)){
 const id='static.'+key,packet=packets.get(id),text=effective.translations.get(official.toLocaleLowerCase('en-CA'));
 need(effective.findingAcceptedKeys.get(official.toLocaleLowerCase('en-CA'))===key,'Finding key mapping changed');
 need(typeof text==='string' && text===effective.SCARB_COPY[key] && effective.findingDraft('translation',{wording:official})===text,'Effective translation or override differs');
 need(packet?.kind==='safety' && packet.surface==='source-note' && canonical(protect(text))===canonical({draft:packet.draft,locks:packet.locks}),'Finding classification or locks changed');
 need(packet.evidence.length===2 && packet.evidence[1].id==='official-finding.'+key && packet.evidence[1].source==='https://open.toronto.ca/dataset/dinesafe/' && packet.evidence[1].fact===official && packet.evidence[1].sha256===sha(official),'Official evidence differs');
 contexts[id]={source_sha256,official_evidence_id:packet.evidence[1].id,official_wording:official,effective_translation:text,accepted_key:key,locks:packet.locks,meaning:'Exact dated inspection-finding explanation only. Preserve official wording, required qualifiers and all locks. No humour or inference of current conditions, actual contamination or illness. Unknown wording remains untranslated.'};
}
need(contexts['static.finding-explanation-376035dc95fc05a1'].effective_translation.includes('This does not establish that contamination occurred.'),'Contamination qualifier lost');
need(contexts['static.finding-explanation-7e0c1202c0f59cfd'].effective_translation.includes('internal temperature'),'Internal-temperature qualifier lost');
need(contexts['static.finding-explanation-7e0c1202c0f59cfd'].locks.VALUE_0==='4' && contexts['static.finding-explanation-7e0c1202c0f59cfd'].locks.VALUE_1==='60','Temperature-range override lost');
process.stdout.write(canonical(contexts));
