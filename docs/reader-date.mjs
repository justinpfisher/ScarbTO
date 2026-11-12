/** Reader dates keep source-only calendar dates intact; only zoned instants
 * are converted to Toronto time. Original values stay in the source data. */
function parsedDate(value) {
  if (typeof value !== 'string') return null;
  const match = value.trim().match(/^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(Z|[+-]\d{2}:\d{2})?)?$/);
  if (!match) return null;
  const [, day, hour, minute, second, zone] = match;
  const calendar = new Date(day + 'T12:00:00Z');
  if (!Number.isFinite(calendar.valueOf()) || calendar.toISOString().slice(0,10) !== day) return null;
  if (hour !== undefined && (Number(hour) > 23 || Number(minute) > 59 || Number(second || 0) > 59)) return null;
  if (!zone) return {date:calendar, timeZone:'UTC', hasTime:false};
  const date = new Date(value.trim().replace(' ', 'T'));
  return Number.isFinite(date.valueOf()) ? {date, timeZone:'America/Toronto', hasTime:true} : null;
}

function format(value, includeTime) {
  const parsed = parsedDate(value);
  if (!parsed) return 'Date unavailable';
  return new Intl.DateTimeFormat('en-US', {
    timeZone:parsed.timeZone, weekday:'long', month:'long', day:'numeric', year:'numeric',
    ...(includeTime && parsed.hasTime ? {hour:'numeric', minute:'2-digit', timeZoneName:'short'} : {}),
  }).format(parsed.date);
}

export function readerDate(value) { return format(value, false); }
export function readerDateTime(value) { return format(value, true); }
