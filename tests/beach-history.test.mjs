import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { beachPreviewFeature, renderBeachMeasurementHistory, validateBeachSamplePreview } from "../docs/beach-history.mjs";

const preview = JSON.parse(await readFile(new URL("../docs/data/beach-sample-preview.json", import.meta.url), "utf8"));

function fakeDocument() {
  return {
    createElement(tag) {
      return {
        tag, children: [], textContent: "", className: "", href: "", target: "", rel: "", dateTime: "",
        append(...items) { this.children.push(...items); },
      };
    },
  };
}

assert.equal(validateBeachSamplePreview(preview), preview);
const feature = beachPreviewFeature(preview);
assert.equal(feature.id, "beach:10");
assert.deepEqual(feature.geometry.coordinates, [-79.2252, 43.7141]);
assert.equal(feature.properties.status, "Beach sample");

const rendered = renderBeachMeasurementHistory(fakeDocument(), preview);
assert.equal(rendered.children[0].textContent, "Bluffer's Beach Park sample history");
assert.match(rendered.children[1].textContent, /not a complete history or current swimming advice/i);
assert.match(rendered.children[1].textContent, /10,300 rows/);
assert.equal(rendered.children[2].children.length, 2, "records are grouped into dated sample collections");
assert.equal(rendered.children[2].children[0].children[0].children[0].dateTime, "2026-09-16");
assert.equal(rendered.children[2].children[0].children[1].children.length, 5);
assert.match(rendered.children[2].children[0].children[1].children[0].children[1].textContent, /No numeric E\. coli measurement recorded/);
assert.equal(rendered.children[4].href, "https://open.toronto.ca/dataset/toronto-beaches-water-quality/");
assert.equal(rendered.children[5].href, "https://open.toronto.ca/open-data-licence/");
assert.equal(rendered.children[6].href, "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/beach-water-quality/");
assert.ok(rendered.children.every(child => child.innerHTML === undefined));

const syntheticPreview = {
  ...preview,
  retrieved_on: "2026-10-28",
  selection: "synthetic fixture only",
  total_rows_in_source_filter: 3,
  rows_included: 3,
  records: [
    {beachId: 10, beachName: "Bluffer's Beach Park", siteName: "Synthetic Site B", collectionDate: "2026-10-02", eColi: 31},
    {beachId: 10, beachName: "Bluffer's Beach Park", siteName: "Synthetic Site A", collectionDate: "2026-10-02", eColi: null},
    {beachId: 10, beachName: "Bluffer's Beach Park", siteName: "Synthetic Site C", collectionDate: "2026-10-01", eColi: 5},
  ],
};
const syntheticView = renderBeachMeasurementHistory(fakeDocument(), syntheticPreview);
assert.equal(syntheticView.children[2].children[0].children[0].children[0].dateTime, "2026-10-02");
assert.match(syntheticView.children[2].children[0].children[1].children[0].children[0].textContent, /Synthetic Site A/);
assert.match(syntheticView.children[2].children[0].children[1].children[0].children[1].textContent, /No numeric/);
assert.match(syntheticView.children[2].children[0].children[1].children[1].children[1].textContent, /E\. coli measurement: 31/);
assert.doesNotMatch(JSON.stringify(syntheticView), /unsafe|safe to swim|advisory/i, "measurements never become a safety classification");

for (const mutate of [
  value => { value.resource_id = "other"; },
  value => { value.coordinates[0] = -79.2; },
  value => { value.total_was_estimated = true; },
  value => { value.total_rows_in_source_filter = 1; },
  value => { value.records[0].statusFlag = "SAFE"; },
  value => { value.statusFlag = "Safe to swim"; },
  value => { value.advisory = "Current conditions"; },
  value => { value.records[0].collectionDate = "2026-02-30"; },
]) {
  const changed = structuredClone(preview);
  mutate(changed);
  assert.throws(() => validateBeachSamplePreview(changed), TypeError);
}

console.log("Beach history app integration tests passed");
