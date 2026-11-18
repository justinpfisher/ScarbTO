"""Non-publishing homepage preview of one retained geography packet.
No CLI, file writes, network, funding, receipt creation, or manifest enrollment.
The returned test-fixture markup deliberately fails the normal voice gateway.
"""
from html import escape
from . import scarb_ai_voice as voice, scarb_ai_fact_slots as slots
from .scarb_static_materialize import materialize

PACKET_SHA256 = 'ddbd209615b07051923e4008834c2c64df170fa26e6ab9f3da4e8abc58db2992'
TARGET = 'static.home-intro'
NOTICE = 'OFFLINE TEST PREVIEW: source-bound draft, not model-reviewed or approved for publication.'

def homepage_preview(packet, slot_output, record):
    """Render exact retained proof into the existing intro slot, never accept it."""
    voice.need(voice.digest(packet) == PACKET_SHA256, 'Preview requires the exact retained Ionview packet')
    voice.need(sum(s['id'] == TARGET for s in record['slots']) == 1,
               'Preview requires exactly one homepage intro slot')
    voice.need('<body>' in record['source'] and '<head>' in record['source'],
               'Preview requires the complete homepage shell')
    writer = slots.assemble(packet, slot_output)
    text = voice.text_check(packet, writer)
    lookup = {s['id']: s['draft'] for s in record['slots']}
    lookup[TARGET] = text
    html = materialize(record, lookup.__getitem__)
    # Make the artifact inert and conspicuous even if opened outside the test.
    html = html.replace('<head>', '<head><meta name="robots" content="noindex,nofollow">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">', 1)
    html = html.replace('<body>', '<body data-scarb-preview="test-fixture"><aside role="note">'
        + escape(NOTICE) + '</aside>', 1)
    return {'origin': 'test-fixture', 'accepted': False, 'packet_sha256': voice.digest(packet),
            'target': TARGET, 'text': text, 'html': html}
