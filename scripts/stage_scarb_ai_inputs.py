"""Offline bridge from private accepted receipts to exact generator inputs.

This does not generate copy, install a catalogue, activate AI, or publish files.
Only a new directory inside the existing private state may be written. The
normal source/release review must bind these exact bytes to the committed input;
public digest/origin fields alone never attest private receipt acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.scarb_ai_voice import VERSION, VoiceError, compile_catalogue, digest, encoded, need, verify_catalogue


def generator_inputs(packets, config, state, candidate, *, shells=None, event_source=None,
                     authoring_version="v1", mixed_bundle=None, registry_path=None, registry_sha256=None):
    """External coordinator pin scopes trust to this one private invocation."""
    from contextlib import nullcontext
    need((registry_path is None) == (registry_sha256 is None), "Registry path and external digest required together")
    need(registry_path is None or authoring_version == "v3", "Registry belongs only to mixed authoring")
    context = private_grouped_registry(state, registry_path, registry_sha256) if registry_path is not None else nullcontext()
    with context:
        return _generator_inputs(packets,config,state,candidate,shells=shells,event_source=event_source,
                                 authoring_version=authoring_version,mixed_bundle=mixed_bundle)


from contextlib import contextmanager

@contextmanager
def private_grouped_registry(state, path, expected_sha256):
    """Read an externally pinned single-run grant; never discover or self-enrol."""
    import re
    from types import MappingProxyType
    from scripts import scarb_grouped_provenance_candidate as provenance
    state,path=Path(state).resolve(),Path(path)
    need(isinstance(expected_sha256,str) and re.fullmatch(r"[a-f0-9]{64}",expected_sha256), "External registry digest required")
    need(state.is_dir() and path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(state)
         and not any((p/".git").exists() for p in (state,*state.parents)), "Use protected private registry inside state")
    raw=path.read_bytes();need(hashlib.sha256(raw).hexdigest()==expected_sha256,"Private registry bytes changed")
    value=json.loads(raw)
    need(isinstance(value,dict) and set(value)=={"version","runs"} and value['version']=='scarb-private-grouped-registry-1'
         and isinstance(value['runs'],dict) and len(value['runs'])==1,"Exact single-run registry required")
    fields={'cost_version','expected_purpose','funding_sha256','ledger_before_sha256','manifest_sha256','membership_before_sha256','membership_version','month_cap_nusd','packet_bindings','prices_sha256','requested_models','reservation_nusd','returned_models','runner_sha256','solo_state_root','solo_state_sha256','source_context_sha256'}
    for identity,pin in value['runs'].items():
        need(isinstance(identity,str) and re.fullmatch(r"[a-f0-9]{64}",identity) and isinstance(pin,dict)
             and set(pin)==fields and pin.get('manifest_sha256')==identity and pin.get('expected_purpose')=='production-grouped-review'
             and pin.get('cost_version')==2 and pin.get('membership_version')==1
             and Path(pin.get('solo_state_root','')).resolve()==state,"Wrong registry identity or provenance scope")
    need(not provenance.TRUSTED_GROUPED_RUNS,"Nested or ambient registry grant refused")
    previous=provenance.TRUSTED_GROUPED_RUNS
    try:
        provenance.TRUSTED_GROUPED_RUNS=MappingProxyType(value['runs'])
        yield
    finally:provenance.TRUSTED_GROUPED_RUNS=previous


def _generator_inputs(packets: list, config: dict, state: Path, candidate: Path, *, shells=None, event_source=None, authoring_version="v1", mixed_bundle=None) -> dict[str, bytes]:
    """Revalidate private receipts, then derive BOTH consumers from that result.

    The request manifest comes from caller-supplied current qualified packets,
    not from the candidate's self-reported packet hashes. The second compile
    is compared with the candidate again to detect a changed file/receipt set.
    No raw receipts, usage, credentials, funding data or source packets escape.
    """
    need(authoring_version in {"v1", "v2", "v3"}, "Unknown private authoring contract")
    need((mixed_bundle is not None) == (authoring_version == "v3"), "Mixed receipt bundle belongs only to v3")
    compile_private, verify_private = compile_catalogue, verify_catalogue
    if authoring_version == "v2":
        from scripts import scarb_ai_fact_slots
        compile_private, verify_private = scarb_ai_fact_slots.compile_catalogue, scarb_ai_fact_slots.verify_catalogue
    if authoring_version == "v3":
        from scripts import scarb_grouped_context_candidate as mixed
        current = mixed.seam.current_canonical_requests()
        need(len(packets) == 736 and len({p["id"] for p in packets}) == 736 and
             {p["id"]: p for p in packets} == current, "Exact complete current mixed requests required")
        mixed.verify_mixed_catalogue(mixed_bundle, config, candidate)
        accepted = mixed.compile_mixed_catalogue(mixed_bundle, config)
    else:
        verify_private(packets, config, state, candidate)
        accepted = compile_private(packets, config, state)
    need(encoded(json.loads(candidate.read_text(encoding="utf-8"))) == encoded(accepted),
         "Candidate changed during generator-input preparation")
    expected = {packet["id"]: digest(packet) for packet in packets}
    public = accepted
    raw = encoded(public) + b"\n"
    # Browser module and Python JSON carry the identical data, with no API path.
    # Do not embed an expected manifest in the public catalogue: each consumer
    # must construct it from its CURRENT qualified inputs, not from this output.
    # The private receipt records the authoring-time manifest for comparison.
    module = b"// Receipt-verified build input; no inference or credentials.\nexport default " + encoded(public) + b";\n"
    event_bindings = {}
    for packet in packets:
        if packet['id'].startswith('event.'):
            need(len(packet['evidence']) == 1, 'Event explanation requires one exact factual packet')
            facts = json.loads(packet['evidence'][0]['fact'])
            need(isinstance(facts, dict) and isinstance(facts.get('id'), str), 'Invalid event facts')
            need(facts['id'] not in event_bindings, 'Duplicate event explanation')
            event_bindings[facts['id']] = {'key': packet['id'], 'facts': packet['evidence'][0]['fact']}
    if event_bindings:
        need(isinstance(event_source,dict) and set(event_source)=={'release_id','sha256'}, 'Supply retained qualified event source')
        import re
        need(all(isinstance(event_source[k],str) and re.fullmatch(r'[a-f0-9]{64}',event_source[k]) for k in event_source), 'Invalid event evidence reference')
        release_raw=(ROOT/'docs/community-data/releases'/(event_source['release_id']+'.json')).read_bytes().replace(b'\r\n',b'\n')
        need(hashlib.sha256(release_raw).hexdigest()==event_source['sha256'], 'Retained event evidence bytes changed')
        release=json.loads(release_raw);need(release['id']==event_source['release_id'], 'Retained event release identity changed')
        fields=('id','feed','establishment_id','name','kind','status','previous_status','inspection_date','detected_at','source_url')
        facts={event['id']:{k:event[k] for k in fields if k in event} for event in release['events']}
        for identity,binding in event_bindings.items():
            need(identity in facts and encoded(facts[identity]).decode()==binding['facts'], 'Event prose lacks exact retained factual evidence')
    else:need(event_source is None, 'Unexpected event evidence without event prose')
    rendered = {'event-source.json': encoded(event_source) + b'\n',
                'current-request-manifest.json': encoded(expected) + b'\n',
                'current-request-manifest.mjs': b'export default ' + encoded(expected) + b';\n',
                'event-inputs.json': encoded(event_bindings) + b"\n",
                'event-inputs.mjs': b'export default ' + encoded(event_bindings) + b';\n'}
    if shells is not None:
        from scripts.scarb_accepted_copy import accepted_resolver
        from scripts.scarb_static_materialize import materialize
        lookup = accepted_resolver(public, expected)
        for path, record in shells.items():
            target = Path(path)
            need(target.parts[0] == 'docs' and '..' not in target.parts and
                 'briefs' not in target.parts and target.suffix == '.html',
                 'Static staging may not change archived or arbitrary paths')
            rendered[path] = materialize(record, lookup).encode('utf-8')
    attestation = {
        "version": "scarb-generator-inputs-1",
        "requests_sha256": digest(packets),
        "authoring_request_manifest": expected,
        "catalogue_sha256": digest(accepted),
        "authoring_version": authoring_version,
        "accepted_receipts": {key: value["receipt_sha256"] for key, value in accepted["entries"].items()},
        "files": {"accepted-copy.json": hashlib.sha256(raw).hexdigest(),
                  "accepted-copy.mjs": hashlib.sha256(module).hexdigest(),
                  **{name: hashlib.sha256(data).hexdigest() for name, data in rendered.items()}},
        "meaning": "Compared against private accepted receipts; not API qualification or publication",
    }
    return {"accepted-copy.json": raw, "accepted-copy.mjs": module,
            "private-input-attestation.json": encoded(attestation) + b"\n", **rendered}


def stage_inputs(packets: list, config: dict, state: Path, candidate: Path, output: Path, *, shells=None, event_source=None, authoring_version="v1", mixed_bundle=None, registry_path=None, registry_sha256=None) -> dict:
    state, output = state.resolve(), output.resolve()
    need("docs" not in state.parts and not any((p / ".git").exists() for p in (state, *state.parents)),
         "Use existing private state outside public output and repositories")
    need(output != state and output.is_relative_to(state) and not output.exists(),
         "Choose a new generator-input directory inside private state")
    files = generator_inputs(packets, config, state, candidate, shells=shells, event_source=event_source, authoring_version=authoring_version, mixed_bundle=mixed_bundle, registry_path=registry_path, registry_sha256=registry_sha256)
    output.mkdir(parents=False, exist_ok=False)
    for name, content in files.items():
        (output / name).parent.mkdir(parents=True, exist_ok=True)
        with (output / name).open("xb") as handle:
            handle.write(content)
    return json.loads(files["private-input-attestation.json"])


def compare_publication(packets, config, state, candidate, publication, *, shells=None, event_source=None, authoring_version="v1", mixed_bundle=None, registry_path=None, registry_sha256=None):
    """Read-only exact-byte comparison, freshly rechecking private receipts.
    Does not install outputs, regenerate accepted prose or approve publication.
    """
    files=generator_inputs(packets,config,state,candidate,shells=shells, event_source=event_source, authoring_version=authoring_version, mixed_bundle=mixed_bundle, registry_path=registry_path, registry_sha256=registry_sha256)
    mapping={'accepted-copy.json':'docs/scarb-copy-inputs.json',
             'accepted-copy.mjs':'docs/scarb-copy-inputs.mjs',
             'event-inputs.json':'docs/scarb-event-inputs.json',
             'event-inputs.mjs':'docs/scarb-event-inputs.mjs',
             'current-request-manifest.json':'docs/scarb-copy-manifest.json',
             'current-request-manifest.mjs':'docs/scarb-copy-manifest.mjs',
             'event-source.json':'docs/scarb-event-source.json'}
    for name, data in files.items():
        if name=='private-input-attestation.json':continue
        target=publication/mapping.get(name,name)
        need(target.is_file() and target.read_bytes()==data,
             'Publication bytes differ from private accepted inputs: '+mapping.get(name,name))
    return json.loads(files['private-input-attestation.json'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("requests", "config", "state", "catalogue", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--static-shells", action="store_true", help="Stage the six exact current shells privately; never the weekly archive")
    parser.add_argument("--event-source", type=Path, help="Non-secret retained-release id and byte-hash descriptor")
    parser.add_argument("--authoring-version", choices=("v1", "v2", "v3"), default="v1")
    parser.add_argument("--mixed-receipts", type=Path, help="Private admitted original receipt bundle for v3 only; not reader metadata")
    parser.add_argument("--private-registry",type=Path)
    parser.add_argument("--approved-registry-sha256",help="Coordinator-supplied expected digest, never taken from the candidate")
    args = parser.parse_args()
    stage_inputs(json.loads(args.requests.read_text(encoding="utf-8")),
                 json.loads(args.config.read_text(encoding="utf-8")),
                 args.state, args.catalogue, args.output,
                 shells=json.loads((ROOT / "config/scarb-static-shells.json").read_text(encoding="utf-8")) if args.static_shells else None,
                 event_source=json.loads(args.event_source.read_text(encoding="utf-8")) if args.event_source else None,
                 authoring_version=args.authoring_version,
                 mixed_bundle=json.loads(args.mixed_receipts.read_text(encoding="utf-8")) if args.mixed_receipts else None,
                 registry_path=args.private_registry,registry_sha256=args.approved_registry_sha256)
    print("Receipt-bound generator inputs staged privately; no model called or publication changed.")


if __name__ == "__main__":
    main()
