const CATALOGUE_URL = "https://open.toronto.ca/dataset/toronto-beaches-water-quality/";
const MAX_VISIBLE_RECORDS = 50;

/** Render a complete, validated catalogue snapshot as dated measurements only.
 * This component deliberately has no map, health label, status inference or fetch.
 */
export function createBeachMeasurementHistory(document, snapshot) {
  if (snapshot?.resource_id !== "8102bd4c-83cd-4354-9788-eecc0c7a09b4"
      || snapshot?.beach_id !== 10
      || !Array.isArray(snapshot.records)
      || snapshot.row_count !== snapshot.records.length
      || typeof snapshot.sha256 !== "string") {
    throw new TypeError("A complete validated Bluffer's Beach measurement snapshot is required");
  }
  const section = document.createElement("section");
  section.className = "beach-measurement-history";
  const heading = document.createElement("h3");
  heading.textContent = "Bluffer's Beach Park sample history";
  const explanation = document.createElement("p");
  explanation.textContent = `Dated catalogue measurements only; not current swimming advice. ${snapshot.row_count} records in this snapshot.`;
  section.append(heading, explanation);

  const list = document.createElement("ol");
  list.className = "beach-measurement-list";
  const records = [...snapshot.records].sort((left, right) =>
    right.collectionDate.localeCompare(left.collectionDate)
      || left.siteName.localeCompare(right.siteName)
      || left._id - right._id,
  );
  for (const record of records.slice(0, MAX_VISIBLE_RECORDS)) {
    const item = document.createElement("li");
    const date = document.createElement("time");
    date.dateTime = record.collectionDate;
    date.textContent = record.collectionDate;
    const measurement = document.createElement("span");
    measurement.textContent = record.eColi === null
      ? `${record.siteName}: no numeric eColi measurement recorded`
      : `${record.siteName}: eColi ${record.eColi}`;
    item.append(date, measurement);
    list.append(item);
  }
  section.append(list);
  if (records.length > MAX_VISIBLE_RECORDS) {
    const note = document.createElement("p");
    note.textContent = `Showing ${MAX_VISIBLE_RECORDS} of ${records.length} dated records.`;
    section.append(note);
  }
  const source = document.createElement("a");
  source.href = CATALOGUE_URL;
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  source.textContent = "Open the Toronto Open Data dataset";
  section.append(source);
  return section;
}
