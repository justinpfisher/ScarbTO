import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { beachPreviewFeature, renderBeachSamplePreview, validateBeachSamplePreview } from "../docs/beach-history.mjs";

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

const rendered = renderBeachSamplePreview(fakeDocument(), preview);
assert.equal(rendered.children[0].textContent, "Bluffer's Beach Park");
assert.equal(rendered.children[1].textContent, "These are older water samples, not today’s swimming conditions. Check the City’s latest advice before swimming.");
assert.equal(rendered.children[2].href, "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/beach-water-quality/");
const dates = rendered.children[3];
assert.equal(dates.children.length, 2, "Bluffer's ten records are grouped into two useful dates");
assert.equal(dates.children[0].children[0].textContent, "Wednesday, September 16, 2026");
assert.equal(dates.children[1].children[0].textContent, "Tuesday, September 8, 2026");
assert.equal(dates.children[0].children[1].textContent, "5 sample records. None includes an E. coli number. A missing number is not a zero.");
const details = rendered.children[4];
assert.equal(details.tag, "details");
assert.equal(details.open, undefined, "technical/source details start collapsed");
assert.match(details.children[1].textContent, /out of 10,300 for this beach/);
const records = details.children[2];
assert.equal(records.children.length, 10);
for (let index = 0; index < preview.records.length; index++) {
  assert.equal(records.children[index].children[0].dateTime, preview.records[index].collectionDate);
  assert.equal(records.children[index].children[1].textContent, `Site ${preview.records[index].siteName}`);
  assert.equal(records.children[index].children[2].textContent, "No E. coli number was recorded");
}
assert.match(details.children[3].textContent, /Tuesday, October 27, 2026/);
assert.equal(details.children[4].href, "https://open.toronto.ca/dataset/toronto-beaches-water-quality/");
assert.equal(details.children[5].href, "https://open.toronto.ca/open-data-licence/");
assert.ok(rendered.children.every(child => child.innerHTML === undefined));

const mixed = structuredClone(preview);
mixed.records[0].eColi = 0;
mixed.records[1].eColi = 7;
const mixedRendered = renderBeachSamplePreview(fakeDocument(), mixed);
assert.equal(mixedRendered.children[3].children[0].children[1].textContent,
  "5 sample records. Recorded E. coli numbers: 0, 7. 3 records have no E. coli number. A missing number is not a zero.");
assert.equal(mixedRendered.children[4].children[2].children[0].children[2].textContent, "E. coli measurement: 0");
assert.equal(mixedRendered.children[4].children[2].children[2].children[2].textContent, "No E. coli number was recorded");
assert.deepEqual(preview.records.map(row => row.eColi), Array(10).fill(null), "rendering does not fill missing source numbers");

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
