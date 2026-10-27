function matches(element, className) {
  return element.classList?.contains(className) === true;
}

export function captureListFocus(list, activeElement) {
  if (!activeElement || !list.contains(activeElement)) return null;
  if (matches(activeElement, 'record-item')) return {kind:'record', id:activeElement.dataset.id};
  if (matches(activeElement, 'record-source-link')) return {kind:'source', id:activeElement.dataset.id};
  if (matches(activeElement, 'more-results')) return {kind:'more'};
  return null;
}

export function restoreListFocus(list, previous) {
  if (!previous) return null;
  const records = [...list.querySelectorAll('.record-item')];
  const sources = [...list.querySelectorAll('.record-source-link')];
  const more = list.querySelector('.more-results');
  let target;
  if (previous.kind === 'record') target = records.find(element => element.dataset.id === previous.id);
  if (previous.kind === 'source') target = sources.find(element => element.dataset.id === previous.id);
  if (previous.kind === 'more') target = more || records.at(-1);
  target ||= records[0] || list;
  target.focus({preventScroll:true});
  return target;
}

export function revealSelectedRecord(list, selectedId) {
  if (selectedId === null || selectedId === undefined) return null;
  const card = [...list.querySelectorAll('.record-card')].find(element => element.dataset.id === String(selectedId));
  if (card) card.scrollIntoView({block:'nearest'});
  return card || null;
}
