"""Dormant exact stage verifier for the neighbourhood directory page only."""
import re
from hashlib import sha256
from html import escape

from scripts import scarb_ai_fact_slots as solo, scarb_ai_voice as v
from scripts import scarb_grouped_projection_seam as seam

PAGE = 'docs/neighbourhoods/index.html'
CSS = 'docs/neighbourhood-page.css'
ITEM = 'static.directory-intro'
PACKET_SHA256 = '8b7aac42544e4233b26b94fc720337ebb2be32d3f57313b0cea027234b7e3b18'
RECEIPT_SHA256 = 'bed905d41d658c6d2c76aab27f56b33c3dfc4f7eae2760c0d66da0426a18be53'
OLD = b'<p>There is so much to explore! Choose one of the 30 neighbourhoods in this map selection to open its source-linked records and boundary view.</p>'
OUTPUT_SHA256 = 'da63b3bb8c264cf515743bd696eab7069600883da19370e73f46d682c52af369'
TRUSTED_STAGE_SHA256 = None


def _sha(raw):
    return sha256(raw).hexdigest()


def reviewed_directory_projection(baseline, observed, receipt, config):
    v.need(PAGE in baseline and CSS in baseline and
           _sha(baseline[PAGE]) == 'c828318c19ebe70035b0c1130b0b1cd095dfaec29bab07537c95ea0a0fb105d0' and
           _sha(baseline[CSS]) == '6ecc6985898d7685fd50b2e6794372d5a84b19c495f3df044369550bcd3a350c',
           'Directory live baseline drift')
    source = baseline[PAGE]
    v.need(source.count(OLD) == 1, 'Directory intro not unique')
    routes = re.findall(rb'<li><a href="(/[a-z0-9-]+/)">[^<]+</a></li>', source)
    v.need(len(routes) == len(set(routes)) == 30 and
           all('docs' + route.decode() + 'index.html' in baseline for route in routes),
           'Exact retained directory destinations incomplete')
    packet = seam.current_canonical_requests()[ITEM]
    v.need(v.digest(packet) == PACKET_SHA256 and receipt.get('sha256') == RECEIPT_SHA256,
           'Directory exact editorial evidence differs')
    text = solo.receipt_check(receipt, packet, config)
    v.need(text.count('{{COUNT}}') == 1, 'Exact directory count binding not present')
    entry = escape(text.replace('{{COUNT}}', str(len(routes))), quote=False)
    new = ('<p data-scarb-voice="directory-intro">' + entry + '</p>').encode()
    output = source.replace(OLD, new, 1)
    v.need(_sha(output) == OUTPUT_SHA256 and observed.get(PAGE) == output,
           'Directory staged output drift')
    v.need(set(observed) == set(baseline) and
           all(observed[p] == raw for p,raw in baseline.items() if p != PAGE),
           'Directory modified out-of-scope output')
    return {'unit':'neighbourhood-directory-page','output_sha256':_sha(output),
            'baseline':{p:_sha(raw) for p,raw in baseline.items()},
            'packet_sha256':PACKET_SHA256,'receipt_sha256':RECEIPT_SHA256}


def verify_dormant_directory_stage(baseline, observed, reviewed_manifest, receipt, config):
    v.need(TRUSTED_STAGE_SHA256 is not None and v.digest(reviewed_manifest) == TRUSTED_STAGE_SHA256,
           'No independently approved coherent directory stage')
    result = reviewed_directory_projection(baseline, observed, receipt, config)
    v.need(result == reviewed_manifest, 'Directory stage manifest differs')
    return {**result, 'production_enabled':False}
