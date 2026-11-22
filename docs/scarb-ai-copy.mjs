/** Accepted-copy lookup for existing JS producers. No API key, inference or I/O.
 * Python generators can use the same compiled JSON after compile_catalogue().
 * Callers obtain expected packet hashes from their exact current request manifest,
 * never from the catalogue being checked. Missing/new inputs hold publication.
 */
import fixedPins from './scarb-fixed-wording-pins.mjs';
import directoryPins from './scarb-fixed-directory-pins.mjs';
import layoutPins from './scarb-fixed-community-layout-pins.mjs';
import editionPins from './scarb-fixed-community-edition-pins.mjs';

export function createScarbAiResolver(catalogue, expected) {
  const editionVersion = catalogue?.version === 'scarb-ai-voice-mixed-5';
  const layoutVersion = editionVersion || catalogue?.version === 'scarb-ai-voice-mixed-4';
  const directoryVersion = layoutVersion || catalogue?.version === 'scarb-ai-voice-mixed-3';
  const fixedVersion = directoryVersion || catalogue?.version === 'scarb-ai-voice-mixed-2';
  const mixed = fixedVersion || catalogue?.version === 'scarb-ai-voice-mixed-1';
  const pins = {
    ...(fixedVersion ? fixedPins : {}),
    ...(directoryVersion ? directoryPins : {}),
    ...(layoutVersion ? layoutPins : {}),
    ...(editionVersion ? editionPins : {}),
  };
  if ((!mixed && catalogue?.version !== 'scarb-ai-voice-1') || !catalogue.entries || !expected ||
      Object.keys(catalogue.entries).length !== Object.keys(expected).length ||
      (mixed && Object.keys(expected).length !== 736) ||
      !Object.keys(pins).every(id => Object.hasOwn(expected, id))) {
    throw new Error('AI copy catalogue does not match the qualified request manifest');
  }
  const entries = new Map();
  for (const [id, hash] of Object.entries(expected)) {
    const entry = catalogue.entries[id];
    const p = entry?.provenance;
    const fixed = Object.hasOwn(pins, id) ? pins[id] : null;
    const fixedOk = fixed && entry?.origin === 'scarb-fixed-wording-review-1' && p == null &&
      fixed.packet_sha256 === hash && fixed.receipt_sha256 === entry.receipt_sha256 &&
      fixed.text === entry.text;
    const groupOk = mixed && p && p.manifest_sha256 === entry?.receipt_sha256 && p.packet_id === id && (
      (entry.origin === 'scarb-grouped-projection-2' && Object.keys(p).length === 3 &&
        p.version === 'scarb-grouped-run-envelope-2') ||
      (entry.origin === 'scarb-grouped-projection-3' && Object.keys(p).length === 4 &&
        p.version === 'scarb-grouped-run-envelope-3' && p.prompt_version === 'numeric-citation-2'));
    const editorialOk = groupOk || (['openai-api-reviewed','protected-verbatim'].includes(entry?.origin) && (!mixed || p == null));
    if (!/^[a-f0-9]{64}$/.test(hash) || entry?.packet_sha256 !== hash ||
        !/^[a-f0-9]{64}$/.test(entry.receipt_sha256) || typeof entry.text !== 'string' || !entry.text ||
        !(fixed ? fixedOk : editorialOk)) {
      throw new Error('Unaccepted or stale AI copy: ' + id);
    }
    entries.set(id, Object.freeze({...entry}));
  }
  return id => {
    if (!entries.has(id)) throw new Error('Public copy has not passed the AI gateway: ' + id);
    return entries.get(id).text;
  };
}
