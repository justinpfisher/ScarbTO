const RESOURCE_ID = "8102bd4c-83cd-4354-9788-eecc0c7a09b4";
const BEACH_ID = 10;
const EXPECTED_COORDINATES = [-79.2252, 43.7141];
const RECORD_KEYS = ["beachId", "beachName", "siteName", "collectionDate", "eColi"];
const PREVIEW_KEYS = ["schema_version", "source", "source_url", "licence_url", "resource_id", "beach_id", "beach_name", "coordinates", "selection", "total_rows_in_source_filter", "total_was_estimated", "rows_included", "retrieved_on", "coverage_note", "records"];
const CATALOGUE_URL = "https://open.toronto.ca/dataset/toronto-beaches-water-quality/";
const LICENCE_URL = "https://open.toronto.ca/open-data-licence/";
const CURRENT_INFO_URL = "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/beach-water-quality/";

function isCalendarDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}

export function validateBeachSamplePreview(input) {
  if (!input || typeof input !== "object" || input.schema_version !== 1
      || Object.keys(input).sort().join(",") !== [...PREVIEW_KEYS].sort().join(",")
      || input.resource_id !== RESOURCE_ID || input.beach_id !== BEACH_ID
      || input.total_was_estimated !== false || !Number.isInteger(input.total_rows_in_source_filter)
      || input.total_rows_in_source_filter < 1 || !Array.isArray(input.records)
      || input.records.length < 1 || input.records.length > 10
      || input.total_rows_in_source_filter < input.records.length
      || input.rows_included !== input.records.length
      || typeof input.retrieved_on !== "string" || !isCalendarDate(input.retrieved_on)
      || !Array.isArray(input.coordinates) || input.coordinates.length !== 2
      || input.coordinates.some((value, index) => value !== EXPECTED_COORDINATES[index])) {
    throw new TypeError("Invalid bounded Toronto beach-sample preview");
  }
  for (const record of input.records) {
    if (!record || typeof record !== "object"
        || Object.keys(record).sort().join(",") !== [...RECORD_KEYS].sort().join(",")
        || record.beachId !== BEACH_ID || record.beachName !== "Bluffer's Beach Park"
        || typeof record.siteName !== "string" || !record.siteName.trim()
        || !isCalendarDate(record.collectionDate)
        || (record.eColi !== null && (!Number.isFinite(record.eColi) || record.eColi < 0))) {
      throw new TypeError("Invalid beach-sample record");
    }
  }
  return input;
}

export function beachPreviewFeature(input) {
  const preview = validateBeachSamplePreview(input);
  return {
    type: "Feature",
    id: "beach:10",
    geometry: { type: "Point", coordinates: [...preview.coordinates] },
    properties: { id: "beach:10", name: preview.beach_name, status: "Beach sample", activity: false, selected: true },
  };
}

export function renderBeachMeasurementHistory(document, input) {
  const preview = validateBeachSamplePreview(input);
  const section = document.createElement("section");
  section.className = "beach-sample-preview";
  const title = document.createElement("h3");
  title.textContent = `${preview.beach_name} sample history`;
  const note = document.createElement("p");
  note.textContent = `Latest ${preview.rows_included} catalogue rows shown, selected from ${preview.total_rows_in_source_filter.toLocaleString("en-CA")} rows for this beach. This is a limited sample preview, not a complete history or current swimming advice. Measurements are grouped by their sample collection date; the map pin marks the beach reference point, not sample-site coordinates. Contains information licensed under the Open Government Licence - Toronto.`;
  const byDate = new Map();
  for (const record of preview.records) {
    if (!byDate.has(record.collectionDate)) byDate.set(record.collectionDate, []);
    byDate.get(record.collectionDate).push(record);
  }
  const days = document.createElement("div");
  days.className = "beach-sample-days";
  for (const [collectionDate, dayRecords] of [...byDate.entries()].sort(([left], [right]) => right.localeCompare(left))) {
    const day = document.createElement("section");
    day.className = "beach-sample-day";
    const heading = document.createElement("h4");
    const date = document.createElement("time");
    date.dateTime = collectionDate;
    date.textContent = collectionDate;
    heading.append(date);
    const records = document.createElement("ol");
    records.className = "beach-sample-preview-list";
    for (const record of [...dayRecords].sort((left, right) => left.siteName.localeCompare(right.siteName))) {
      const item = document.createElement("li");
      const site = document.createElement("span");
      site.textContent = `Site ${record.siteName}`;
      const measurement = document.createElement("span");
      measurement.textContent = record.eColi === null
        ? "No numeric E. coli measurement recorded"
        : `E. coli measurement: ${record.eColi}`;
      item.append(site, measurement);
      records.append(item);
    }
    day.append(heading, records);
    days.append(day);
  }
  const captured = document.createElement("p");
  captured.className = "beach-sample-preview-meta";
  captured.textContent = `Catalogue preview retrieved ${preview.retrieved_on}. Latest sample date: ${preview.records.reduce((latest, row) => row.collectionDate > latest ? row.collectionDate : latest, "0000-00-00")}.`;
  const source = document.createElement("a");
  source.href = CATALOGUE_URL;
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  source.textContent = "Toronto Open Data source";
  const licence = document.createElement("a");
  licence.href = LICENCE_URL;
  licence.target = "_blank";
  licence.rel = "noopener noreferrer";
  licence.textContent = "Toronto Open Data Licence";
  const currentInfo = document.createElement("a");
  currentInfo.href = CURRENT_INFO_URL;
  currentInfo.target = "_blank";
  currentInfo.rel = "noopener noreferrer";
  currentInfo.textContent = "Official current beach information";
  section.append(title, note, days, captured, source, licence, currentInfo);
  return section;
}

// Keep the existing app call site compatible while exposing the dated-history view explicitly.
export const renderBeachSamplePreview = renderBeachMeasurementHistory;
