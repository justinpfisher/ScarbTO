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
assert.match(rendered.children[1].textContent, /not current swimming advice/i);
assert.match(rendered.children[1].textContent, /10,300 rows/);
assert.equal(rendered.children[2].children.length, 10);
assert.match(rendered.children[2].children[0].children[0].textContent, /^2026-09-16$/);
assert.match(rendered.children[2].children[0].children[2].textContent, /No numeric E\. coli measurement recorded/);
assert.equal(rendered.children[4].href, "https://open.toronto.ca/dataset/toronto-beaches-water-quality/");
assert.equal(rendered.children[5].href, "https://open.toronto.ca/open-data-licence/");
assert.equal(rendered.children[6].href, "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/beach-water-quality/");
assert.ok(rendered.children.every(child => child.innerHTML === undefined));

for (const mutate of [
  value => { value.resource_id = "other"; },
  value => { value.coordinates[0] = -79.2; },
  value => { value.total_was_estimated = true; },
  value => { value.records[0].statusFlag = "SAFE"; },
  value => { value.records[0].collectionDate = "2026-02-30"; },
]) {
  const changed = structuredClone(preview);
  mutate(changed);
  assert.throws(() => validateBeachSamplePreview(changed), TypeError);
}

console.log("Beach history app integration tests passed");

