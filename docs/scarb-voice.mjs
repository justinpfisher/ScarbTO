/**
 * Approved Scarb-authored copy gateway. Pure and deterministic: no network,
 * runtime AI, source mutation or free-form factual rewriting.
 * See SCARB_VOICE_GATEWAY.md before adding a new public copy path.
 */
export const VOICE_REVISION = '2026-11-17-2x';

export const SCARB_COPY = Object.freeze({
  'home-title': "Scarborough has a lot of stories hiding in its data.",
  'home-intro': "I can lose an afternoon following Scarborough's maps and public records. I've brought the places, inspection results and neighbourhood boundaries together here, with their dates and sources. Pick a thread. Let's see where it leads.",
  'home-boundaries': "Here's a favourite Scarborough map quirk: City wards and neighbourhoods don't always line up. Try either boundary to narrow the food inspection map and list. Beach samples and police division totals use different areas.",
  'neighbourhood-intro': "Now this is a patch of Scarborough worth getting to know. I've put the food inspection records and City neighbourhood boundaries for {{NAME}} side by side. Start with a familiar place, then follow the source links. There's often another detail worth checking.",
  'directory-intro': "Right now this map selection has {{COUNT}} City neighbourhoods, each with its own page. Pick one and I'll show you the boundaries, recorded inspections and source links. I find it's the little geographic details that make this especially interesting.",
  'community-title': "Let's turn local records into a neighbourhood update.",
  'community-intro': "There's a lot tucked away in Scarborough's public records. Choose your patch and I'll bring the dated, source-linked findings together for print or your website. The evidence stays attached; you decide what to share.",
  'community-coverage': "A little map nerdiness before we begin: City neighbourhoods don't always stay inside Scarborough's six ward boundaries. For DineSafe, I count only records inside those wards, even if a selected neighbourhood carries on beyond them. These are editorial selections, not claimed newspaper or association territories.",
  'community-core': "Your corner of Scarborough",
  'evidence-title': "Let's follow the paper trail.",
  'evidence-intro': "Now for one of my favourite parts: where did this edition's information actually come from? Here's the saved source release, its dates and what those records can tell us. This page doesn't publicly store a publisher's own wording; import the finalised receipt to inspect the exact edition.",
  'embed-title': "Local discoveries, with the receipts.",
  'embed-intro': "Here's what the records turned up for this area. I keep the source dates and links close by, because the trail behind a finding can be just as interesting as the finding itself.",
  'briefs-title': "The week's food inspection paper trail.",
  'briefs-intro': "I love seeing how one week's DineSafe records fit together. Pick an edition and follow the inspection dates, neighbourhood connections and original source links. A quiet week in these records isn't proof that nothing happened, and I only publish a brief when there are updates to share.",
  'editor-start': "Choose your neighbourhoods and reporting dates. Experiment with drafts all you like: your next edition starts after the last one you finalised, not after a preview or text download.",
  'missing-pdf-tools': "The PDF tools didn't load. You can still save the text and settings before reloading to try again; a finalised receipt is available only after finalisation succeeds."
});

const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const required = (value, field) => {
  if (typeof value !== 'string' || !value.trim()) throw new TypeError('Missing verified voice fact: ' + field);
  return value;
};

/** The caller escapes interpolated text for HTML; use textContent for DOM. */
export function staticCopy(key, fields = {}) {
  if (!own(SCARB_COPY, key)) throw new TypeError('Unregistered Scarb copy: ' + key);
  return SCARB_COPY[key].replace(/\{\{([A-Z]+)\}\}/g, (_, name) => {
    if (!own(fields, name) || !['string', 'number'].includes(typeof fields[name])) {
      throw new TypeError('Missing copy field: ' + name);
    }
    return String(fields[name]);
  });
}

/** Source-backed narrative only. No invention of discoveries or openings. */
export function communityVoice(kind, facts = {}) {
  switch (kind) {
    case 'heading':
      return "Here's what turned up in the DineSafe records for " + required(facts.name, 'name');
    case 'period':
      return "Here's the time window I checked: information added " +
        (facts.inclusive ? 'from ' : 'after ') + required(facts.start, 'start') +
        ' through ' + required(facts.end, 'end') +
        '. The inspections themselves may have happened earlier; I show each inspection date separately.';
    case 'event': {
      const name = required(facts.name, 'name');
      const status = required(facts.status, 'status');
      const inspected = required(facts.inspected, 'inspection date');
      const recorded = required(facts.recorded, 'first-recorded date');
      const prefix = facts.nearby ? 'From nearby: ' : '';
      let observation;
      if (facts.eventKind === 'first_seen') {
        observation = name + ' appeared in the records I checked for the first time (not a confirmed opening).';
      } else if (facts.eventKind === 'status_changed' && facts.previousStatus) {
        observation = 'A change worth checking in the original record: ' + name +
          ' moved from a recorded ' + required(facts.previousStatus, 'previous status') +
          ' to ' + status + '.';
      } else {
        observation = 'Another dated inspection update turned up for ' + name + '.';
      }
      return prefix + observation + ' DineSafe recorded ' + status + ' for the inspection on ' +
        inspected + '. Scarb.TO first recorded this information on ' + recorded + '.';
    }
    case 'boundary-note': {
      const note = required(facts.note, 'boundary note');
      const standard = 'Only records inside the qualified six Scarborough wards are included. City neighbourhoods can cross those wards; this is not necessarily a whole-neighbourhood total.';
      if (note === standard) {
        return "Here's an interesting boundary wrinkle: some neighbourhoods cross Scarborough's six City ward lines. I count only DineSafe records inside those wards, so this may be a slice of a neighbourhood, not its whole total.";
      }
      return 'A boundary detail worth keeping in view: ' + note;
    }
    case 'limitations':
      return "One detail I never want to skip: these dated inspection results are not restaurant ratings or a guarantee of conditions today. Check the official DineSafe record for anything newer.";
    case 'stale':
      return "I couldn't check for anything newer than " + required(facts.checked, 'last checked') +
        '. This edition does not cover later information.';
    case 'changed':
      return "The selected areas or settings changed since the previous edition. That makes this a different view of the records, not a like-for-like comparison.";
    case 'snapshot':
      if (!Number.isSafeInteger(facts.count) || facts.count < 0) throw new TypeError('Invalid record count');
      return "Here's a useful bit of context: this selection contains " + facts.count +
        ' DineSafe establishment source records from the snapshot checked ' +
        required(facts.checked, 'last checked') +
        ". That's not the number of changes during this period, or necessarily the number of distinct businesses.";
    case 'empty':
      return "Well, this is interesting in its own quiet way: I found no new updates in the DineSafe records checked for these areas and dates. That doesn't mean nothing happened. The source dates above show exactly what I checked.";
    case 'embed-summary': {
      const {shown, eligible, omitted} = facts;
      if (![shown, eligible, omitted].every(n => Number.isSafeInteger(n) && n >= 0) || shown > eligible) {
        throw new TypeError('Invalid validated update counts');
      }
      return shown + ' dated updates shown from ' + eligible + ' eligible records.' +
        (omitted ? ' ' + omitted + ' left out to fit the chosen space.' : '') +
        " Here's the boundary wrinkle: DineSafe coverage is limited to records inside Scarborough's six City wards, even if a selected neighbourhood extends beyond them.";
    }
    default:
      throw new TypeError('Unregistered Scarb composition: ' + kind);
  }
}
