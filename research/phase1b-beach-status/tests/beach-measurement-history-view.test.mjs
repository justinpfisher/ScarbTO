import assert from "node:assert/strict";
import { createBeachMeasurementHistory } from "../web/beach-measurement-history-view.mjs";

function fakeDocument() {
  return {
    createElement(tag) {
      return {
        tag, children: [], textContent: "", className: "", href: "", target: "", rel: "",
        append(...items) { this.children.push(...items); },
      };
    },
  };
}

function snapshot(records) {
  return {
    resource_id: "8102bd4c-83cd-4354-9788-eecc0c7a09b4",
    beach_id: 10,
    row_count: records.length,
    sha256: "synthetic-digest",
    records,
  };
}

const view = createBeachMeasurementHistory(fakeDocument(), snapshot([
  {_id: 1, beachId: 10, beachName: "Bluffer's Beach Park", siteName: "50E", collectionDate: "2026-09-08", eColi: null},
  {_id: 2, beachId: 10, beachName: "Bluffer's Beach Park", siteName: "49E", collectionDate: "2026-09-16", eColi: 17},
]));
assert.equal(view.children[0].textContent, "Bluffer's Beach Park sample history");
assert.match(view.children[1].textContent, /not current swimming advice/i);
assert.match(view.children[2].children[0].children[0].textContent, /2026-09-16/);
assert.match(view.children[2].children[0].children[1].textContent, /eColi 17/);
assert.match(view.children[2].children[1].children[1].textContent, /no numeric eColi measurement recorded/);
assert.equal(view.children.at(-1).href, "https://open.toronto.ca/dataset/toronto-beaches-water-quality/");
assert.equal(view.children.at(-1).rel, "noopener noreferrer");

assert.throws(() => createBeachMeasurementHistory(fakeDocument(), {
  ...snapshot([{_id: 1}]), row_count: 2,
}), /complete validated/);

const tooMany = snapshot(Array.from({length: 51}, (_, i) => ({
  _id: i + 1, beachId: 10, beachName: "Bluffer's Beach Park", siteName: "49E",
  collectionDate: `2026-09-${String(16 - (i % 15)).padStart(2, "0")}`, eColi: null,
})));
const bounded = createBeachMeasurementHistory(fakeDocument(), tooMany);
assert.equal(bounded.children[2].children.length, 50);
assert.match(bounded.children[3].textContent, /Showing 50 of 51/);

console.log("Beach measurement history view tests passed");
