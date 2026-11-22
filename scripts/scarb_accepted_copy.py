"""Pure Python consumer matching the browser's accepted-output resolver.

This validates exact request membership, not the truth of a receipt claim.
Use only bytes staged after private receipt verification and bound by release
review. Fixed wording uses the same checked-in pins as the browser.
"""
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path


def _fixed_pins_from_module(filename, expected):
    path = Path(__file__).resolve().parents[1] / "docs" / filename
    module = path.read_text(encoding="utf-8")
    if hashlib.sha256(module.encode("utf-8")).hexdigest() != expected:
        raise ValueError("Fixed wording pin module differs from the approved source")
    return json.loads(module.removeprefix("export default ").removesuffix(";\n"))


def fixed_wording_pins():
    return _fixed_pins_from_module("scarb-fixed-wording-pins.mjs",
                                   "5d47bcbe680ce4a09ae9ec73d81d6e3d1bb18744fcbbb24a267ca04c72393b93")


def fixed_directory_pins():
    return _fixed_pins_from_module("scarb-fixed-directory-pins.mjs",
                                   "3417086eac16a6f6814489aae06d031e49186858288600ae50210d1baddb4aca")


def fixed_community_layout_pins():
    return _fixed_pins_from_module("scarb-fixed-community-layout-pins.mjs",
                                   "03c1e368325e21a84d163874cbbef9439c1f8c2a49490fe25cf3cf29b918a179")


def accepted_resolver(catalogue, expected):
    version = catalogue.get("version") if isinstance(catalogue, dict) else None
    layout_version = version == "scarb-ai-voice-mixed-4"
    directory_version = layout_version or version == "scarb-ai-voice-mixed-3"
    fixed_version = directory_version or version == "scarb-ai-voice-mixed-2"
    mixed = fixed_version or version == "scarb-ai-voice-mixed-1"
    if ((not mixed and version != "scarb-ai-voice-1")
            or not isinstance(catalogue.get("entries"), dict) or not isinstance(expected, dict)
            or set(catalogue["entries"]) != set(expected) or (mixed and len(expected) != 736)):
        raise ValueError("AI copy catalogue does not match the qualified request manifest")
    fixed_pins = fixed_wording_pins() if fixed_version else {}
    if directory_version:
        fixed_pins.update(fixed_directory_pins())
    if layout_version:
        fixed_pins.update(fixed_community_layout_pins())
    if not fixed_pins.keys() <= expected.keys():
        raise ValueError("AI copy catalogue does not match the qualified request manifest")
    entries = {}
    for key, request_hash in expected.items():
        entry = catalogue["entries"][key]
        origin = entry.get("origin") if isinstance(entry, dict) else None
        grouped = origin == "scarb-grouped-projection-2"
        provenance = entry.get("provenance") if isinstance(entry, dict) else None
        group_ok = mixed and grouped and provenance == {
            "version": "scarb-grouped-run-envelope-2", "manifest_sha256": entry.get("receipt_sha256"), "packet_id": key}
        if mixed and isinstance(entry, dict) and entry.get("origin") == "scarb-grouped-projection-3":
            group_ok = provenance == {"version": "scarb-grouped-run-envelope-3",
                "prompt_version": "numeric-citation-2", "manifest_sha256": entry.get("receipt_sha256"), "packet_id": key}
        fixed = fixed_pins.get(key)
        fixed_ok = fixed is not None and origin == "scarb-fixed-wording-review-1" and provenance is None and (
            fixed["packet_sha256"] == request_hash and fixed["receipt_sha256"] == entry.get("receipt_sha256")
            and fixed["text"] == entry.get("text"))
        editorial_ok = group_ok or (origin in ("openai-api-reviewed", "protected-verbatim") and (not mixed or provenance is None))
        if (not isinstance(request_hash, str) or re.fullmatch(r"[a-f0-9]{64}", request_hash) is None
                or not isinstance(entry, dict) or entry.get("packet_sha256") != request_hash
                or not isinstance(entry.get("receipt_sha256"), str)
                or re.fullmatch(r"[a-f0-9]{64}", entry["receipt_sha256"]) is None
                or not isinstance(entry.get("text"), str) or not entry["text"]
                or not (fixed_ok if fixed is not None else editorial_ok)):
            raise ValueError("Unaccepted or stale AI copy: " + key)
        entries[key] = deepcopy(entry)

    def resolve(key):
        if key not in entries:
            raise ValueError("Public copy has not passed the AI gateway: " + key)
        return entries[key]["text"]
    return resolve


# Explicitly dormant until private receipt-bound inputs are installed. Source
# refresh has no dependency on this resolver or on a model being online.
_CURRENT = None
_LOADED = False

def current_copy(key, source_draft):
    global _CURRENT, _LOADED
    if not _LOADED:
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        catalogue = json.loads((root / "docs/scarb-copy-inputs.json").read_text(encoding="utf-8"))
        if catalogue is not None:
            expected = json.loads((root / "docs/scarb-copy-manifest.json").read_text(encoding="utf-8"))
            _CURRENT = accepted_resolver(catalogue, expected)
        _LOADED = True
    return source_draft if _CURRENT is None else _CURRENT(key)


def event_copy(event, *, bindings=None, read=None):
    """Optional reviewed explanation: exact current facts or no explanation.
    Structured factual output is independent and continues when this is absent.
    """
    import json
    from pathlib import Path
    if bindings is None:
        bindings=json.loads((Path(__file__).resolve().parents[1]/'docs/scarb-event-inputs.json').read_text(encoding='utf-8-sig'))
    binding=bindings.get(event['id'])
    if not binding:return None
    fields=('id','feed','establishment_id','name','kind','status','previous_status','inspection_date','detected_at','source_url')
    facts={k:event[k] for k in fields if k in event}
    if isinstance(facts.get('detected_at'),__import__('datetime').datetime):facts['detected_at']=facts['detected_at'].isoformat()
    if json.dumps(facts,sort_keys=True,ensure_ascii=False,separators=(',',':'))!=binding['facts']:return None
    if read is not None:return read(binding['key'])
    current_copy(binding['key'],'') if not _LOADED else None
    return _CURRENT(binding['key']) if _CURRENT is not None else None


def event_explanation_or_notice(event):
    result=event_copy(event)
    if result is not None:return result
    # A null catalogue is only the explicit offline draft state. With accepted
    # inputs, missing/currently stale event prose gets a faithful accepted notice.
    from pathlib import Path
    import json
    if json.loads((Path(__file__).resolve().parents[1]/'docs/scarb-copy-inputs.json').read_text(encoding='utf-8')) is None:return None
    from scripts.scarb_voice import copy
    return copy('event-prose-unavailable')
