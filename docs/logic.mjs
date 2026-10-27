/** Pure presentation/filtering functions; safe to test without a browser. */
export const STATUS = ['Pass', 'Conditional Pass', 'Closed'];
export const DEFAULTS = Object.freeze({mode:'recent',status:'all',days:'30',neighbourhood:'',search:''});

export function dayInWindow(date, days, now = new Date()) {
  if (days === 'all') return true;
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const day = Date.parse(date + 'T00:00:00Z');
  if (!Number.isFinite(day)) return false;
  // Calendar date rather than local clock to avoid a one-day cutoff error.
  const parts = new Intl.DateTimeFormat('en-CA',{timeZone:'America/Toronto',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now);
  const values=Object.fromEntries(parts.map(p=>[p.type,p.value]));
  const today=Date.UTC(Number(values.year),Number(values.month)-1,Number(values.day));
  return day <= today && day >= today - Number(days) * 86400000;
}

export function filterEstablishments(items, state, now = new Date()) {
  const query = state.search.trim().toLocaleLowerCase('en-CA');
  return items.filter(e =>
    (state.status === 'all' || e.status === state.status) &&
    (!state.neighbourhood || e.neighbourhood === state.neighbourhood) &&
    (!query || `${e.name} ${e.address}`.toLocaleLowerCase('en-CA').includes(query)) &&
    dayInWindow(e.inspection_date, state.days, now)
  );
}

export function filterActivity(items, state, now = new Date()) {
  const query = state.search.trim().toLocaleLowerCase('en-CA');
  return items.filter(e =>
    (state.status === 'all' || e.status === state.status) &&
    (!state.neighbourhood || e.neighbourhood === state.neighbourhood) &&
    (!query || `${e.name} ${e.address}`.toLocaleLowerCase('en-CA').includes(query)) &&
    dayInWindow((e.detected_at || '').slice(0,10), state.days, now)
  );
}

export function isStale(iso, now = new Date()) {
  const parsed = Date.parse(iso);
  return !Number.isFinite(parsed) || now.valueOf() - parsed > 48 * 60 * 60 * 1000;
}

export function fitBoundsFromFeatures(features) {
  const coords = [];
  for (const f of features) {
    const g = f.geometry;
    if (!g) continue;
    const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
    for (const poly of polys) for (const ring of poly) for (const point of ring) coords.push(point);
  }
  if (!coords.length) return null;
  return coords.reduce(([west,south,east,north],[lon,lat])=>[Math.min(west,lon),Math.min(south,lat),Math.max(east,lon),Math.max(north,lat)], [180,90,-180,-90]);
}


export function cityDineSafeRecordUrl(id) {
  return `https://www.toronto.ca/community-people/health-wellness-care/health-programs-advice/food-safety/dinesafe/#establishment/${encodeURIComponent(String(id))}`;
}

export function pageRecords(records, limit = 80, selectedId = null) {
  const page = records.slice(0, limit);
  if (selectedId !== null && !page.some(entry => String(entry.id) === String(selectedId))) {
    const selected = records.find(entry => String(entry.id) === String(selectedId));
    if (selected) page.push(selected);
  }
  return page;
}
