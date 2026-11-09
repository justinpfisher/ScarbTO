import {areaFor} from './area-selection.mjs';

export function slugForName(name){
  if(typeof name!=='string'||!name.trim())throw new TypeError('Neighbourhood name is required');
  const slug=name.normalize('NFKD').replace(/\p{M}/gu,'').toLocaleLowerCase('en-CA').replace(/&/g,' and ').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  if(!slug)throw new TypeError('Neighbourhood name has no route-safe characters');
  return slug;
}

export function neighbourhoodPagePath(code){
  const area=areaFor('neighbourhood',code);
  return area?`/${slugForName(area.name)}/`:null;
}
