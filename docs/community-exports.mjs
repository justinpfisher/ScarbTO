/** One measured layout feeds vector PDF and 300-dpi PNG. No HTML conversion. */
import {digest} from './community-publishing.mjs';
let fontBytes=null;
async function loadFont(){if(!fontBytes){const r=await fetch('/assets/community/DMSans.ttf');if(!r.ok)throw new Error('The licensed export font could not load. Try again before exporting.');fontBytes=new Uint8Array(await r.arrayBuffer());}return fontBytes;}
export async function prepareOutputs(edition){
 if(!window.jspdf?.jsPDF)throw new Error('The PDF tools could not load. Your text and receipt remain available.');
 const bytes=await loadFont();let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);
 const {width_mm:w,height_mm:h,margin_mm:m,grayscale}=edition.profile.layout;
 const pdf=new window.jspdf.jsPDF({orientation:w>h?'landscape':'portrait',unit:'mm',format:[w,h],compress:true,putOnlyUsedFonts:true});
 pdf.addFileToVFS('DMSans.ttf',binary);pdf.addFont('DMSans.ttf','DMSans','normal');pdf.setFont('DMSans');
 const all=edition.copy+'\n\n'+edition.footer;
 const metadata=pdf.getFont().metadata;
 for(const char of all){if(!/\s/u.test(char)&&(!metadata.characterToGlyph||!metadata.characterToGlyph(char.codePointAt(0))))throw new Error(`The export font cannot represent ${char}. Do not publish substituted glyphs; retain the text and choose a font-qualified output.`);}
 const lines=[];let y=m+5;
 for(const [text,size] of [[edition.copy,11],[edition.footer,8]]){
   pdf.setFontSize(size);const step=size*0.352778*1.4;
   for(const paragraph of text.split('\n')){
     const wrapped=paragraph?pdf.splitTextToSize(paragraph,w-2*m):[''];
     for(const line of wrapped){if(y+size*0.352778*.3>h-m)throw new Error('This copy does not fit the chosen physical page at readable size. Choose less copy or a larger layout.');lines.push({text:line,size,y});pdf.text(line,m,y);y+=step;}
   }
   y+=3;
 }
 pdf.setCreationDate('D:'+new Date(edition.generated_at).toISOString().replace(/\D/g,'').slice(0,14)+"+00'00'");pdf.setFileId((await digest(all+JSON.stringify(edition.profile.layout))).slice(0,32));pdf.setProperties({title:edition.profile.name,subject:'Frozen, source-linked community edition',creator:'Scarb.TO'});
 const face=new FontFace('ScarbExport',bytes.buffer);await face.load();document.fonts.add(face);
 const scale=300/25.4,canvas=document.createElement('canvas');canvas.width=Math.round(w*scale);canvas.height=Math.round(h*scale);const ctx=canvas.getContext('2d');if(!ctx)throw new Error('Image export is unavailable in this browser.');
 ctx.fillStyle='#ffffff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.fillStyle=grayscale?'#000000':'#18382b';ctx.textBaseline='alphabetic';
 for(const line of lines){ctx.font=`${line.size*300/72}px ScarbExport`;if(ctx.measureText(line.text).width>(w-2*m)*scale+1)throw new Error('The image font wraps differently at this size. Choose a wider layout before exporting.');ctx.fillText(line.text,m*scale,line.y*scale);}
 const png=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!png)throw new Error('The high-resolution image could not be created.');
 return {pdf:pdf.output('blob'),png:await pngDensity(png),width_mm:w,height_mm:h,pixels:[canvas.width,canvas.height],dpi:300,lines};
}
export function downloadBlob(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

export function attributedMap(edition){
 const entries=Object.values(edition.boundaries),rings=entries.flatMap(b=>b.geometry.type==='Polygon'?b.geometry.coordinates:b.geometry.coordinates.flat());
 const mercator=([lng,lat])=>[lng*Math.PI/180,Math.log(Math.tan(Math.PI/4+lat*Math.PI/360))];
 const points=rings.flat().map(mercator),xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
 const west=Math.min(...xs),east=Math.max(...xs),south=Math.min(...ys),north=Math.max(...ys);
 const scale=Math.min(900/(east-west),600/(north-south));
 const xy=p=>{const [x,y]=mercator(p);return [50+(x-west)*scale,50+(north-y)*scale];};
 const escape=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
 const paths=entries.map(b=>{const polygons=b.geometry.type==='Polygon'?[b.geometry.coordinates]:b.geometry.coordinates;return polygons.map(rings=>`<path d="${rings.map(ring=>ring.map((p,i)=>(i?'L':'M')+xy(p).map(v=>v.toFixed(3)).join(',')).join(' ')+'Z').join(' ')}" fill="#cfe6c2" fill-rule="evenodd" stroke="#18382b" stroke-width="2"/>`).join('');}).join('');
 const events=edition.evidence.events.filter(e=>edition.included_event_ids.includes(e.id));
 const markers=events.map(e=>{const [x,y]=xy([e.longitude,e.latitude]);return `<circle cx="${x.toFixed(3)}" cy="${y.toFixed(3)}" r="5" fill="#18382b"><title>${escape(e.name)}: ${escape(e.status)} on ${escape(e.inspection_date)}</title></circle>`;}).join('');
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="800" viewBox="0 0 1000 800" role="img" aria-label="Selected coverage and locations of updates included in this edition"><rect width="1000" height="800" fill="#ffffff"/>${paths}${markers}<g fill="#111" font-family="sans-serif" font-size="16"><text x="40" y="700">Locations of included updates, not all places or current safety conditions.</text><text x="40" y="730">City of Toronto boundaries and DineSafe. Open Government Licence - Toronto.</text><text x="40" y="755">${escape('https://open.toronto.ca/open-data-licence/')}</text><text x="40" y="780">Scarb.TO | Retain the edition receipt for exact boundaries, dates and source records.</text></g></svg>`;
 return new Blob([svg],{type:'image/svg+xml;charset=utf-8'});
}

export async function retainedOutput(blob){
 const bytes=new Uint8Array(await blob.arrayBuffer());let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);
 const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');
 return {mime_type:blob.type,sha256:hash,encoding:'base64',content:btoa(binary)};
}

/** Canvas PNGs default to 96 dpi. Set the physical resolution explicitly. */
async function pngDensity(blob){
 const source=new Uint8Array(await blob.arrayBuffer()),parts=[source.slice(0,8)];let pos=8;
 const chunk=new Uint8Array(21),view=new DataView(chunk.buffer);view.setUint32(0,9);chunk.set([112,72,89,115],4);view.setUint32(8,11811);view.setUint32(12,11811);chunk[16]=1;
 let crc=0xffffffff;for(const byte of chunk.slice(4,17)){crc^=byte;for(let i=0;i<8;i++)crc=crc&1?(crc>>>1)^0xedb88320:crc>>>1;}view.setUint32(17,(crc^0xffffffff)>>>0);
 while(pos<source.length){const size=new DataView(source.buffer,source.byteOffset+pos,4).getUint32(0);const type=String.fromCharCode(...source.slice(pos+4,pos+8));if(pos+size+12>source.length)throw new Error('The generated PNG is incomplete.');if(type!=='pHYs')parts.push(source.slice(pos,pos+size+12));if(type==='IHDR')parts.push(chunk);pos+=size+12;}
 return new Blob(parts,{type:'image/png'});
}