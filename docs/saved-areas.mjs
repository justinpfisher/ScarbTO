import {staticCopy} from './scarb-voice.mjs';
import {areaFor, NEIGHBOURHOODS, WARDS} from './area-selection.mjs';

export const SAVED_AREAS_KEY = 'scarbto-public-areas-v1';
export function validatedAreas(value) {
  if (!Array.isArray(value)) return [];
  const seen = new Set();
  return value.flatMap(item => {
    const area = areaFor(item?.kind, item?.code);
    const key = area && `${area.kind}:${area.code}`;
    if (!area || seen.has(key)) return [];
    seen.add(key);
    return [{kind:area.kind, code:area.code}];
  });
}
export function publicAreaHref(area) {
  const valid = areaFor(area?.kind, area?.code);
  return valid ? '/?' + new URLSearchParams({areaKind:valid.kind, areaCode:valid.code, mode:'all', days:'all'}) : null;
}
export function mountSavedAreas(document, storage) {
  const choice=document.getElementById('saved-area-choice');
  if (!choice) return;
  const save=document.getElementById('save-public-area');
  const list=document.getElementById('saved-areas-list');
  const status=document.getElementById('saved-areas-status');
  let areas=[];
  try { areas=validatedAreas(JSON.parse(storage.getItem(SAVED_AREAS_KEY)||'[]')); }
  catch { status.textContent=staticCopy('saved-unreadable'); }
  for (const [kind, records] of [['neighbourhood',NEIGHBOURHOODS],['ward',WARDS]]) {
    const group=document.createElement('optgroup');group.label=kind==='ward'?staticCopy('saved-wards'):staticCopy('saved-neighbourhoods');
    for (const [code, area] of Object.entries(records)) {
      const option=document.createElement('option');option.value=`${kind}:${code}`;option.textContent=area.name;group.append(option);
    }
    choice.append(group);
  }
  function persist(next) {
    try { storage.setItem(SAVED_AREAS_KEY, JSON.stringify(next)); areas=next; return true; }
    catch { status.textContent=staticCopy('saved-write-failed'); return false; }
  }
  function render() {
    list.replaceChildren();
    for (const identity of areas) {
      const area=areaFor(identity.kind,identity.code);
      const row=document.createElement('li'), link=document.createElement('a'), remove=document.createElement('button');
      link.href=publicAreaHref(area);link.textContent=area.name;
      remove.type='button';remove.textContent=staticCopy('saved-remove');remove.setAttribute('aria-label',staticCopy('saved-remove-label',{NAME:area.name}));
      remove.addEventListener('click',()=>{
        if (!persist(areas.filter(item=>item.kind!==area.kind||item.code!==area.code))) return;
        render();status.textContent=staticCopy('saved-removed',{NAME:area.name});choice.focus();
      });
      row.append(link,remove);list.append(row);
    }
  }
  choice.disabled=false;
  choice.addEventListener('change',()=>{save.disabled=!choice.value;});
  save.addEventListener('click',()=>{
    const [kind,code]=choice.value.split(':');const area=areaFor(kind,code);
    if (!area) return;
    if (areas.some(item=>item.kind===kind&&item.code===code)) {status.textContent=staticCopy('saved-duplicate',{NAME:area.name});return;}
    if (!persist(validatedAreas([...areas,area]))) return;
    render();status.textContent=staticCopy('saved-added',{NAME:area.name});
  });
  render();
}
if (globalThis.document?.getElementById('saved-area-choice')) {
  let storage;
  try {storage=globalThis.localStorage;} catch {storage=null;}
  mountSavedAreas(document,storage);
}
