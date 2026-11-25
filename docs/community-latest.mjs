import {canonical, counts, LICENCE, selectCoverage, SOURCE, validateProfile} from './community-publishing.mjs';
import {cityDineSafeRecordUrl} from './logic.mjs';
import {readerDate, readerDateTime} from './reader-date.mjs';

export const LATEST = 'latest';
export const CHANGES = 'changes';
export const TEXT_PROOF_ONLY = "The PDF didn’t come together. You can still download the text.";
const hexDigest = /^[a-f0-9]{64}$/;
export const SNAPSHOT_UNAVAILABLE = "I can’t show the inspection records right now. You can still check the City’s DineSafe site.";
export const LATEST_SETTINGS_ERROR = "I can’t make a proof with those settings. Try choosing the area and what to show again.";
export const WIDGET_SETTINGS_ERROR = "I don’t recognise those widget settings. You can still see the inspections on Scarb.TO.";
export const INSPECTION_SCOPE = "I’m working from City records I can verify in Scarborough’s six wards.";
const validInstant = value => typeof value === 'string' && /(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));

export function readPublicationSettings(value, registry) {
  if (value?.schema_version !== 2) {
    return {view: CHANGES, profile: validateProfile(value, registry)};
  }
  if (Object.keys(value).length !== 3 || ![LATEST, CHANGES].includes(value.view) || !Object.hasOwn(value, 'profile')) {
    throw new TypeError(LATEST_SETTINGS_ERROR);
  }
  try {
    return {view: value.view, profile: validateProfile(value.profile, registry)};
  } catch (error) {
    if (value.view === LATEST) throw new TypeError(LATEST_SETTINGS_ERROR);
    throw error;
  }
}

export function widgetView(params) {
  if ([...params.keys()].some(key => !['areas', 'nearby', 'days', 'view'].includes(key)) ||
      params.getAll('view').length > 1 ||
      (params.has('view') && (params.get('view') !== LATEST || params.has('days')))) {
    throw new TypeError(params.has('view') ? WIDGET_SETTINGS_ERROR : 'This widget has an unsupported setting.');
  }
  return params.has('view') ? LATEST : CHANGES;
}

export function widgetUrl(profile, view) {
  const query = new URLSearchParams({areas:profile.core.join(','), nearby:profile.nearby.join(',')});
  if (view === LATEST) query.set('view', LATEST);
  else query.set('days', '30');
  return 'https://scarb.to/embed/?' + query;
}

export function mergeSnapshot(latest, pieces) {
  const basis = pieces[0];
  if (!basis || !hexDigest.test(latest.release_id) || !hexDigest.test(latest.boundary_version) ||
      !hexDigest.test(basis.snapshot_sha256) || !validInstant(latest.checked_at)) {
    throw new TypeError(SNAPSHOT_UNAVAILABLE);
  }
  const records = new Map();
  for (const piece of pieces) {
    if (!piece || piece.schema_version !== 1 || piece.id !== latest.release_id ||
        piece.registry_sha256 !== latest.boundary_version || piece.checked_at !== latest.checked_at ||
        piece.snapshot_sha256 !== basis.snapshot_sha256 || piece.source_url !== SOURCE ||
        piece.licence_url !== LICENCE || piece.upstream_date_as_supplied !== basis.upstream_date_as_supplied ||
        !Array.isArray(piece.records)) {
      throw new TypeError(SNAPSHOT_UNAVAILABLE);
    }
    for (const row of piece.records) {
      if (!row?.id) throw new TypeError(SNAPSHOT_UNAVAILABLE);
      if (records.has(row.id) && canonical(records.get(row.id)) !== canonical(row)) {
        throw new TypeError("The source records disagree. I’m not picking a winner.");
      }
      records.set(row.id, row);
    }
  }
  return {...basis, records:[...records.values()]};
}

function isCalendarDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d\d-\d\d$/.test(value)) return false;
  const date = new Date(value + 'T12:00:00Z');
  return Number.isFinite(date.valueOf()) && date.toISOString().slice(0,10) === value;
}

export function latestInspections(release, profile, registry, now) {
  if (!Array.isArray(release?.records) || !validInstant(release.checked_at) ||
      !validInstant(now) || Date.parse(now) < Date.parse(release.checked_at)) {
    throw new TypeError(SNAPSHOT_UNAVAILABLE);
  }
  const rows = selectCoverage(release.records, profile, registry).map(({record, coverage}) => {
    if (typeof record.id !== 'string' || typeof record.name !== 'string' || !record.name.trim()) {
      throw new TypeError(SNAPSHOT_UNAVAILABLE);
    }
    if (typeof record.status !== 'string' || !record.status.trim() || !isCalendarDate(record.inspection_date)) {
      throw new TypeError("I can’t show that inspection without both the date and the result.");
    }
    return {...record, coverage, sourceUrl:cityDineSafeRecordUrl(record.id)};
  });
  rows.sort((a,b) => (a.coverage === 'nearby') - (b.coverage === 'nearby') ||
    a.name.localeCompare(b.name, 'en-CA') || a.id.localeCompare(b.id, 'en-CA'));
  return {
    rows,
    checkedLabel: 'I last checked: ' + readerDateTime(release.checked_at) + '.',
    upstreamLabel: release.upstream_date_as_supplied ?
      'Date on the City’s data: ' + release.upstream_date_as_supplied + '.' : "The City’s data didn’t come with a date.",
    stale:Date.parse(now) - Date.parse(release.checked_at) > 72 * 3600000,
  };
}

