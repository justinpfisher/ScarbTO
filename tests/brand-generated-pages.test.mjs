import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildPageFiles,normalizeGeneratedText} from '../scripts/build_neighbourhood_pages.mjs';

const repoRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));

test('all generated neighbourhood routes match the published page files', async () => {
  // Canonicalize only checkout newlines in the two file inputs, not generated output.
  const template = normalizeGeneratedText(await readFile(resolve(repoRoot, 'docs/neighbourhood-page.template.html'), 'utf8'));
  const generated = buildPageFiles(undefined, template);
  assert.equal(generated.size, 32);
  for (const [relativePath, expected] of generated) {
    const published = await readFile(resolve(repoRoot, relativePath), 'utf8');
    assert.equal(normalizeGeneratedText(published), expected, `${relativePath} must match the authoritative template`);
  }
});
