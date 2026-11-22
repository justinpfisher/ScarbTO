"""Isolated offline grouped-projection compiler seam, never production authority.

The current v1/v2 admission contracts remain untouched. Synthetic provenance
cannot qualify a new production contract merely because its bytes are complete.
"""
from scripts import scarb_ai_voice as v
from scripts import scarb_grouped_fixture_envelope as group

VERSION='scarb-grouped-projection-seam-1'

def compile_projection_fixture(packets, models, current_manifest, scope, envelopes, projections):
    """Require a complete current fixture catalogue, not a caller-shortened subset.

    scope is an explicit synthetic test expectation, not a production grant.
    Results retain a fixture-only origin rejected by the production resolver.
    """
    v.need(scope.get('origin')=='test-fixture-scope' and scope.get('version')==VERSION,
           'No grouped production eligibility is established')
    expected={p['id']:v.digest(p) for p in packets}
    v.need(len(expected)==len(packets) and expected==current_manifest,
           'Full current request manifest required')
    v.need(set(scope)=={'version','origin','manifest','models','envelope_hashes'}
           and scope['manifest']==current_manifest and scope['models']==models,
           'Exact fixture scope/model/current version mismatch')
    v.need(isinstance(envelopes,dict) and set(envelopes)==set(scope['envelope_hashes']),
           'Complete pinned envelope set required')
    v.need(isinstance(projections,dict) and set(projections)==set(expected),
           'Missing or extra current projection')
    membership={}
    for digest,envelope in envelopes.items():
        v.need(digest==envelope.get('sha256'),'Envelope identity differs')
        subset=envelope.get('packets',[])
        v.need(all(p.get('id') in expected and expected[p['id']]==v.digest(p) for p in subset),
               'Stale or unknown envelope packet')
        group.verify_fixture(envelope,subset,models)
        for packet in subset:
            identity=packet['id'];v.need(identity not in membership,'Ambiguous overlapping envelopes')
            membership[identity]=digest
    v.need(set(membership)==set(expected),'Envelope coverage incomplete')
    entries={}
    for packet in packets:
        identity=packet['id'];envelope=envelopes[membership[identity]]
        view=projections[identity]
        v.need(view.get('id')==identity,'Cross-item projection')
        group.verify_projection(view,envelope,envelope['packets'],models)
        entries[identity]={'packet_sha256':expected[identity],
            'receipt_sha256':v.digest(view),'envelope_sha256':envelope['sha256'],
            'text':view['item']['text'],'origin':'test-fixture-grouped-projection',
            'provenance_version':view['version']}
    return {'version':v.VERSION,'entries':entries}

def compile_for_production(*args, **kwargs):
    raise v.VoiceError('Grouped production provenance/eligibility contract is not approved; v1/v2 unchanged')

def current_canonical_requests():
    """Regenerate through real producer inventories, never caller-supplied scope."""
    import json, subprocess
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    script="""import {catalogueRequests,pythonCatalogueRequests,shellCatalogueRequests,canonical} from './scripts/collect_scarb_ai_requests.mjs';
import {SCARB_COPY} from './docs/scarb-voice.mjs';
process.stdout.write(canonical([...catalogueRequests(SCARB_COPY),...pythonCatalogueRequests(),...shellCatalogueRequests()]));"""
    raw=subprocess.run(['node','--input-type=module','-e',script],cwd=root,check=True,capture_output=True,text=True,encoding='utf-8').stdout
    packets=json.loads(raw);manifest={p['id']:v.digest(p) for p in packets}
    committed=json.loads((root/'docs/scarb-copy-manifest.json').read_text(encoding='utf-8'))
    v.need(len(manifest)==len(packets) and manifest==committed,'Current producer manifest drift')
    return {p['id']:p for p in packets}


def compile_mixed_fixture_file(path, models):
    """Offline test-file seam; no real receipt, acceptance or public installation."""
    import json
    from pathlib import Path
    from scripts import scarb_ai_fact_slots as solo
    current=current_canonical_requests();bundle=json.loads(Path(path).read_text(encoding='utf-8'))
    v.need(set(bundle)=={'origin','solo_v2','grouped'} and bundle['origin']=='test-fixture-mixed-catalogue',
           'Mixed fixture origin required')
    config={'author_model':models['author'],'reviewer_model':models['reviewer']};entries={}
    for identity,receipt in bundle['solo_v2'].items():
        v.need(identity in current,'Unknown solo current ID')
        text=solo.fixture_receipt_check(receipt,current[identity],config)
        entries[identity]={'packet_sha256':v.digest(current[identity]),'receipt_sha256':receipt['sha256'],
                           'text':text,'origin':'test-fixture-solo-v2'}
    for item in bundle['grouped']:
        v.need(set(item)=={'envelope','projections'},'Grouped fixture fields')
        envelope=item['envelope'];subset=envelope['packets']
        v.need(all(p['id'] in current and p==current[p['id']] for p in subset),'Grouped current packet mismatch')
        group.verify_fixture(envelope,subset,models)
        v.need(set(item['projections'])=={p['id'] for p in subset},'Incomplete group views')
        for packet in subset:
            identity=packet['id'];view=item['projections'][identity]
            v.need(identity not in entries and view.get('id')==identity,'Duplicate/cross-item view')
            group.verify_projection(view,envelope,subset,models)
            entries[identity]={'packet_sha256':v.digest(packet),'receipt_sha256':v.digest(view),
                               'text':view['item']['text'],'origin':'test-fixture-grouped-projection'}
    v.need(set(entries)==set(current),'Mixed fixture missing full canonical catalogue')
    return {'version':v.VERSION,'entries':entries}
