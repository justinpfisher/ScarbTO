import {DEFAULTS, STATUS} from './logic.mjs';
import {areaFor} from './area-selection.mjs';

// Only public filter choices belong in a shared URL, never device coordinates.
export function viewFromSearch(search) {
  const params=new URLSearchParams(search), state={...DEFAULTS};
  if(['recent','all','beach','selected-calls'].includes(params.get('mode')))state.mode=params.get('mode');
  if(['all',...STATUS].includes(params.get('status')))state.status=params.get('status');
  if(['7','30','90','all'].includes(params.get('days')))state.days=params.get('days');
  state.neighbourhood=params.get('neighbourhood')||'';
  const area=areaFor(params.get('areaKind'),params.get('areaCode'));
  const requested=params.get('overlay');
  const overlay=['off','neighbourhood','ward'].includes(requested)?requested:area?.kind||'off';
  if(area&&overlay===area.kind){state.areaKind=area.kind;state.areaCode=area.code;}
  return {state,overlay};
}
export function searchFromView(state,overlay='off') {
  const p=new URLSearchParams();
  p.set('mode',state.mode);p.set('days',state.days);p.set('overlay',overlay);
  if(state.status!=='all')p.set('status',state.status);
  if(state.neighbourhood)p.set('neighbourhood',state.neighbourhood);
  if(areaFor(state.areaKind,state.areaCode)){p.set('areaKind',state.areaKind);p.set('areaCode',state.areaCode);}
  return '?'+p.toString();
}
