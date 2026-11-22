"""Offline production candidate; no bridge wiring, registry grant or writes."""
import json,hashlib
from pathlib import Path
from scripts import scarb_ai_voice as v,scarb_ai_fact_slots as solo
from scripts import scarb_grouped_fixture_envelope as contract
from scripts import scarb_grouped_projection_seam as seam
from scripts import scarb_grouped_provenance_candidate as provenance
ROOT=Path(__file__).resolve().parents[1]
ANCHORS={'shell.shell-b04b38d4-007':('/neighbourhoods/','Neighbourhoods'),'shell.shell-b04b38d4-008':('/briefs/','Weekly briefs')}

AREA_CONTROLS={
 '060':('area-reopen','Open selected area information',True),
 '061':('area-clear','Clear area',False),
 '078':('area-panel-expand','Expand area information',True),
 '079':('area-panel-expand','Expand',False),
 '080':('area-panel-close','Close area information',True),
 '081':('area-panel-close','Close',False),
 '082':('area-panel-fit','View boundary',False),
}
AREA_BUTTONS={
 'area-reopen':'<button type="button" id="area-reopen" aria-label="Open selected area information"><span id="area-selection-name"></span></button>',
 'area-clear':'<button type="button" id="area-clear">Clear area</button>',
 'area-panel-expand':'<button type="button" id="area-panel-expand" aria-expanded="false" aria-label="Expand area information">Expand</button>',
 'area-panel-close':'<button type="button" id="area-panel-close" aria-label="Close area information">Close</button>',
 'area-panel-fit':'<button type="button" id="area-panel-fit">View boundary</button>',
}
AREA_MEANINGS={
 'area-reopen':'Reopen information for the already selected area; do not select or clear another area.',
 'area-clear':'Clear the selected area and close its panel; not delete a saved area.',
 'area-panel-expand':'Toggle the selected area information panel expanded state; do not zoom map or change selection.',
 'area-panel-close':'Close information panel and return focus to reopen control; do not clear selected area.',
 'area-panel-fit':'Fit the map to selected area boundary; unavailable without map; no electoral-address determination.',
}
AREA_BEHAVIOR_SHA256='98e8ad4e1537dbf9a8d244e69e2f0e76b0929de76e383346ca75c18a32d474de'

def area_context(packet,raw,text):
 from scripts.scarb_static_materialize import discover
 suffix=packet['id'].removeprefix('shell.shell-b04b38d4-')
 v.need(packet['id']=='shell.shell-b04b38d4-'+suffix and suffix in AREA_CONTROLS,'Unsupported area control')
 dom,label,attribute=AREA_CONTROLS[suffix];anchor=AREA_BUTTONS[dom]
 v.need(text.count(anchor)==1 and text.count('id="'+dom+'"')==1 and packet['draft']==label and packet['kind']=='functional','Exact area control changed')
 behavior=(ROOT/'docs/area-explorer.mjs').read_bytes()
 v.need(hashlib.sha256(behavior).hexdigest()==AREA_BEHAVIOR_SHA256,'Area control behavior changed')
 shell=json.loads((ROOT/'config/scarb-static-shells.json').read_text(encoding='utf8'))['docs/index.html']
 v.need(discover(shell['source'])==[{k:v for k,v in s.items() if k not in ('id','fields')} for s in shell['slots']],'Area source slot inventory changed')
 slots=[s for s in shell['slots'] if s['id']==packet['id']]
 v.need(len(slots)==1 and slots[0]['draft']==label and slots[0]['attribute']==attribute and shell['source'].count(anchor)==1,'Area canonical slot changed')
 slot=slots[0];start=shell['source'].index(anchor)
 v.need(start<=slot['start']<slot['end']<=start+len(anchor),'Area slot belongs to different control')
 return {'path':'docs/index.html','source_sha256':hashlib.sha256(raw).hexdigest(),'anchor_html':anchor,
 'behavior_path':'docs/area-explorer.mjs','behavior_sha256':AREA_BEHAVIOR_SHA256,
 'meaning':AREA_MEANINGS[dom]+' Keep visible and accessible names aligned; no new findings or changes to source facts.'}


SAVED_PACKET_BINDINGS={'static.saved-added': '8446e89d6860fe98da2faab21a20cd230dcd7d12fa6b4fb111929a556891894a', 'static.saved-duplicate': 'c63dbc710171c7d62ea968309a0c3a0bb393753dc5807414ccaf30cbcab0ac08', 'static.saved-neighbourhoods': '40dc757e741d0ccd3dd166a89b6e37ca688d037efd84c30ee93896128ccdb13f', 'static.saved-remove': '7de975c6a2a08af9849c6ac50523d764b4b1adbbf9da9b6c878d9a18adca67ad', 'static.saved-remove-label': '245dff2c510b2a102ec83ee6b99e8ca6d137954fb96f5b8fb2760d3a8c0c6884', 'static.saved-removed': 'b84fbbd6172e7f77c46b6aa63b67149ad78a1a0606507f1ba90822897143286f', 'static.saved-unreadable': 'efff9b8990933e7e64c2719c245019b3564e5400e02e5e9c95c3bbb35223dcb9', 'static.saved-wards': 'bf7037cbc0577799712a452eed7574b37672f0a64d6286511159bdea0702ef5b', 'static.saved-write-failed': 'ab634f0a4d6da41f9ccfa56119ce843e6dd743f964b798b1037f2861a6c52d01'}
SAVED_SOURCE_PINS={'docs/saved-areas.mjs': '73825cb71f9e4260e1fbdce6ada30ddf88788c625baa20a539bc045cc00c368f', 'docs/area-selection.mjs': '7f6ac42ebe9c174d28f02d97244267b2baa9efd6f538bd98cecb4d57bcc18313'}
SAVED_MEANINGS={'saved-unreadable': 'Reading or parsing saved browser areas failed. Areas can still be chosen; do not claim stored data was deleted.', 'saved-write-failed': 'Persisting a change failed; the existing list remains unchanged. Do not claim the change succeeded.', 'saved-wards': 'Option-group label for City wards, distinct from neighbourhoods.', 'saved-neighbourhoods': 'Option-group label for neighbourhoods, distinct from City wards.', 'saved-remove': 'Visible removal button for one saved public area, not clearing map selection or deleting other records.', 'saved-remove-label': 'Accessible name of the same removal button; preserve NAME and agreement with visible Remove.', 'saved-removed': 'Only after successful persistence of removal; saved list rerenders and focus returns to chooser. Removal is from this browser only.', 'saved-duplicate': 'Selected kind/code is already saved. No duplicate entry or write is made.', 'saved-added': 'Only after successful persistence of a validated new public area; saved on this browser, not an account or cloud service.'}

def saved_context(packet):
 identity=packet['id'];key=identity.removeprefix('static.')
 v.need(identity in SAVED_PACKET_BINDINGS and v.digest(packet)==SAVED_PACKET_BINDINGS[identity],'Unsupported or changed saved-area packet')
 for path,expected in SAVED_SOURCE_PINS.items():
  v.need(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,'Saved-area behavior changed')
 raw=(ROOT/'docs/saved-areas.mjs').read_text(encoding='utf8')
 anchor="staticCopy('"+key+"'";v.need(raw.count(anchor)==1,'Saved-area consumer changed')
 named=key in ('saved-remove-label','saved-removed','saved-duplicate','saved-added')
 v.need(packet['locks']==({'VALUE_0':'{{NAME}}'} if named else {}),'Saved-area NAME contract changed')
 return {'path':'docs/saved-areas.mjs','source_sha256':SAVED_SOURCE_PINS,'consumer':anchor,'locks':packet['locks'],'source_evidence_sha256':packet['evidence'][0]['sha256'],'runtime_parameter':{'NAME':'Public area name supplied locally at rendering; never include a saved selection in the model request.'} if named else {},'meaning':SAVED_MEANINGS[key]+' Preserve the exact functional trigger and scope. No inference about private saved selections, personal location, safety or current source findings.'}


NEIGHBOURHOOD_BUILDER='scripts/build_neighbourhood_pages.mjs'
NEIGHBOURHOOD_PREVIOUS_BUILDER_SHA256='05110e4acd42337845bb1b6038961009c096e10a47662bf04edc37afe42ffa61'
# The builder binds the reviewed Git LF blob 0e58e48566861c64b739c3eed8fc8253d6adc5de.
# Retain the six unchanged context digests and check exact LF/CRLF counterparts.
NEIGHBOURHOOD_SOURCE_PINS={
 'docs/neighbourhood-page.template.html': '5e034b7aa5b2bfadc5fecd2e28bba4043d813db890e0d73202ff9a68d89326aa',
 NEIGHBOURHOOD_BUILDER: '068af6361615fecde5af4f41fd44b74b1a002960b0465e75801c0b488cdd6032',
 'docs/neighbourhood-page.mjs': 'f8416ac22c44f9c07b2857fa02c90eabe7a62d1dd1f93d82d163bc7c8f9efae0',
 'docs/neighbourhood-page-actions.mjs': 'e325cded7126fe5b2f26f62cceeb22e0955459a85c46f5238ed7f30a3601b8ad',
 'docs/area-selection.mjs': '7f6ac42ebe9c174d28f02d97244267b2baa9efd6f538bd98cecb4d57bcc18313',
 'docs/neighbourhood-routes.mjs': '94f3d4970ddb3c017fb8ad957df48881205ba604fc537b7d4f98ae8ebb58009a',
 'scripts/scarb_static_materialize.py': '52bfa6d57868051c3fc02101ecb5c315ea630f91a8955b2fa315ab5168f19beb',
}
NEIGHBOURHOOD_ALTERNATE_PINS={
 'docs/neighbourhood-page.template.html': '9ae0f29f0318eb843ab5f70832451e1fc0cdb8ac0bdc9e520f6712935d449daf',
 NEIGHBOURHOOD_BUILDER: '0a16b7e36d0ee3616e2391a257faf88f870f5bcc09e8ec40ccf1bd6c0a3b2e64',
 'docs/neighbourhood-page.mjs': 'dfc152be8c64ef8258ba0debbbaadd8c013c489a50e20be6ba54ec488aa41145',
 'docs/neighbourhood-page-actions.mjs': 'ba528fed7009509cd99e230f1805779288eccd6bd5cdb267ef4c9771f309b217',
 'docs/area-selection.mjs': 'b1616d798b2d9867e9e37cd880a5d2cbd3e12398312afa4b5ca86bdadebc9e33',
 'docs/neighbourhood-routes.mjs': '66e5e4aba3145ea66e79fae6fa562080ee01151799b554d073551cc34b4691ff',
 'scripts/scarb_static_materialize.py': '0c7d8296dfbf08585a2909f4b7b83dcd221f283c6df6130d92c237e378143958',
}

