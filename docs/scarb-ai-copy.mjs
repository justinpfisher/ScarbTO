/** Accepted-copy lookup for existing JS producers. No API key, inference or I/O.
 * Python generators can use the same compiled JSON after compile_catalogue().
 * Callers obtain expected packet hashes from their exact current request manifest,
 * never from the catalogue being checked. Missing/new inputs hold publication.
 */
export function createScarbAiResolver(catalogue, expected) {
  if (catalogue?.version !== 'scarb-ai-voice-1' || !catalogue.entries || !expected ||
      Object.keys(catalogue.entries).length !== Object.keys(expected).length) {
    throw new Error('AI copy catalogue does not match the qualified request manifest');
  }
  const entries = new Map();
  for (const [id, hash] of Object.entries(expected)) {
    const entry = catalogue.entries[id];
    if (!/^[a-f0-9]{64}$/.test(hash) || entry?.packet_sha256 !== hash ||
        !/^[a-f0-9]{64}$/.test(entry.receipt_sha256) || typeof entry.text !== 'string' || !entry.text ||
        !['openai-api-reviewed','protected-verbatim'].includes(entry.origin)) {
      throw new Error('Unaccepted or stale AI copy: ' + id);
    }
    entries.set(id, Object.freeze({...entry}));
  }
  return id => {
    if (!entries.has(id)) throw new Error('Public copy has not passed the AI gateway: ' + id);
    return entries.get(id).text;
  };
}
