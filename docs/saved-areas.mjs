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
  catch { status.textContent='Saved areas could not be read. You can still explore any area.'; }
  for (const [kind, records] of [['neighbourhood',NEIGHBOURHOODS],['ward',WARDS]]) {
    const group=document.createElement('optgroup');group.label=kind==='ward'?'City wards':'Neighbourhoods';
    for (const [code, area] of Object.entries(records)) {
      const option=document.createElement('option');option.value=`${kind}:${code}`;option.textContent=area.name;group.append(option);
    }
    choice.append(group);
  }
  function persist(next) {
    try { storage.setItem(SAVED_AREAS_KEY, JSON.stringify(next)); areas=next; return true; }
    catch { status.textContent='This browser could not save the change. Your list has not changed.'; return false; }
  }
  function render() {
    list.replaceChildren();
    for (const identity of areas) {
      const area=areaFor(identity.kind,identity.code);
      const row=document.createElement('li'), link=document.createElement('a'), remove=document.createElement('button');
      link.href=publicAreaHref(area);link.textContent=area.name;
      remove.type='button';remove.textContent='Remove';remove.setAttribute('aria-label',`Remove ${area.name} from saved areas`);
      remove.addEventListener('click',()=>{
        if (!persist(areas.filter(item=>item.kind!==area.kind||item.code!==area.code))) return;
        render();status.textContent=`Removed ${area.name} from this browser.`;choice.focus();
      });
      row.append(link,remove);list.append(row);
    }
  }
  choice.disabled=false;
  choice.addEventListener('change',()=>{save.disabled=!choice.value;});
  save.addEventListener('click',()=>{
    const [kind,code]=choice.value.split(':');const area=areaFor(kind,code);
    if (!area) return;
    if (areas.some(item=>item.kind===kind&&item.code===code)) {status.textContent=`${area.name} is already saved.`;return;}
    if (!persist(validatedAreas([...areas,area]))) return;
    render();status.textContent=`Saved ${area.name} on this browser.`;
  });
  render();
}
if (globalThis.document?.getElementById('saved-area-choice')) {
  let storage;
  try {storage=globalThis.localStorage;} catch {storage=null;}
  mountSavedAreas(document,storage);
}