def verify_neighbourhood_sources():
 for path,expected in NEIGHBOURHOOD_SOURCE_PINS.items():
  actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  v.need(actual in (expected,NEIGHBOURHOOD_ALTERNATE_PINS[path]),'Neighbourhood behavior or source changed: '+path)
 return NEIGHBOURHOOD_SOURCE_PINS.copy()

NEIGHBOURHOOD_RECORD_SHA256='4d0c41a93e204ba9df807ea9776aa6ba0a68fdae877fcaff3c8f3eadf1b50cbf'
NEIGHBOURHOOD_CONTEXTS={'shell.shell-b1bb7e6e-000': {'packet_sha256': 'b883f3e1f42b8dd9991579b11ac6f0eeb21e339f553bf140685e72b380e55a55', 'slot': {'start': 320, 'end': 440, 'draft': 'Explore {{NAME}} through food inspection results and neighbourhood boundaries, with dates and sources to follow further.', 'attribute': True, 'id': 'shell.shell-b1bb7e6e-000'}, 'element': {'tag': 'meta', 'attributes': {'name': 'description', 'content': 'Explore {{NAME}} through food inspection results and neighbourhood boundaries, with dates and sources to follow further.'}, 'opening_tag': '<meta name="description" content="Explore {{NAME}} through food inspection results and neighbourhood boundaries, with dates and sources to follow further.">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-001': {'packet_sha256': 'c2290d84f9ced2b38ed0691cefc508d86831f8c2202497b5db14dea8e3bcbc01', 'slot': {'start': 637, 'end': 656, 'draft': '{{NAME}} | Scarb.TO', 'attribute': True, 'id': 'shell.shell-b1bb7e6e-001'}, 'element': {'tag': 'meta', 'attributes': {'property': 'og:title', 'content': '{{NAME}} | Scarb.TO'}, 'opening_tag': '<meta property="og:title" content="{{NAME}} | Scarb.TO">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-002': {'packet_sha256': '14a94e6188479f502f6249da2bdf1d57b61ab6db8b335cf77887e3499c922522', 'slot': {'start': 702, 'end': 822, 'draft': 'Explore {{NAME}} through food inspection results and neighbourhood boundaries, with dates and sources to follow further.', 'attribute': True, 'id': 'shell.shell-b1bb7e6e-002'}, 'element': {'tag': 'meta', 'attributes': {'property': 'og:description', 'content': 'Explore {{NAME}} through food inspection results and neighbourhood boundaries, with dates and sources to follow further.'}, 'opening_tag': '<meta property="og:description" content="Explore {{NAME}} through food inspection results and neighbourhood boundaries, with dates and sources to follow further.">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-003': {'packet_sha256': 'da9a30fa18f6bf2296a1fbd9413dde78380d9431b8a436cfbdf10ce1b7da2afa', 'slot': {'start': 1004, 'end': 1023, 'draft': '{{NAME}} · Scarb.TO', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-003'}, 'element': {'tag': 'title', 'attributes': {}, 'opening_tag': '<title>'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-004': {'packet_sha256': '7b4a435b074ed622c4a23f1504dc9601b9a3eeb55fed5b5d4c4ed637c3430255', 'slot': {'start': 1156, 'end': 1187, 'draft': 'Skip to food inspection results', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-004'}, 'element': {'tag': 'a', 'attributes': {'class': 'skip-link', 'href': '#inspections'}, 'opening_tag': '<a class="skip-link" href="#inspections">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-005': {'packet_sha256': '8302af5215600755c8b36b716a186766d7742d3ab777c4bfa735050349c149fb', 'slot': {'start': 1265, 'end': 1278, 'draft': 'Scarb.TO home', 'attribute': True, 'id': 'shell.shell-b1bb7e6e-005'}, 'element': {'tag': 'a', 'attributes': {'class': 'brand', 'href': '/', 'aria-label': 'Scarb.TO home'}, 'opening_tag': '<a class="brand" href="/" aria-label="Scarb.TO home">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-006': {'packet_sha256': '9750a54e5bd9e2bff589deeac6602e021a67892087c6ef87d111bd454421a11d', 'slot': {'start': 1490, 'end': 1498, 'draft': 'Scarb.TO', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-006'}, 'element': {'tag': 'span', 'attributes': {'class': 'brand-name'}, 'opening_tag': '<span class="brand-name">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-007': {'packet_sha256': 'f3b3c83893bbfabb50bec932d74bd7de2467db8a3770caefa7dd2599660c4016', 'slot': {'start': 1542, 'end': 1572, 'draft': 'Scarborough. I looked into it.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-007'}, 'element': {'tag': 'span', 'attributes': {'class': 'brand-tagline'}, 'opening_tag': '<span class="brand-tagline">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-008': {'packet_sha256': 'ad06f3a3a4bc9925b4f8d8be496b37e07ca076dfa6403783de4b274963371ea9', 'slot': {'start': 1661, 'end': 1703, 'draft': ' Scarb.TO | Scarborough. I looked into it.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-008'}, 'element': {'tag': 'span', 'attributes': {'class': 'print-brand'}, 'opening_tag': '<span class="print-brand">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-009': {'packet_sha256': '4667fdec3862cdac630f59842818106b24cfbde9e398457c68b8a5cbfbddc0e0', 'slot': {'start': 1747, 'end': 1766, 'draft': 'Explore Scarborough', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-009'}, 'element': {'tag': 'a', 'attributes': {'class': 'header-link', 'href': '/'}, 'opening_tag': '<a class="header-link" href="/">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-010': {'packet_sha256': '0ddcba4e018d98e812e4d24e4c00f32699d36d037720af2b509845afb46a1e93', 'slot': {'start': 1953, 'end': 1978, 'draft': 'Scarborough neighbourhood', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-010'}, 'element': {'tag': 'p', 'attributes': {'class': 'eyebrow'}, 'opening_tag': '<p class="eyebrow">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-011': {'packet_sha256': '01a8b162c20e1136146b92bb27142f1ee015951d856db20b437b26f5211ebb61', 'slot': {'start': 2009, 'end': 2017, 'draft': '{{NAME}}', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-011'}, 'element': {'tag': 'h1', 'attributes': {'id': 'page-title'}, 'opening_tag': '<h1 id="page-title">'}, 'semantic_class': 'identity-or-metadata'}, 'static.neighbourhood-intro': {'packet_sha256': '8ae2f231f1f76abe2f508f13b88d020821de460e4fda080ec022f9301ea36da5', 'slot': {'start': 2071, 'end': 2330, 'draft': "Now this is a patch of Scarborough worth getting to know. I've put the food inspection records and City neighbourhood boundaries for {{NAME}} side by side. Start with a familiar place, then follow the source links. There's often another detail worth checking.", 'attribute': False, 'id': 'static.neighbourhood-intro', 'fields': {'NAME': '{{NAME}}'}}, 'element': {'tag': 'p', 'attributes': {'data-scarb-voice': 'neighbourhood-intro'}, 'opening_tag': '<p data-scarb-voice="neighbourhood-intro">'}, 'semantic_class': 'editorial'}, 'shell.shell-b1bb7e6e-013': {'packet_sha256': 'fba08f77c1cf163dbf3659a4d1273af83d1dd4554f5857fce0fca797fc81aa2c', 'slot': {'start': 2392, 'end': 2404, 'draft': 'Page actions', 'attribute': True, 'id': 'shell.shell-b1bb7e6e-013'}, 'element': {'tag': 'div', 'attributes': {'class': 'page-actions', 'role': 'group', 'aria-label': 'Page actions'}, 'opening_tag': '<div class="page-actions" role="group" aria-label="Page actions">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-014': {'packet_sha256': '58724a91511bcd9897fafb7993c68236d7478d4c91d9ea1d92f1cdc64665f8cb', 'slot': {'start': 2478, 'end': 2502, 'draft': 'Share this neighbourhood', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-014'}, 'element': {'tag': 'button', 'attributes': {'class': 'secondary-button', 'id': 'share-page', 'type': 'button'}, 'opening_tag': '<button class="secondary-button" id="share-page" type="button">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-015': {'packet_sha256': '2915a62a79ca636a6f625e73e854e16f487d9c7f70909f165a2c8e3f9a15f24b', 'slot': {'start': 2583, 'end': 2598, 'draft': 'Print this page', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-015'}, 'element': {'tag': 'button', 'attributes': {'class': 'secondary-button', 'id': 'print-page', 'type': 'button'}, 'opening_tag': '<button class="secondary-button" id="print-page" type="button">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-016': {'packet_sha256': 'f855ff53ce100cbf1ae86a8649891ccc492002a022b8b7de19b6a91e392f3fcc', 'slot': {'start': 2749, 'end': 2897, 'draft': 'Print includes every record loaded for this neighbourhood, with its inspection findings, dates and source links, not just the first page of results.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-016'}, 'element': {'tag': 'p', 'attributes': {'class': 'section-note'}, 'opening_tag': '<p class="section-note">'}, 'semantic_class': 'editorial'}, 'shell.shell-b1bb7e6e-017': {'packet_sha256': 'b9837cc1747a42e4bbc1216d2080116712266aa51bed62d0337a9e3765ce552d', 'slot': {'start': 2947, 'end': 2992, 'draft': 'Make a neighbourhood update to print or share', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-017'}, 'element': {'tag': 'a', 'attributes': {'href': '/community/?area={{CODE}}'}, 'opening_tag': '<a href="/community/?area={{CODE}}">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-018': {'packet_sha256': 'b806f41330dedadf7923a47e31f2ada484100be229eb45f9b6f7d751cc72c31c', 'slot': {'start': 2996, 'end': 3079, 'draft': '. Choose your coverage and edition period, then preview the source-linked material.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-018'}, 'element': {'tag': 'p', 'attributes': {}, 'opening_tag': '<p>'}, 'semantic_class': 'editorial'}, 'shell.shell-b1bb7e6e-019': {'packet_sha256': '9b69ecd85107b0a1379fc5dc561e876f14f3e155ba3b29c98c2b8d9808dfc78a', 'slot': {'start': 3217, 'end': 3234, 'draft': 'Explore this area', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-019'}, 'element': {'tag': 'h2', 'attributes': {'id': 'explore-title'}, 'opening_tag': '<h2 id="explore-title">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-020': {'packet_sha256': 'be37a86b4718e6abd3c854d6668907ec5ac141f9c5c5501faf8a06c7e32e44f4', 'slot': {'start': 3251, 'end': 3351, 'draft': 'Curious where these places sit? Explore the map, or browse the same places in the list alongside it.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-020'}, 'element': {'tag': 'p', 'attributes': {}, 'opening_tag': '<p>'}, 'semantic_class': 'editorial'}, 'shell.shell-b1bb7e6e-021': {'packet_sha256': 'd85c4b3f75a60d2032fd575cf45a75f0fff17a77507e1f68b965dcfacc3da1ca', 'slot': {'start': 3493, 'end': 3526, 'draft': 'Open {{NAME}} in the map and list', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-021'}, 'element': {'tag': 'a', 'attributes': {'class': 'primary-link', 'id': 'map-link', 'href': '/?areaKind=neighbourhood&areaCode={{CODE}}&mode=all&days=all'}, 'opening_tag': '<a class="primary-link" id="map-link" href="/?areaKind=neighbourhood&amp;areaCode={{CODE}}&amp;mode=all&amp;days=all">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-022': {'packet_sha256': '95829595fd19d5c2739a0676459585a075ff16bc4f03a9b40c06844fe11f52e2', 'slot': {'start': 3665, 'end': 3680, 'draft': 'Your City wards', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-022'}, 'element': {'tag': 'h2', 'attributes': {'id': 'ward-title'}, 'opening_tag': '<h2 id="ward-title">'}, 'semantic_class': 'editorial'}, 'shell.shell-b1bb7e6e-023': {'packet_sha256': '0026546d53f70305ab4e6cb174231c5c38f0815c2d644f6746809987c42f67cd', 'slot': {'start': 3718, 'end': 3931, 'draft': "Here's another layer to explore: neighbourhood boundaries and ward boundaries don't always line up! These wards overlap this neighbourhood. Check your address with the City to find which councillor represents you.", 'attribute': False, 'id': 'shell.shell-b1bb7e6e-023'}, 'element': {'tag': 'p', 'attributes': {'class': 'section-note'}, 'opening_tag': '<p class="section-note">'}, 'semantic_class': 'editorial'}, 'shell.shell-b1bb7e6e-024': {'packet_sha256': '7cc245c1d9b12549c9b17b5e697600da464e87ac206b09122b17a31f49802aba', 'slot': {'start': 4020, 'end': 4173, 'draft': 'Provincial and federal boundaries add two more layers. Use the official tools below to find your representatives. You enter your address there, not here.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-024'}, 'element': {'tag': 'p', 'attributes': {'class': 'section-note'}, 'opening_tag': '<p class="section-note">'}, 'semantic_class': 'editorial'}, 'shell.shell-b1bb7e6e-025': {'packet_sha256': '1ce1c432566113f98c9027f9d1cfcd2be948eaa99d3f5e1101ffc057f357d146', 'slot': {'start': 4314, 'end': 4333, 'draft': 'Find an Ontario MPP', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-025'}, 'element': {'tag': 'a', 'attributes': {'href': 'https://www.ola.org/en/members/current', 'target': '_blank', 'rel': 'noopener noreferrer'}, 'opening_tag': '<a href="https://www.ola.org/en/members/current" target="_blank" rel="noopener noreferrer">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-026': {'packet_sha256': '62d0622e1e9eb9443b6c0f790a71cc3c69bf6065743f6367cecf56ad51ed64db', 'slot': {'start': 4453, 'end': 4470, 'draft': 'Find a federal MP', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-026'}, 'element': {'tag': 'a', 'attributes': {'href': 'https://www.ourcommons.ca/Members/en/search', 'target': '_blank', 'rel': 'noopener noreferrer'}, 'opening_tag': '<a href="https://www.ourcommons.ca/Members/en/search" target="_blank" rel="noopener noreferrer">'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-027': {'packet_sha256': '8b5c8a985fffc23673ca2abde099c4092766d882ce97b0fbdd662fa575b35b74', 'slot': {'start': 4642, 'end': 4665, 'draft': 'Food inspection results', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-027'}, 'element': {'tag': 'h2', 'attributes': {'id': 'inspection-title'}, 'opening_tag': '<h2 id="inspection-title">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-028': {'packet_sha256': '5b2739e348fefff0e43fe7136fee964876d5b2d6050ffe48556bb44fbf37ebd3', 'slot': {'start': 4703, 'end': 5082, 'draft': "I match each DineSafe record's source coordinates to the City's neighbourhood boundaries, just like the map. This is a Scarb.TO calculation, not a neighbourhood label supplied by DineSafe or an independent check of the address. Source coordinates can be imperfect. Results describe the inspection on the date shown, not current safety. Check the City's record for anything newer.", 'attribute': False, 'id': 'shell.shell-b1bb7e6e-028'}, 'element': {'tag': 'p', 'attributes': {'class': 'section-note'}, 'opening_tag': '<p class="section-note">'}, 'semantic_class': 'source-status-limitation'}, 'shell.shell-b1bb7e6e-029': {'packet_sha256': '3b60a6d0189d72723e46eb933436bb5808f336350a81ffbe11b28de2d2348b24', 'slot': {'start': 5119, 'end': 5279, 'draft': 'These counts are source records, not a confirmed count of distinct businesses. Different source IDs can share a name and address; I keep those records separate.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-029'}, 'element': {'tag': 'p', 'attributes': {'class': 'section-note'}, 'opening_tag': '<p class="section-note">'}, 'semantic_class': 'source-status-limitation'}, 'shell.shell-b1bb7e6e-030': {'packet_sha256': '66863c4bb7a07c872a4780548f23515a31e993eff54aacdbd34e9987f98ec21e', 'slot': {'start': 5365, 'end': 5401, 'draft': 'Getting the food inspection results.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-030'}, 'element': {'tag': 'p', 'attributes': {'id': 'feed-status', 'class': 'feed-status', 'role': 'status', 'aria-live': 'polite'}, 'opening_tag': '<p id="feed-status" class="feed-status" role="status" aria-live="polite">'}, 'semantic_class': 'source-status-limitation'}, 'shell.shell-b1bb7e6e-031': {'packet_sha256': '62fea8f25c75f203cf31dbd0e184619c2ac823b468b057a175f6cac12a8369db', 'slot': {'start': 5493, 'end': 5512, 'draft': 'About these records', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-031'}, 'element': {'tag': 'summary', 'attributes': {}, 'opening_tag': '<summary>'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-032': {'packet_sha256': '7e0e657193f366f78a06a23f6a7ab065cd109a8501b98976ede13a46f0aa7a25', 'slot': {'start': 5699, 'end': 5716, 'draft': 'Show more records', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-032'}, 'element': {'tag': 'button', 'attributes': {'id': 'show-more', 'class': 'secondary-button', 'type': 'button', 'hidden': None}, 'opening_tag': '<button id="show-more" class="secondary-button" type="button" hidden>'}, 'semantic_class': 'action-or-accessible-label'}, 'shell.shell-b1bb7e6e-033': {'packet_sha256': '0aff3909c7addb29c33170c297aee6dca0c8fb786c60df93858dd56f15965ce9', 'slot': {'start': 5851, 'end': 5881, 'draft': "About the City's DineSafe data", 'attribute': False, 'id': 'shell.shell-b1bb7e6e-033'}, 'element': {'tag': 'a', 'attributes': {'href': 'https://open.toronto.ca/dataset/dinesafe/', 'target': '_blank', 'rel': 'noopener noreferrer'}, 'opening_tag': '<a href="https://open.toronto.ca/dataset/dinesafe/" target="_blank" rel="noopener noreferrer">'}, 'semantic_class': 'source-licence-attribution'}, 'shell.shell-b1bb7e6e-034': {'packet_sha256': '4707f17beeafd845f494824323bad5e8b78f7ff5167ce86716b190a7785047d6', 'slot': {'start': 5983, 'end': 6016, 'draft': 'Open Government Licence – Toronto', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-034'}, 'element': {'tag': 'a', 'attributes': {'href': 'https://open.toronto.ca/open-data-licence/', 'target': '_blank', 'rel': 'noopener noreferrer'}, 'opening_tag': '<a href="https://open.toronto.ca/open-data-licence/" target="_blank" rel="noopener noreferrer">'}, 'semantic_class': 'source-licence-attribution'}, 'shell.shell-b1bb7e6e-035': {'packet_sha256': '7abdccfca08f14b91138d379b7d29776b490a6cca7cddce1bb10592b355c2ff3', 'slot': {'start': 6167, 'end': 6199, 'draft': 'More to explore, with a few gaps', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-035'}, 'element': {'tag': 'h2', 'attributes': {'id': 'other-data-title'}, 'opening_tag': '<h2 id="other-data-title">'}, 'semantic_class': 'identity-or-metadata'}, 'shell.shell-b1bb7e6e-036': {'packet_sha256': 'df1e83c416d2e6ff673466701fa0eb9928e00b6f9b3041a851b01f613b811a46', 'slot': {'start': 6214, 'end': 6359, 'draft': "I haven't published neighbourhood police history, planning applications or building permits here yet. That gap doesn't mean nothing has happened.", 'attribute': False, 'id': 'shell.shell-b1bb7e6e-036'}, 'element': {'tag': 'p', 'attributes': {}, 'opening_tag': '<p>'}, 'semantic_class': 'source-status-limitation'}, 'shell.shell-b1bb7e6e-037': {'packet_sha256': '55e597ed1feb589f2dac02083fee50fc63f097e172d6ba15f42c53dbd04e5fb3', 'slot': {'start': 6373, 'end': 6469, 'draft': "Beach results on Scarb.TO describe past samples. Don't use them to decide whether to swim today.", 'attribute': False, 'id': 'shell.shell-b1bb7e6e-037'}, 'element': {'tag': 'p', 'attributes': {}, 'opening_tag': '<p>'}, 'semantic_class': 'source-status-limitation'}, 'shell.shell-b1bb7e6e-038': {'packet_sha256': '56b3d78f35b3bba311ea5c20d4cb281fb63566602c1aa9285ed15e9c03d778de', 'slot': {'start': 6629, 'end': 6658, 'draft': 'City neighbourhood boundaries', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-038'}, 'element': {'tag': 'a', 'attributes': {'href': 'https://open.toronto.ca/dataset/neighbourhoods/', 'target': '_blank', 'rel': 'noopener noreferrer'}, 'opening_tag': '<a href="https://open.toronto.ca/dataset/neighbourhoods/" target="_blank" rel="noopener noreferrer">'}, 'semantic_class': 'source-licence-attribution'}, 'shell.shell-b1bb7e6e-039': {'packet_sha256': '9720b9a58c2c4f6ba3bab79a9fc75b1fbcf051cc1eb5fecf4a2475f7d7839ab2', 'slot': {'start': 6675, 'end': 6749, 'draft': 'Contains information licensed under the Open Government Licence – Toronto.', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-039'}, 'element': {'tag': 'span', 'attributes': {}, 'opening_tag': '<span>'}, 'semantic_class': 'source-licence-attribution'}, 'shell.shell-b1bb7e6e-040': {'packet_sha256': 'baac0e50eb239df6383b9f13e16432d163b6b55d8ebc4b48a1e599a4a249a260', 'slot': {'start': 6788, 'end': 6898, 'draft': "Sharing the data? Check the City's source and licence terms first, and keep the attribution and dates with it.", 'attribute': False, 'id': 'shell.shell-b1bb7e6e-040'}, 'element': {'tag': 'span', 'attributes': {'class': 'reuse-note'}, 'opening_tag': '<span class="reuse-note">'}, 'semantic_class': 'source-licence-attribution'}, 'shell.shell-b1bb7e6e-041': {'packet_sha256': 'a744179e4f966bdf1825407bc3c43ef441502000f6fecaadcde2c29f4bd38c74', 'slot': {'start': 6918, 'end': 7016, 'draft': "I'm an AI-assisted guide to public records, not an official City service or a first-hand reporter.", 'attribute': False, 'id': 'shell.shell-b1bb7e6e-041'}, 'element': {'tag': 'span', 'attributes': {}, 'opening_tag': '<span>'}, 'semantic_class': 'source-licence-attribution'}, 'shell.shell-b1bb7e6e-042': {'packet_sha256': 'd0382525e8f83b0b57403511bd9becff3d4a08baf3020d4cc639fe74eaf2d3b0', 'slot': {'start': 7042, 'end': 7055, 'draft': 'Scarb.TO home', 'attribute': False, 'id': 'shell.shell-b1bb7e6e-042'}, 'element': {'tag': 'a', 'attributes': {'href': '/'}, 'opening_tag': '<a href="/">'}, 'semantic_class': 'action-or-accessible-label'}}

def neighbourhood_context(packet):
 identity=packet['id'];v.need(identity in NEIGHBOURHOOD_CONTEXTS,'Unsupported neighbourhood template packet')
 bound=NEIGHBOURHOOD_CONTEXTS[identity];v.need(v.digest(packet)==bound['packet_sha256'],'Neighbourhood packet changed')
 sources=verify_neighbourhood_sources()
 record=json.loads((ROOT/'config/scarb-static-shells.json').read_text(encoding='utf8'))['docs/neighbourhood-page.template.html']
 v.need(v.digest(record)==NEIGHBOURHOOD_RECORD_SHA256 and len(record['slots'])==43,'Neighbourhood template inventory changed')
 from scripts.scarb_static_materialize import discover
 v.need(discover(record['source'])==[{k:value for k,value in s.items() if k not in ('id','fields')} for s in record['slots']],'Neighbourhood source ranges changed')
 slot=bound['slot'];v.need(slot in record['slots'],'Neighbourhood slot changed')
 return {'path':'docs/neighbourhood-page.template.html','source_sha256':sources,'slot_range':[slot['start'],slot['end']],'attribute':slot['attribute'],'element':bound['element'],'semantic_class':bound['semantic_class'],'locks':packet['locks'],'template_fields':{'NAME':'Public neighbourhood name, HTML-escaped at render time','CODE':'Qualified public neighbourhood code, HTML-escaped','SLUG':'Canonical slug from public name; fixed route generation'},'meaning':'Exact reusable slot for 30 qualified neighbourhood pages, not a claim about a particular private selection. Preserve element, attribute, link destination, template fields and semantic class. Keep inspection date versus current safety, coordinate-calculated boundaries versus source labels, records versus unique businesses, neighbourhood versus ward/address representation, missing feeds versus no events, historical beach samples and exact source/licence attribution distinctions. Share uses canonical URL with supported fallback; print includes loaded records and restores state; show-more expands records, not a new source refresh. Do not turn editorial interest into invented findings or successful operations.'}

HOME_FILTER_SLOTS={
 'shell.shell-b04b38d4-014':('<aside class="filters" aria-label="Map filters">','Map filters',True),
 'shell.shell-b04b38d4-016':('<button class="mobile-filter-toggle" id="toggle-filters" type="button" aria-expanded="false" aria-controls="filter-options">Filters</button>','Filters',False),
}
HOME_FILTER_BEHAVIOR_PINS={
 'docs/app.mjs':'f5d46d07bd8a2c670831fa4b60c87930f4af76ee02c8dfc90b002dc8dc007b9d',
 'docs/styles.css':'329e6c662ca681c65a9392305403de33ce4249e5d23cb4d62e3ec8f5859ee598',
}

def home_filter_context(packet,raw,text):
 from scripts.scarb_static_materialize import discover
 identity=packet['id'];v.need(identity in HOME_FILTER_SLOTS,'Unsupported home filter label')
 anchor,label,attribute=HOME_FILTER_SLOTS[identity]
 options='<div id="filter-options" class="filter-options">'
 v.need(text.count(anchor)==1 and text.count(options)==1 and text.count('id="toggle-filters"')==1
        and packet['draft']==label and packet['kind']=='functional' and packet['locks']=={},'Exact homepage filter disclosure changed')
 for path,digest in HOME_FILTER_BEHAVIOR_PINS.items():
  v.need(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,'Homepage filter disclosure behavior changed')
 shell=json.loads((ROOT/'config/scarb-static-shells.json').read_text(encoding='utf8'))['docs/index.html']
 v.need(discover(shell['source'])==[{k:value for k,value in s.items() if k not in ('id','fields')} for s in shell['slots']],
        'Homepage filter source slot inventory changed')
 slots=[s for s in shell['slots'] if s['id']==identity]
 v.need(len(slots)==1 and slots[0]['draft']==label and slots[0]['attribute']==attribute
        and shell['source'].count(anchor)==1 and shell['source'].count(options)==1,'Homepage filter canonical slot changed')
 slot=slots[0];start=shell['source'].index(anchor)
 v.need(start<=slot['start']<slot['end']<=start+len(anchor),'Homepage filter slot belongs to different control')
 meaning=('Accessible name of the homepage filter region, not a button or status.'
          if attribute else 'Initial collapsed mobile button label; expansion reveals filter options and runtime switches to the separate hide-filters label.')
 return {'path':'docs/index.html','source_sha256':hashlib.sha256(raw).hexdigest(),'anchor_html':anchor,
         'behavior_source_sha256':HOME_FILTER_BEHAVIOR_PINS,'slot_role':'region-name' if attribute else 'initial-disclosure-label',
         'meaning':meaning+' Keep the region and disclosure labels aligned with the existing controls. Do not claim the label applies filters, changes data, or reports success.'}


# Exact homepage Food inspection results-list states. Context only: no text,
# source data, renderer, prior context bytes or admission contract changes.
HOME_LIST_PINS={
 'docs/app.mjs':'f5d46d07bd8a2c670831fa4b60c87930f4af76ee02c8dfc90b002dc8dc007b9d',
 'docs/index.html':'2ec549f9cb4a193c5bae436545533ab093a4ade4e95526648fc825aaf0391db9',
}
HOME_LIST_STATES={
 'static.app-38':('93e2f920c20fd987138fb16d671ac76736821b21a555ca011b374aee0400c1cb','functional','Scarb.TO',
  "dineSafeLoadState==='loading'?staticCopy('app-38'):staticCopy('app-39')",
  'Loading before a checked inspection snapshot is ready; not a failed request or a zero result.'),
 'static.app-39':('bcf79c8af5238a177dbc42cb4ccf44005bdf8258ab79e9f5381860dc78955766','safety','DineSafe',
  "dineSafeLoadState==='loading'?staticCopy('app-38'):staticCopy('app-39')",
  'No checked snapshot ready after excluding loading and error. Not a zero-match result or a claim no inspections occurred.'),
 'static.app-40':('4e8a8724a624c606bf4b04cdb8ce17980bdca9528c102c53a0153279f06eef32','safety','Scarborough',
  "list.append(els('p','empty',staticCopy('app-40')));",
  'Checked snapshot ready, no records match current filters/map view. Existing controls may clear filters or fit the map; never infer no incidents or promise results.'),
}

def home_list_context(packet):
 identity=packet['id']; v.need(identity in HOME_LIST_STATES,'Unsupported homepage results-list state')
 digest,kind,lock,anchor,meaning=HOME_LIST_STATES[identity]
 v.need(v.digest(packet)==digest and packet['kind']==kind and packet['locks']=={'VALUE_0':lock},
        'Homepage results-list packet or factual lock changed')
 sources={path:(ROOT/path).read_bytes() for path in HOME_LIST_PINS}
 v.need(all(hashlib.sha256(raw).hexdigest()==HOME_LIST_PINS[path] for path,raw in sources.items()),
        'Homepage results-list producer or accessible region changed')
 app=sources['docs/app.mjs'].decode('utf8'); html=sources['docs/index.html'].decode('utf8')
 v.need(app.count(anchor)==1 and app.count("staticCopy('"+identity.removeprefix('static.')+"')")==1
        and app.count("const list=$('record-list');")==1
        and html.count('id="record-list"')==1 and html.count('id="results-count" aria-live="polite"')==1,
        'Homepage results-list consumer changed')
 return {'path':'docs/app.mjs','source_sha256':HOME_LIST_PINS,'consumer':'renderList/record-list',
         'trigger':anchor,'locks':packet['locks'],'meaning':meaning+
         ' Keep separate from the existing polite results count; no claims about safety, source refresh or current events.'}


# Accessible food-inspection map only; other map modes have distinct producers.
HOME_MAP_ACCESSIBILITY={
 'static.app-16':('d65a238769d37ac33b13955459d58adaa466e56c3fd5cd390fdb61d9b81554c6',True),
 'static.app-17':('9c8573ec78b1d1f32e5bacdf9fc45964c42ada12561aa2f8e7a7de18fef20cd3',False),
}
HOME_MAP_PINS=dict(HOME_LIST_PINS)

def home_map_accessibility_context(packet):
 sources={path:(ROOT/path).read_bytes() for path in HOME_MAP_PINS}
 return _home_map_accessibility_context(packet,sources)

def _home_map_accessibility_context(packet,sources):
 identity=packet['id']
 v.need(identity in HOME_MAP_ACCESSIBILITY,'Unsupported homepage map accessibility state')
 digest,shapes=HOME_MAP_ACCESSIBILITY[identity]
 v.need(v.digest(packet)==digest and packet['kind']=='safety' and packet['locks']=={'VALUE_0':'DineSafe'},
        'Homepage map accessibility packet or factual lock changed')
 v.need(set(sources)==set(HOME_MAP_PINS) and all(hashlib.sha256(raw).hexdigest()==HOME_MAP_PINS[path] for path,raw in sources.items()),
        'Homepage map accessibility source changed')
 app=sources['docs/app.mjs'].decode('utf8'); html=sources['docs/index.html'].decode('utf8')
 consumer="$('map').setAttribute('aria-label',mapLabel);"
 switch="?staticCopy('app-16')\n        :staticCopy('app-17');"
 v.need(app.replace('\r\n','\n').count(switch)==1 and app.count(consumer)==1 and app.count('statusMarkerImagesAvailable=addStatusMarkerImages(map);')==1
        and html.count('id="map" role="region"')==1 and html.count('id="record-list"')==1,
        'Homepage map accessibility consumer changed')
 marker='Marker shapes and letters identify inspection outcomes alongside colour.' if shapes else 'Marker letters identify inspection outcomes alongside colour.'
 return {'path':'docs/app.mjs','source_sha256':HOME_MAP_PINS,'consumer':'syncMapAccessibilityLabel/aria-label',
         'state':'inspection marker images available' if shapes else 'inspection marker image fallback',
         'locks':packet['locks'],'must_preserve':['Interactive map of places with DineSafe records.',marker,
         'Each inspection outcome is written out in the matching list.'],
         'meaning':'Food-inspection map accessible name only. Do not describe a different map mode, rely only on colour, or claim marker shapes in fallback.'}


# The homepage selected-calls adapter has its own status, source note and list
# renderers. Do not extend the separate selected-calls source contract.
HOME_SELECTED_CALLS_PINS={**HOME_LIST_PINS,
 'docs/selected-calls.mjs':'3be2e3bebbda9d57ac55cad86f998b14380ae9807ca4b7b421b88a9629232a4a',
}
HOME_SELECTED_CALLS_STATES={
 'static.app-02':('75d7161ce4c7d75c2f8aeace91d7a0417daa0656ebf25f0de8ff55c3f2f8154f', 'functional', {'VALUE_0': '41', 'VALUE_1': '42', 'VALUE_2': '43'}, 'loading', ('Loading selected TPS call counts for Divisions 41, 42 and 43.', 'No counts have been rendered in this loading state.')),
 'static.app-03':('0f3c35259386b8f0922d25755e420d3fc3e41fad60461e5384d05ece2c059a06', 'safety', {'VALUE_0': '41', 'VALUE_1': '42', 'VALUE_2': '43'}, 'source attribution', ('Source is Toronto Police Service selected calls for Divisions 41, 42 and 43.', 'Not all calls, confirmed crimes, or neighbourhood incidents.')),
 'static.app-dynamic-02':('dd96df98eb596e7b330d80bb71971ae928c9e0aeda9a1e82e4274050657d30d9', 'safety', {'VALUE_0': '{{VALUE0}}', 'VALUE_1': '{{VALUE1}}'}, 'validated counts status', ('First date is when TPS changed the records; second date is when Scarb.TO checked them.', 'Older counts are removed.')),
 'static.app-dynamic-04':('32175f5daa9dc2fc4cf737ebddd263a113a196b78edec8b150bb6d929a14cd88', 'functional', {'VALUE_0': '{{VALUE0}}'}, 'available list total', ('Sum of the selected call counts in the available division rows.', 'Describe selected calls, not confirmed crimes, a neighbourhood count, or all requests.')),
 'static.app-dynamic-05':('ce58d6623251af99faa2aa5cb6c4c952b34313e34ce48a852575a7fb57203769', 'functional', {'VALUE_0': '{{VALUE0}}'}, 'available division row label', ('Identify the Toronto Police division for the matching row.', 'Use only the actual division value supplied by the qualified renderer.')),
}
HOME_SELECTED_CALLS_ANCHORS={
 'static.app-02':"selectedCallsViewState.reason==='loading'?staticCopy('app-02')",
 'static.app-03':"sourceDetail(staticCopy('app-audit-source'), staticCopy('app-03'));",
 'static.app-dynamic-02':"staticCopy('app-dynamic-02',{ VALUE0:(readerDateTime(selectedCallsViewState.sourceEditedAt)), VALUE1:(readerDateTime(selectedCallsViewState.fetchedAt)) })",
 'static.app-dynamic-04':"staticCopy('app-dynamic-04',{ VALUE0:(view.counts.reduce((sum,row)=>sum+row.count,0).toLocaleString('en-CA')) })",
 'static.app-dynamic-05':"staticCopy('app-dynamic-05',{ VALUE0:(row.division.slice(1)) })",
}

def home_selected_calls_context(packet):
 identity=packet['id']
 v.need(identity in HOME_SELECTED_CALLS_STATES,'Unsupported homepage selected-calls runtime state')
 digest,kind,locks,state,meaning=HOME_SELECTED_CALLS_STATES[identity]
 v.need(v.digest(packet)==digest and packet['kind']==kind and packet['locks']==locks,
        'Homepage selected-calls packet or locks changed')
 sources={path:(ROOT/path).read_bytes() for path in HOME_SELECTED_CALLS_PINS}
 v.need(all(hashlib.sha256(raw).hexdigest()==HOME_SELECTED_CALLS_PINS[path] for path,raw in sources.items()),
        'Homepage selected-calls producer changed')
 app=sources['docs/app.mjs'].decode('utf8')
 html=sources['docs/index.html'].decode('utf8')
 producer=sources['docs/selected-calls.mjs'].decode('utf8')
 anchor=HOME_SELECTED_CALLS_ANCHORS[identity]
 v.need(app.count(anchor)==1 and app.count("if(state.mode==='selected-calls'){")>=2
        and producer.count('const DIVISIONS = Object.freeze(["D41", "D42", "D43"]);')==1
        and html.count('id="results-count" aria-live="polite"')==1 and html.count('id="source-provenance-content"')==1,
        'Homepage selected-calls consumer changed')
 return {'path':'docs/app.mjs','source_sha256':HOME_SELECTED_CALLS_PINS,'consumer':anchor,
         'state':state,'locks':locks,'must_preserve':list(meaning),
         'meaning':'Selected call counts only; not mapped incidents, neighbourhood totals or real-time data. Runtime locks remain exact.'}


# Food-inspection list copy binds the actual filtered view/card controls, not
# the separate selected-calls and beach renderers.
HOME_DINESAFE_LIST_STATES={
 'static.app-26':('e0dd33f18fa0a0c21dc4f45fa348308db91c916f79eb1849519fcc3a35fb6254', 'functional', {'VALUE_0': 'Scarb.TO'}, "staticCopy('app-26')", 2, ('Added to Scarb.TO means the record first appeared here, not that the City first inspected or opened the place.', 'Keep the same meaning in the recent-view kicker and first-seen event title.')),
 'static.app-28':('65916485de26fa61e433e51dd2d932ca65543603fd3b7d7fc0c7a6e9643a7d77', 'functional', {'VALUE_0': 'DineSafe'}, "staticCopy('app-28')", 1, ('This is a view of places with DineSafe records; it does not classify all Scarborough businesses or their present safety.',)),
 'static.app-30':('d8303b6dbe5a515d7bdb53d537f22e00b066efcbae3e2ffe96a64f6c3f3b4ecb', 'editorial', {'VALUE_0': 'DineSafe'}, "staticCopy('app-30')", 1, ('In first person, report what Scarb found in DineSafe: comparing the records day to day brings changes into view.', 'The inspection date may be earlier than the date on which a record first appeared on Scarb.TO.')),
 'static.app-32':('544fc4aa0ea78ac72a7ade596273a0cba3856809b2a142fce6538ca457c853bc', 'editorial', {'VALUE_0': 'DineSafe'}, "staticCopy('app-32')", 1, ('Invite the reader to pick a familiar name and follow its inspection trail with Scarb. Show the latest DineSafe records in this snapshot, not a live feed.', 'Readers can follow the original City record link for each place.')),
 'static.app-43':('366250cac151c248439c0cf11f627e62fc555006ee6d9724b5a7c316122ddf7c', 'functional', {'LAYOUT_SUFFIX': ' ', 'VALUE_0': 'Scarb.TO'}, "staticCopy('app-43')+publishedAt(entry.event.detected_at)", 1, ('The appended value is when Scarb.TO detected the event, not the City inspection date.', 'Preserve the exact separator and trailing layout space.')),
 'static.app-46':('260c35504a5c40b2704a8e855c692c32784c9e1e29b33270d56510e6bb055b03', 'functional', {'VALUE_0': 'DineSafe'}, "staticCopy('app-46')", 1, ('The link opens the City DineSafe record page for the matching source record.', 'Do not relabel it as an establishment home page or verification of current safety.')),
 'static.app-dynamic-08':('d06d58876a9a262af43fb7d94d252290348f765f1f2ad68193afd842c244e820', 'functional', {'VALUE_0': '{{VALUE0}}'}, "staticCopy('app-dynamic-08',{ VALUE0:(records.length.toLocaleString('en-CA')) })", 1, ('The supplied total counts the matching records in the current rendered-view scope, not all City records or only the first loaded page.',)),
 'static.app-dynamic-09':('527f6d4209a30eca7632f37bb9e1cb8b0c4fa8027bcfb735bdc312fa3b7413f1', 'functional', {'VALUE_0': '{{VALUE0}}'}, "staticCopy('app-dynamic-09',{ VALUE0:(entry.event.previous_status||staticCopy('app-audit-unknown')) })", 1, ('For a status-change event, the supplied outcome is the previous recorded status or the explicit unknown fallback.', 'Do not say it is the new or current City outcome.')),
 'static.app-dynamic-12':('63f7939a284f06afe7a6419daad8566c28ccc4b098dce21db5e43e7823a00a2e', 'functional', {'VALUE_0': '{{VALUE0}}'}, "staticCopy('app-dynamic-12',{ VALUE0:(Math.min(80,remaining).toLocaleString('en-CA')) })", 1, ('This button reveals the next displayed count of already matched records, up to the retained page increment.', 'It does not fetch a new snapshot, reset filters, or promise records beyond that count.')),
}

def home_dinesafe_list_context(packet):
 identity=packet['id']
 v.need(identity in HOME_DINESAFE_LIST_STATES,'Unsupported homepage DineSafe list consumer')
 digest,kind,locks,anchor,count,meaning=HOME_DINESAFE_LIST_STATES[identity]
 v.need(v.digest(packet)==digest and packet['kind']==kind and packet['locks']==locks,
        'Homepage DineSafe list packet or locks changed')
 sources={path:(ROOT/path).read_bytes() for path in HOME_LIST_PINS}
 v.need(all(hashlib.sha256(raw).hexdigest()==HOME_LIST_PINS[path] for path,raw in sources.items()),
        'Homepage DineSafe list source changed')
 app=sources['docs/app.mjs'].decode('utf8')
 html=sources['docs/index.html'].decode('utf8')
 v.need(app.count(anchor)==count and app.count("const list=$('record-list');")==1
        and html.count('id="record-list"')==1 and html.count('id="results-count" aria-live="polite"')==1,
        'Homepage DineSafe list consumer changed')
 return {'path':'docs/app.mjs','source_sha256':HOME_LIST_PINS,'consumer':anchor,'occurrences':count,
         'locks':locks,'must_preserve':list(meaning),
         'meaning':'Homepage food-inspection list only. Keep official source, inspection, and Scarb.TO observation distinct.'}


# Qualified shared runtime for generated neighbourhood pages, separate from
# static template slots; context only, not a new source or publication route.
NEIGHBOURHOOD_RUNTIME_PINS={k:NEIGHBOURHOOD_SOURCE_PINS[k] for k in (
 'docs/neighbourhood-page.mjs','docs/neighbourhood-page.template.html','docs/area-selection.mjs')}
NEIGHBOURHOOD_RUNTIME={
 'static.neighbourhood-page-dynamic-01':('c2d848c90ff1254ba015242dd3a3e315a8a3ca220d382c878ae56ca944829ea7', 'functional', {'VALUE_0': '{{VALUE0}}', 'VALUE_1': '{{VALUE1}}'}, "staticCopy('neighbourhood-page-dynamic-01',", 'renderWards', ('Give the actual ward code and name, with an invitation to find the City councillor.', 'Ward overlaps are not an address or electoral assignment.')),
 'static.neighbourhood-page-dynamic-02':('97cdf0c1874a4e1abcb4f41eddae0d1f6515c0f6bfa04e2cd9803332592de5eb', 'functional', {'VALUE_0': '{{VALUE0}}'}, "staticCopy('neighbourhood-page-dynamic-02',", 'renderRecords', ('The supplied date is the City inspection date for this matched record.',)),
 'static.neighbourhood-page-dynamic-03':('03e641ac6e129d480004e934edcea21f54e4265befc7d029e822e112c8c17c39', 'functional', {'VALUE_0': '{{VALUE0}}', 'VALUE_1': '{{VALUE1}}', 'VALUE_2': '{{VALUE2}}'}, "staticCopy('neighbourhood-page-dynamic-03',", 'renderRecords', ('Give the matching related City record ID, its recorded result or explicit missing-result text, and its inspection date.', 'It is a separate source record, not proof of the selected establishment’s present outcome.')),
 'static.neighbourhood-page-dynamic-04':('7c66e61b3cbdbf0bbf67afa3c4e1b6accea8e20c6bc13fed9dff5f47248b215e', 'functional', {'VALUE_0': '{{VALUE0}}', 'VALUE_1': '{{VALUE1}}', 'VALUE_2': 'DineSafe'}, "staticCopy('neighbourhood-page-dynamic-04',", 'renderRecords', ('First count is currently shown, second is the total matched DineSafe source records.', 'These records were matched to this neighbourhood, not all local businesses.')),
 'static.neighbourhood-page-dynamic-05':('716684a8280a6161680bf2ce2b068d25de77aecf75276187a1baff5fe1f5eb71', 'functional', {'VALUE_0': '{{VALUE0}}', 'VALUE_1': 'Scarb.TO'}, "staticCopy('neighbourhood-page-dynamic-05',", 'loadPage', ('The title pairs the exact qualified public neighbourhood name and Scarb.TO.', 'It identifies the page, not findings or data freshness.')),
 'static.neighbourhood-page-dynamic-06':('d0b25afed4e583e729151d36d7a1aab2b90cb59264a3d58d331eb7a9746e4081', 'safety', {'VALUE_0': '{{VALUE0}}'}, "staticCopy('neighbourhood-page-dynamic-06',", 'loadPage', ('Warn that results may be out of date, state when they were last checked, and direct the reader to the City record for anything newer.',)),
 'static.neighbourhood-page-dynamic-07':('c56416652e13ab91d873db15b21e5b58caaa485d96816f87733e2e5338bdb414', 'safety', {'VALUE_0': '{{VALUE0}}'}, "staticCopy('neighbourhood-page-dynamic-07',", 'loadPage', ('State when these food inspection records were checked and that they are not live results.',)),
 'static.neighbourhood-page-dynamic-08':('c5427331e72b5a4f127abed1eee54dd41b14646abdd696937be342e36a17d54b', 'safety', {'VALUE_0': 'Scarb.TO', 'VALUE_1': '{{VALUE0}}', 'VALUE_2': '{{VALUE1}}'}, "staticCopy('neighbourhood-page-dynamic-08',", 'loadPage', ('Separate the Scarb.TO successful check from the City catalogue timestamp, whose timezone is unspecified.', 'Both are distinct from an inspection date and do not establish current conditions.')),
}

def neighbourhood_runtime_context(packet):
 identity=packet['id']
 v.need(identity in NEIGHBOURHOOD_RUNTIME,'Unsupported neighbourhood runtime consumer')
 digest,kind,locks,anchor,consumer,meaning=NEIGHBOURHOOD_RUNTIME[identity]
 v.need(v.digest(packet)==digest and packet['kind']==kind and packet['locks']==locks,
        'Neighbourhood runtime packet or locks changed')
 sources={path:(ROOT/path).read_bytes() for path in NEIGHBOURHOOD_RUNTIME_PINS}
 v.need(all(hashlib.sha256(raw).hexdigest()==NEIGHBOURHOOD_RUNTIME_PINS[path] for path,raw in sources.items()),
        'Neighbourhood runtime source changed')
 app=sources['docs/neighbourhood-page.mjs'].decode('utf8')
 html=sources['docs/neighbourhood-page.template.html'].decode('utf8')
 v.need(app.count(anchor)==1 and app.count('function '+consumer+'(')==1
        and html.count('id="feed-status"')==1 and html.count('id="source-provenance"')==1,
        'Neighbourhood runtime consumer changed')
 return {'path':'docs/neighbourhood-page.mjs','source_sha256':NEIGHBOURHOOD_RUNTIME_PINS,'consumer':consumer,
         'anchor':anchor,'locks':locks,'must_preserve':list(meaning),
         'meaning':'Generated neighbourhood pages only. Keep existing runtime values, official attribution and source limits.'}


# Exact editable weekly HTML renderer only; never activate an archive rewrite
# or extend the separately pinned RSS producer.
# Verified fefaba0 Git blob bytes (LF) and clean GMKtec checkout bytes (CRLF).
# Match exact whole-file hashes; context records the representation actually read.
WEEKLY_HTML_PINS={
 'scripts/build_weekly_brief.py':('b990db32234c6576603037c5229459b9f0e42c9b1d05190a38d878a6a2ac2415','a5af87e4f32b07def1dc0c5ae5d9c5f9e0b4d548927195a40d67aed203992cba'),
 'scripts/scarb_voice.py':('48921ff3372649708e9ed3405a31aa824b9d6f76da71f86c17d9a79b4beb2e45','eaa22ee4c6bb8f15eaa972d0bf6ddebe8db4c5929f17de8f33608232f0a8480b'),
}
WEEKLY_HTML_STATES={
 'python.weekly-counts':('128a6b0e03d27ded4619e4ede47aa59968f980cea6ff786ecffd803b38b945a5', 'safety', {'VALUE_0': '{{COUNT}}', 'VALUE_1': '{{AREAS}}', 'VALUE_2': 'Scarb.TO'}, 'C', ('Keep exact recorded update count and number of Scarb.TO-matched neighbourhoods.', 'A place can have multiple updates; invite readers to see how the records fit together.')),
 'python.weekly-geography':('8bf631de74cf8db36b3a1e1323456e386ff19be21b2e9ca619ff532c6287bf4a', 'safety', {'VALUE_0': 'DineSafe', 'VALUE_1': 'Scarb.TO', 'VALUE_2': 'DineSafe', 'VALUE_3': 'Scarborough', 'VALUE_4': 'Scarb.TO'}, 'V', ('In first person, explain that Scarb.TO matches City DineSafe coordinates to City neighbourhood boundaries; DineSafe does not supply the neighbourhood label.', 'Source coordinate error can give the wrong neighbourhood; some neighbourhoods cross the six Scarborough ward selection boundaries.', 'Inspection date, when Scarb.TO first recorded the update, and page publication are distinct; newly added does not mean a new business.')),
 'python.weekly-source-limit':('76c6f92eabb81834f9e7ecc80dad4177a027a88410a8574de31e7d9c72440b5c', 'safety', {'VALUE_0': 'DineSafe'}, 'V', ('The updates are from City DineSafe records, not visits.', 'The brief is not a complete record of City activity and results may have changed.')),
 'python.weekly-source-note':('8e755c1139cf89688397b02099ad8592bcb82aa91158e3038f27b30e167ec426', 'safety', {'VALUE_0': 'DineSafe'}, 'V', ('Each place name leads to the City DineSafe record; that source may contain newer information than the inspection date shown.', 'Link behaviour must not imply fresh inspection or current conditions.')),
 'python.weekly-source-invitation':('d45b52c19541b3e47a8579ea3dd6f366a86b115c674865b078a58934dde79e27', 'functional', {'LAYOUT_SUFFIX': ' '}, 'V', ('Invite readers to follow the trail to the following official dataset link.', 'Keep the exact separator and trailing space before the link.')),
 'python.weekly-source-name':('04afd63fd4d7b9bbdf3f09d74b5ec883abde1722513989b4c5d400d13fd26e2f', 'functional', {'VALUE_0': 'DineSafe'}, 'V', ('Identify the linked dataset as City of Toronto DineSafe Open Data.', 'Keep this official source identity distinct from the individual City establishment record and the adjacent licence link.')),
 'python.weekly-preparation':('bec263f592bd4c2fd0cb637b783c17d4218de41aa17aed86cd6975f189fa5578', 'safety', {'VALUE_0': '{{ID}}', 'VALUE_1': '{{REVISION}}', 'VALUE_2': '{{FIRST}}', 'VALUE_3': '{{REVISED}}'}, 'C', ('Keep exact edition ID, revision, first-prepared UTC value and revision value; these are edition preparation times, not publication.', 'Preserve the first-person disclosure that individual addresses and map coordinates are left out.')),
 'python.weekly-correction':('867354b2e785d2c97562593e2e6b75473986c4abf7702a46707926b562116771', 'functional', {'VALUE_0': '{{REVISION}}'}, 'C', ('Label the existing correction and exact revision number, introducing the independent supplied correction explanation.', 'Only rendered if revision is above one; do not invent a correction or change its wording.')),
 'python.weekly-updated':('1fb92bfe535d9ebad12facd9837dd5a5e436b8598455edd249787d48b2c1fb7f', 'functional', {'VALUE_0': '{{DATE}}'}, 'C', ('Show the dated update of an existing correction; the runtime date is the revision time interpreted in Toronto.', 'Do not conflate it with first preparation, page publication or any inspection date.')),
}

def weekly_html_context(packet):
 import ast
 identity=packet['id'];v.need(identity in WEEKLY_HTML_STATES,'Unsupported weekly HTML producer context')
 digest,kind,locks,formatter,meaning=WEEKLY_HTML_STATES[identity]
 v.need(v.digest(packet)==digest and packet['kind']==kind and packet['locks']==locks,
        'Weekly HTML packet or locks changed')
 sources={path:(ROOT/path).read_bytes() for path in WEEKLY_HTML_PINS}
 source_hashes={path:hashlib.sha256(raw).hexdigest() for path,raw in sources.items()}
 v.need(all(digest in WEEKLY_HTML_PINS[path] for path,digest in source_hashes.items()),
        'Weekly HTML renderer or formatter changed')
 module=ast.parse(sources['scripts/build_weekly_brief.py'])
 functions={x.name:x for x in module.body if isinstance(x,ast.FunctionDef)}
 key=identity.removeprefix('python.')
 calls=[node for node in ast.walk(functions['_render_voice_edition']) if isinstance(node,ast.Call)
        and isinstance(node.func,ast.Name) and node.func.id==formatter and node.args
        and isinstance(node.args[0],ast.Constant) and node.args[0].value==key]
 v.need(len(calls)==1 and 'prior["html_sha256"]' in ast.unparse(functions['build_weekly_brief']).replace("'",'"')
        and 'html_sha256' in ast.unparse(functions['preserve_weekly_archive']),
        'Weekly HTML call site or archive guard changed')
 return {'path':'scripts/build_weekly_brief.py','source_sha256':source_hashes,
         'consumer':'_render_voice_edition/'+formatter+'/'+key,'locks':locks,'must_preserve':list(meaning),
         'meaning':'Future editable weekly HTML copy only. Existing archived editions and RSS identities are unchanged.'}

EDITORIAL_ENTRY_PINS={
 'docs/index.html':('93283867eba047a32a2866994fb2f496e16aaf5eabc8772407a8823a923eb753','2ec549f9cb4a193c5bae436545533ab093a4ade4e95526648fc825aaf0391db9'),
 'docs/community/index.html':('db2475b3831c70edc8b7fd49ba5e7450c2ddbf8c66183292e62d7390ec02dfac','6690986d1ad8779abe76ecac3db1253882748efcef016be7b47e54f01e2ae1b2'),
 'docs/embed/index.html':('072ad58e394b381d3f7ff0f2e6a73c85703f31abe3dbcf747f466a66f27e4ea5','a32967347bacdc06f4266bb6f08209e2ad11f6bb665f29d07c0e28af6468b9e3'),
}
EDITORIAL_ENTRY_STATES={
 'static.home-title':('a014d351e20bf0b97d4e77311dc626b9ba756deb3a7558f7187476732fb3e6c2','docs/index.html','h1','Lead with curiosity about Scarborough and the stories readers can uncover in its data; this is an invitation, not a claim that any particular finding has been verified.'),
 'static.home-intro':('7f72fd883cae81f02c687cb26fa99b415473b21cafe693d77949a0a8d24e6c36','docs/index.html','p','Keep the first-person curiosity and invite readers to pick a thread and follow it. The map brings together places, inspection results and neighbourhood boundaries with their dates and sources; do not promise complete data, current safety, firsthand reporting or a particular new finding.'),
 'static.community-title':('e5f7ea55c31fcfd47029c843fecde099a155f39e6fe5a9e9fc4c26a5d725b16e','docs/community/index.html','h1','Invite the reader to make a neighbourhood update from local records, not to publish automatically or claim new findings.'),
 'static.community-intro':('0f3f850aebea58410d23f54f53e62da3aefc0ea7f6f38c3b1258de1651bc49c3','docs/community/index.html','p','Invite the reader to choose their part of Scarborough and assemble dated, source-linked findings for print or their website. Evidence remains attached and the user chooses what to share.'),
 'static.embed-intro':('40f5c7b5399918193e75dcb074a10de457fb27ac61c18f695de3d56748321931','docs/embed/index.html','p','Introduce records for this area, not a sitewide census or firsthand discovery. Keep the clear positive invitation to explore the source trail, and retain source dates and links.'),
}

def editorial_entry_context(packet):
 import re
 from html import unescape
 identity=packet['id'];v.need(identity in EDITORIAL_ENTRY_STATES,'Unsupported fixed editorial entry')
 digest,path,tag,meaning=EDITORIAL_ENTRY_STATES[identity]
 v.need(v.digest(packet)==digest and packet['kind']=='editorial','Editorial entry packet changed')
 raw=(ROOT/path).read_bytes();observed=hashlib.sha256(raw).hexdigest()
 v.need(observed in EDITORIAL_ENTRY_PINS[path],'Editorial entry source changed')
 key=identity.removeprefix('static.')
 marks=re.findall(r'<'+tag+r' data-scarb-voice="'+re.escape(key)+r'">([^<>]+)</'+tag+r'>',raw.decode('utf8'))
 phrase=packet['draft']
 for field,value in packet['locks'].items():phrase=phrase.replace('{{LOCK:'+field+'}}',value)
 v.need(len(marks)==1 and unescape(marks[0])==phrase,'Editorial entry consumer changed')
 return {'path':path,'source_sha256':observed,'consumer':tag+'[data-scarb-voice='+key+']','locks':packet['locks'],'meaning':meaning,'boundary':'This is entry-page prose only; no generated or archived editions, source data, published findings or RSS change.'}

def current_contexts(packets):
 current=seam.current_canonical_requests();path=ROOT/'docs/index.html';raw=path.read_bytes();text=raw.decode('utf8');contexts={}
 findings=None;selected_calls=None;community_validation=None
 if any(p['id'].startswith('static.finding-explanation-') for p in packets):
  import subprocess
  findings=json.loads(subprocess.run(['node',str(ROOT/'scripts/scarb_finding_contexts.mjs')],cwd=ROOT,check=True,capture_output=True,text=True,encoding='utf8').stdout)
 if any(p['id'].startswith('static.selected-calls-') for p in packets):
  import subprocess
  selected_calls=json.loads(subprocess.run(['node',str(ROOT/'scripts/scarb_selected_calls_contexts.mjs')],cwd=ROOT,check=True,capture_output=True,text=True,encoding='utf8').stdout)
 if any(p['id'].startswith('static.community-publishing-message-') for p in packets):
  import subprocess
  community_validation=json.loads(subprocess.run(['node',str(ROOT/'scripts/scarb_community_validation_contexts.mjs')],cwd=ROOT,check=True,capture_output=True,text=True,encoding='utf8').stdout)
 for packet in packets:
  identity=packet['id'];v.need(current.get(identity)==packet,'Unsupported or stale context producer')
  if identity.startswith('shell.shell-b1bb7e6e-') or identity=='static.neighbourhood-intro':
   contexts[identity]=neighbourhood_context(packet);continue
  if identity.startswith('static.saved-'):
   contexts[identity]=saved_context(packet);continue
  if identity.startswith('static.community-publishing-message-'):
   v.need(identity in community_validation,'Unsupported Community Publishing validation key');contexts[identity]=community_validation[identity];continue
  if identity.startswith('python.rss-'):
   from scripts.scarb_rss_contexts import contexts as rss_contexts
   contexts.update(rss_contexts([packet]));continue
  if identity.startswith('static.selected-calls-'):
   v.need(identity in selected_calls,'Unbound selected-call context');contexts[identity]=selected_calls[identity];continue
  if identity.startswith('static.finding-explanation-'):
   v.need(identity in findings,'Unbound finding context');contexts[identity]=findings[identity];continue
  if identity in EDITORIAL_ENTRY_STATES:
   contexts[identity]=editorial_entry_context(packet);continue
  if identity in WEEKLY_HTML_STATES:
   contexts[identity]=weekly_html_context(packet);continue
  if identity in NEIGHBOURHOOD_RUNTIME:
   contexts[identity]=neighbourhood_runtime_context(packet);continue
  if identity in HOME_DINESAFE_LIST_STATES:
   contexts[identity]=home_dinesafe_list_context(packet);continue
  if identity in HOME_SELECTED_CALLS_STATES:
   contexts[identity]=home_selected_calls_context(packet);continue
  if identity in HOME_MAP_ACCESSIBILITY:
   contexts[identity]=home_map_accessibility_context(packet);continue
  if identity in HOME_LIST_STATES:
   contexts[identity]=home_list_context(packet);continue
  if identity in HOME_FILTER_SLOTS:
   contexts[identity]=home_filter_context(packet,raw,text);continue
  if identity not in ANCHORS:
   contexts[identity]=area_context(packet,raw,text);continue
  destination,label=ANCHORS[identity];anchor=f'<a href="{destination}" class="about-link">{label}</a>'
  v.need(text.count(anchor)==1 and packet['draft']==label,'Exact unique source anchor missing')
  contexts[identity]={'path':'docs/index.html','source_sha256':hashlib.sha256(raw).hexdigest(),'anchor_html':anchor,'destination':destination,'meaning':'Existing navigation label only; preserve its destination and unambiguous function; no new claims.'}
 return contexts

def context_prompts(packets,models,contexts,authors=None,*,prompt_version=contract.LEGACY_PROMPT):
 v.need(isinstance(contexts,dict) and set(contexts)==set(contract.identities(packets)),'Missing or extra source context')
 bodies=contract.prompts(packets,models,authors,prompt_version=prompt_version)
 def bind(body):
  payload=json.loads(body['input'][0]['content'][0]['text']);payload['source_context']=contexts
  body['input'][0]['content'][0]['text']=json.dumps(payload,sort_keys=True,separators=(',',':'))
  v.need(len(v.encoded(body))<=48000,'Context exceeds input bound');return body
 return bind(bodies) if authors is None else tuple(bind(x) for x in bodies)

def _collect_admitted_editorial_entries(bundle,config,current):
 v.need(set(bundle)=={'solo_v1','solo_v2','grouped'},'Mixed input fields')
 entries={}
 for key,checker in [('solo_v1',v.receipt_check),('solo_v2',solo.receipt_check)]:
  for identity,receipt in bundle[key].items():
   v.need(identity in current and identity not in entries,'Unknown or duplicate solo ID')
   text=checker(receipt,current[identity],config)
   entries[identity]={'text':text,'packet_sha256':v.digest(current[identity]),'receipt_sha256':receipt['sha256'],'origin':receipt['origin']}
 for root in bundle['grouped']:
  # Registry pin selects members: caller-supplied envelope cannot grant membership.
  digest=provenance.file_hash(Path(root)/'manifest.json');pin=provenance.TRUSTED_GROUPED_RUNS.get(digest)
  v.need(pin is not None,'No admitted grouped run')
  ids=list(pin['packet_bindings']);v.need(all(i in current and i not in entries for i in ids),'Unknown or overlapping group')
  packets=[current[i] for i in ids];proof=provenance.verify_grouped_provenance(root,packets)
  env=json.loads((Path(root)/'envelope.json').read_text(encoding='utf8'));authors,_=v.unpack(env['author_response'])
  for packet in packets:
   identity=packet['id'];text=v.text_check(packet,solo.assemble(packet,authors[identity]))
   v.need(v.digest(text)==proof['text_sha256'][identity],'Verified projection differs')
   entries[identity]={'text':text,'packet_sha256':v.digest(packet),'receipt_sha256':digest,'origin':'scarb-grouped-projection-2'}
   if env['version']=='scarb-grouped-run-envelope-3':
    entries[identity].update(origin='scarb-grouped-projection-3',provenance={'version':env['version'],'prompt_version':env['prompt_version'],'manifest_sha256':digest,'packet_id':identity})
 return entries


def compile_admitted_mixed_draft(bundle,config):
 """Pure disabled-by-empty-registry candidate. Not a production-reader artifact."""
 current=seam.current_canonical_requests()
 entries=_collect_admitted_editorial_entries(bundle,config,current)
 v.need(set(entries)==set(current),'Missing full 736-item current catalogue')
 return {'version':'scarb-mixed-production-draft-1','entries':entries}


def compile_disabled_fixed_mixed_draft(bundle,config,state,fixed_records):
 """Offline-only proof; no production artifact version, writer or reader."""
 from scripts import scarb_fixed_wording_candidate as fixed
 current=seam.current_canonical_requests()
 editorial=_collect_admitted_editorial_entries(bundle,config,current)
 v.need(isinstance(fixed_records,dict),'Fixed evidence must be keyed by canonical ID')
 fixed.require_complete_partition(set(current),set(editorial),set(fixed_records))
 entries=dict(editorial)
 for identity,record in fixed_records.items():
  entries[identity]=fixed.verify_reviewed_private_record(state,current[identity],record)
 return {'version':'scarb-disabled-fixed-mixed-proof-1','entries':entries}


def compile_mixed_catalogue(bundle,config,*,state=None):
 """Compile only privately admitted receipts; never promote a supplied draft.
 Public metadata identifies grouped provenance without exposing private records.
 """
 current=seam.current_canonical_requests()
 fixed_bundle=isinstance(bundle,dict) and 'fixed_records' in bundle
 if fixed_bundle:
  from scripts import scarb_fixed_wording_candidate as fixed
  fixed_records=bundle['fixed_records']
  v.need(isinstance(fixed_records,dict),'Fixed evidence must be keyed by canonical ID')
  editorial=_collect_admitted_editorial_entries(
      {key:value for key,value in bundle.items() if key!='fixed_records'},config,current)
  fixed.require_complete_partition(set(current),set(editorial),set(fixed_records))
  draft={'entries':{**editorial,**fixed.verify_canonical_fixed_records(state,current,fixed_records)}}
 else:
  draft=compile_admitted_mixed_draft(bundle,config)
 v.need(len(current)==736 and set(draft['entries'])==set(current),'Complete current 736-item catalogue required')
 entries={}
 for identity,item in draft['entries'].items():
  entry=dict(item)
  if entry['origin']=='scarb-grouped-projection-2':
   entry['provenance']={'version':'scarb-grouped-run-envelope-2','manifest_sha256':entry['receipt_sha256'],'packet_id':identity}
  entries[identity]=entry
 catalogue={'version':'scarb-ai-voice-mixed-2' if fixed_bundle else 'scarb-ai-voice-mixed-1','entries':entries}
 from scripts.scarb_accepted_copy import accepted_resolver
 accepted_resolver(catalogue,{i:v.digest(p) for i,p in current.items()})
 return catalogue


def verify_mixed_catalogue(bundle,config,artifact,*,state=None):
 """Recompile from original admitted evidence; no caller-provided trust claims."""
 path=Path(artifact)
 v.need(path.is_file() and path.stat().st_size<=10*1024*1024,'Mixed catalogue missing or oversized')
 actual=json.loads(path.read_text(encoding='utf8'))
 v.need(v.encoded(actual)==v.encoded(compile_mixed_catalogue(bundle,config,state=state)),'Mixed catalogue differs from admitted receipts')
 return True
