import {areaFor, validateAreaFeatures} from './area-selection.mjs';
import {fitBoundsFromFeatures} from './logic.mjs';

// Use the same qualified public overlay and MapLibre/style as Explore. This
// preview has no gestures or extra navigation target: the existing link opens
// the full map/list experience, and the local list remains independent.
export async function mountNeighbourhoodMap(root){
  const panel=root.querySelector('.explore-panel');
  const link=panel?.querySelector('#map-link');
  const heading=panel?.querySelector('h2[id]');
  const area=areaFor('neighbourhood',root.dataset.areaCode);
  if(!link||!heading||!area||panel.querySelector('.neighbourhood-map'))return;
  let map,container,stylesheet,timer,stopped=false;
  const controller=new AbortController();
  const discard=()=>{
    if(stopped)return;
    stopped=true;clearTimeout(timer);controller.abort();
    // Preserve focus if an attribution link was active when WebGL failed.
    if(container?.contains(document.activeElement))link.focus({preventScroll:true});
    try{map?.remove();}catch{}
    container?.remove();stylesheet?.remove();panel.classList.remove('has-neighbourhood-map');
  };
  try{
    const context=document.createElement('canvas').getContext('webgl2');
    if(!context)return;
    context.getExtension('WEBGL_lose_context')?.loseContext();
    timer=setTimeout(discard,15000);
    const response=await fetch(new URL('./data/scarborough-overlay-neighbourhoods.geojson',import.meta.url),{cache:'force-cache',signal:controller.signal});
    if(!response.ok)throw new Error('Boundary unavailable');
    const collection=validateAreaFeatures('neighbourhood',await response.json());
    const features=collection.features.filter(feature=>feature.properties.AREA_SHORT_CODE===area.code);
    const bounds=fitBoundsFromFeatures(features);
    if(features.length!==1||!bounds||bounds[0]>=bounds[2]||bounds[1]>=bounds[3])throw new Error('Boundary unavailable');
    if(stopped)return;
    stylesheet=document.createElement('link');
    stylesheet.rel='stylesheet';
    stylesheet.href='https://cdn.jsdelivr.net/npm/maplibre-gl@6.4.1/dist/maplibre-gl.css';
    const styled=new Promise((resolve,reject)=>{
      stylesheet.onload=resolve;stylesheet.onerror=reject;
      controller.signal.addEventListener('abort',()=>reject(new Error('Map unavailable')),{once:true});
    });
    document.head.append(stylesheet);
    const [maplibregl]=await Promise.all([
      import('https://cdn.jsdelivr.net/npm/maplibre-gl@6.4.1/dist/maplibre-gl.mjs'),styled
    ]);
    if(stopped)return;
    container=document.createElement('div');
    container.className='neighbourhood-map';
    container.setAttribute('role','region');
    container.setAttribute('aria-labelledby',heading.id);
    container.style.visibility='hidden';
    link.before(container);panel.classList.add('has-neighbourhood-map');
    const camera=[[bounds[0],bounds[1]],[bounds[2],bounds[3]]];
    const fit={padding:28,duration:0};
    map=new maplibregl.Map({container,style:'https://tiles.openfreemap.org/styles/liberty',
      bounds:camera,fitBoundsOptions:fit,interactive:false,renderWorldCopies:false,
      attributionControl:{compact:false}});
    const canvas=map.getCanvas();
    canvas.setAttribute('tabindex','-1');
    canvas.setAttribute('aria-hidden','true');
    canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();discard();},{once:true});
    map.on('error',discard);
    map.on('load',()=>{
      if(stopped)return;
      try{
        map.addSource('neighbourhood-boundary',{type:'geojson',data:{type:'FeatureCollection',features}});
        map.addLayer({id:'neighbourhood-fill',type:'fill',source:'neighbourhood-boundary',paint:{'fill-color':'#7AAE7A','fill-opacity':0.25}});
        map.addLayer({id:'neighbourhood-outline',type:'line',source:'neighbourhood-boundary',paint:{'line-color':'#0F5132','line-width':3}});
        map.fitBounds(camera,fit);
        map.on('resize',()=>{if(!stopped)map.fitBounds(camera,fit);});
        container.style.visibility='';clearTimeout(timer);
      }catch{discard();}
    });
  }catch{discard();}
}