export const NO_INSPECTIONS = "I don’t have an inspection on record for this area. That doesn’t mean nobody’s been inspected.";
export const STALE_INSPECTIONS = "I couldn’t verify anything newer. These are the last records I could check.";
export const INSPECTION_LIMITS = "The date does some heavy lifting here. It tells you what the inspector found that day, not what you’d find if you walked in now. The City may have a newer result.";

export function inspectionLabel(row) {
  const area = row.coverage === 'nearby' ? 'Nearby: ' : '';
  return area + row.name + ' · ' + row.status;
}

export function inspectionListItem(row) {
  const item = document.createElement('li');
  const date = document.createElement('time');
  const link = document.createElement('a');
  date.dateTime = row.inspection_date;
  date.textContent = readerDate(row.inspection_date);
  link.href = row.sourceUrl;
  link.textContent = 'See the City record';
  link.setAttribute('aria-label', 'See the City inspection record for ' + row.name + '.');
  item.append(inspectionLabel(row) + ' on ', date, ' · ', link);
  return item;
}

export function composeLatestProof({snapshot, release, profile, registry, generatedAt, fitsPage}) {
  const {rows, stale, checkedLabel, upstreamLabel} = snapshot;
  const areaNames = [...profile.core,...profile.nearby].map(id=>registry[id].name).join(', ');
  const footer = [
    'City of Toronto DineSafe: ' + SOURCE,
    'Open Government Licence - Toronto: ' + LICENCE,
    'See the records behind this proof: https://scarb.to/community/evidence/?release=' + release.id,
  ].join('\n');
  const lines = [];
  const dates = new Map();
  function proof(length) {
    for (let index = lines.length; index < length; index++) {
      const row = rows[index];
      if (!dates.has(row.inspection_date)) dates.set(row.inspection_date,readerDate(row.inspection_date));
      lines.push(inspectionLabel(row) + ' on ' + dates.get(row.inspection_date) + '\nSee the City record: ' + row.sourceUrl);
    }
    const omitted = rows.length - length;
    const summary = [
      'Last inspections on record in ' + areaNames,
      checkedLabel, upstreamLabel, ...(stale ? [STALE_INSPECTIONS] : []),
      ...[...new Set([...profile.core,...profile.nearby].map(id=>registry[id].coverage_note).filter(Boolean))],
      rows.length ? (fitsPage ? 'I could fit ' + length + ' of ' + rows.length + ' places on this page.' : omitted + ' omitted for space.') : NO_INSPECTIONS,
      INSPECTION_LIMITS,
    ].join('\n');
    const copy = [summary, ...lines.slice(0,length)].join('\n\n').normalize('NFC');
    // Only the text download gets this notice; print and preview retain their copy.
    const textSummary = !fitsPage && omitted ? summary.split('\n').filter(line => line !== omitted + ' omitted for space.').join('\n') : summary;
    const textNotice = omitted === 1 ? '1 more place isn’t shown in this text version.' :
      omitted + ' more places aren’t shown in this text version.';
    const textCopy = [textSummary, ...lines.slice(0,length),
      ...(omitted ? [textNotice + ' See all ' + rows.length + ' on Scarb.TO.'] : []),
    ].join('\n\n').normalize('NFC');
    return {
      textCopy, textCounts:{editorial:counts(textCopy), sources:counts(footer), panel:counts(textCopy+'\n\n'+footer)},
      view:LATEST, print_measured:typeof fitsPage === 'function', profile, generated_at:generatedAt, summary:summary.normalize('NFC'), copy, footer,
      rows:rows.slice(0,length), omitted, counts:{editorial:counts(copy), sources:counts(footer), panel:counts(copy+'\n\n'+footer)},
    };
  }
  function fits(candidate) {
    const {words, characters, scope} = profile.limits;
    return [candidate.counts[scope], candidate.textCounts[scope]].every(tally =>
      (!words || tally.words <= words) && (!characters || tally.characters <= characters)) &&
      (!fitsPage || fitsPage(candidate));
  }
  // The full list needs no text omission notice, so check it before shorter copies.
  const full = proof(rows.length);
  if (fits(full)) return full;
  let selected = proof(0);
  if (!fits(selected)) throw new TypeError("Give the dates and sources a little more room. Try a larger page or a longer copy limit.");
  let low = 1, high = rows.length - 1;
  while (low <= high) {
    const length = Math.floor((low + high) / 2);
    const candidate = proof(length);
    if (fits(candidate)) {
      selected = candidate;
      low = length + 1;
    } else {
      high = length - 1;
    }
  }
  if (rows.length && !selected.rows.length) {
    throw new TypeError("This page won’t fit a whole inspection and its source. Try a larger page or a longer copy limit.");
  }
  return selected;
}