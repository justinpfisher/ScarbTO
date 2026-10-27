import assert from "node:assert/strict";
import { createBeachStatusCard } from "../web/beach-status-view.mjs";

function fakeDocument() {
  return {
    createElement(tag) {
      return {
        tag,
        children: [],
        append(...items) { this.children.push(...items); this.childNodes = this.children; },
        textContent: "",
        href: "",
        target: "",
        rel: "",
        className: "",
      };
    },
  };
}

const injected = "<img src=x onerror=alert(1)>";
const current = createBeachStatusCard(fakeDocument(), {
  beach_name: "Synthetic Beach",
  display_state: "current",
  water_quality_status: "caution",
  advisory: injected,
  sample_date: "2026-07-15",
  source_update_raw: "2026-07-15 10:19:11",
  fetched_at_utc: "2026-07-15T16:00:00Z",
});
assert.equal(current.tag, "section");
assert.equal(current.children[0].textContent, "Synthetic Beach");
assert.equal(current.children[1].textContent, "Official water-quality status: Caution is advised");
assert.equal(current.children[1].innerHTML, undefined);
assert.equal(current.children[2].children[1].textContent, "2026-07-15");
assert.equal(current.children[2].children[3].textContent, "2026-07-15 10:19:11");
assert.equal(current.children[2].children[5].textContent, "2026-07-15T16:00:00Z");
assert.equal(current.children[3].textContent, injected);
assert.equal(current.children[3].innerHTML, undefined);
assert.equal(current.children[4].href, "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/beach-water-quality/");
assert.equal(current.children[4].rel, "noopener noreferrer");

const offseason = createBeachStatusCard(fakeDocument(), {
  beach_name: "Bluffer's Beach Park",
  display_state: "out_of_season",
  water_quality_status: null,
});
assert.match(offseason.children[1].textContent, /out of season/i);

const unknown = createBeachStatusCard(fakeDocument(), {
  display_state: "status_unrecognized",
  water_quality_status: null,
});
assert.match(unknown.children[1].textContent, /unrecognized status/i);

console.log("Beach view tests passed (3 cases)");

