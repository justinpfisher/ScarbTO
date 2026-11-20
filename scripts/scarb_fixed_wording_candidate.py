"""Disabled, offline exact-wording evidence seam. No public reader or trust registry."""
import hashlib
import json
from pathlib import Path
from scripts import scarb_ai_voice as v

ROOT = Path(__file__).resolve().parents[1]
ITEM = 'shell.shell-012700e3-009'
PACKET = 'a26b0c9784ef49578b31def33e9d87337143076f8e32242b6c5f372a187978c6'
SOURCE = 'research/phase1b-csi/fixtures/official-source-contract/scarbto-neighbourhood158-source-contract-2026-10-27.json'
DIRECTORY = 'docs/neighbourhoods/index.html'
DESTINATION = 'docs/agincourt-north/index.html'
PINS = {
    SOURCE: {'0f16bf16cde47f382f21003050a978251f71c258581746d64c9a8c9f5ae8564e'},
    DIRECTORY: {'4093cfecfd3b5958d55397a2983a04eef9576925a90ae8a7dd69b24e7839641f',
                'da63b3bb8c264cf515743bd696eab7069600883da19370e73f46d682c52af369'},
    DESTINATION: {'319b444d39ae5ecb59fc60a263373fb68e54a8cd9c8c445b6c6904a754de27ed',
                  'da5a2786ba781e0e370ff8231f5feba8a9bace623784c393002ca5f9993d1cc1'},
}


def _source(path):
    raw = (ROOT / path).read_bytes()
    v.need(hashlib.sha256(raw).hexdigest() in PINS[path], 'Fixed wording source changed')
    return raw


def exact_binding(packet):
    v.need(packet['id'] == ITEM and packet['kind'] == 'functional'
           and v.digest(packet) == PACKET, 'Unknown or changed fixed packet')
    rows = [row for row in json.loads(_source(SOURCE))['registry']
            if row['AREA_SHORT_CODE'] == '129']
    v.need(len(rows) == 1 and rows[0]['AREA_NAME'] == packet['draft'], 'Registry name differs')
    route = '/agincourt-north/'
    anchor = f'<a href="{route}">{packet["draft"]}</a>'.encode()
    v.need(_source(DIRECTORY).count(anchor) == 1, 'Fixed wording consumer differs')
    _source(DESTINATION)
    return {'id': ITEM, 'packet_sha256': PACKET, 'text': packet['draft'], 'locks': packet['locks'],
            'official_registry_code': '129', 'route': route,
            'files': {path: sorted(digests) for path, digests in PINS.items()}}


def verify_fixed_evidence(packet, record, independent_sha256, *, excluded_ids):
    """Caller must independently authenticate the exact reviewed record pin and exclusions."""
    v.need(isinstance(excluded_ids, frozenset) and ITEM not in excluded_ids,
           'Fixed item excluded by existing history')
    v.need(independent_sha256 and v.digest(record) == independent_sha256,
           'Exact independent fixed wording record required')
    v.need(record == {'version': 'scarb-fixed-wording-review-1', 'decision': 'verified-unchanged',
                      'binding': exact_binding(packet)}, 'Fixed wording evidence differs')
    return {'text': record['binding']['text'], 'packet_sha256': PACKET,
            'receipt_sha256': independent_sha256, 'origin': 'scarb-fixed-wording-review-1'}


def require_complete_partition(canonical, editorial, fixed):
    """Sets of exact catalogue IDs from already-verified, independent evidence lanes."""
    v.need(len(canonical) == 736 and not (editorial & fixed)
           and (editorial | fixed) == canonical, 'Complete disjoint 736-item catalogue required')
