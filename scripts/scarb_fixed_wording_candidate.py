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


DIRECTORY_WORDING = {
    'shell.shell-012700e3-009': ('a26b0c9784ef49578b31def33e9d87337143076f8e32242b6c5f372a187978c6', '129', 'Agincourt North', '/agincourt-north/', ('319b444d39ae5ecb59fc60a263373fb68e54a8cd9c8c445b6c6904a754de27ed', 'da5a2786ba781e0e370ff8231f5feba8a9bace623784c393002ca5f9993d1cc1')),
    'shell.shell-012700e3-010': ('f9cf5563118746c830c9380b2d715492fe0420781718fc0ab2e9270824bdb839', '128', 'Agincourt South-Malvern West', '/agincourt-south-malvern-west/', ('5900d2cc6fff44cab71270c3d7d6933603d938870395d323a1f5c8c179b32cd2', 'fa4220314b35aab5d470fa46c70cc6a74e9d26835af2818f3733c074bd0e4451')),
    'shell.shell-012700e3-011': ('1304a9f6c17a84b1df6e1e761f93b18d773dc4d1055576e1284fa2e405a05233', '157', 'Bendale South', '/bendale-south/', ('9ff62402b3138fbca6ba5ae5f796a63576438a458afdedef207d602df7b95141', 'f084a080faf86a925f1d6b77173b58c6215724af12f2206be570af19f84041bf')),
    'shell.shell-012700e3-012': ('e349c825d3652f449c541e3e1996fb635119dbac89861424177469f566c5e404', '156', 'Bendale-Glen Andrew', '/bendale-glen-andrew/', ('25cb9d40967ded627b36d838b2fc74b60062f3bb8b77fd2151aa79e02f7f83f1', 'f6f34137202a3e5fed5d1968a235dc0b6522678cabd9e24b645b2b17e73aa2a7')),
    'shell.shell-012700e3-013': ('86495560406bdfb54d39b0efea71859c490c88e6f25b82e728eea4eb8f99bdce', '122', 'Birchcliffe-Cliffside', '/birchcliffe-cliffside/', ('533b14a675e18e813af39b76c6114608ef2646fb196ecd4ba6132893a367e2e4', 'c368b213cb420e7a080d4d0169a65afdb063580d4f3a4ed2d0e327eb38f8cd1d')),
    'shell.shell-012700e3-015': ('b2855b957722d91d3965b3b7c9f889f6128c3bb46592ead4b1c71fbf80dd4e3d', '120', 'Clairlea-Birchmount', '/clairlea-birchmount/', ('01e2189d58b5a0023eca3e7c9f59e736fe196e7d6f4293c6697680e86ecb92ed', '43002741e527a5d7aa801dd33bfb886e1c2e6aa54686443835dfc9db98b2f4e3')),
    'shell.shell-012700e3-016': ('802f46512620c6eaeb882a8a3c1d583d9d56e6acb6793528ed3954fff7a5fdf6', '123', 'Cliffcrest', '/cliffcrest/', ('9ec09b2adaaf5c41a64d1c1b4e8c858c84c801b09d9adad50885810e0abf3d6e', 'cccd49cc2766bb344acfcbb175f56f7ef21367e8e6fd640c2c2fd529136cd9f4')),
    'shell.shell-012700e3-017': ('16f960bf764f69657d8943697ac128ccdce9a5ab5633ea5a0c5aaaf7b4e93b15', '126', 'Dorset Park', '/dorset-park/', ('16e82ec38bdd896d4b754c83a150974d15e339ce870fb01e460f915b48ee1145', '37ed034796deceb4a5309350f3c2d47ba9c33c4e596eddaa5d9aca0e9cdf2592')),
    'shell.shell-012700e3-018': ('be2ee395309d4ca9a326d71528bd155ab22f45d1490731bbeee3608df13173f1', '148', "East L'Amoreaux", '/east-l-amoreaux/', ('1dbedf2514fb1fd8f011ed08a38dbaf05d9f4ccfbccd8aa7064a08e83ecc3814', '27679994b0b4a7c7134ae4e0da4bfbef5bcb8311327d2adff105d4632165e612')),
    'shell.shell-012700e3-019': ('5901a6a016b52cbb8ef7c71ca6faeb4f3c89cfc13ac734d53d988057dd2011e6', '138', 'Eglinton East', '/eglinton-east/', ('813c9dca306760d440ff196823ed96e666459c94c84cb0e2ad69b2fa37bc7295', '9253a499d7801cbeab637f3642112cde75690477ffb92aa5b5dcad024d860338')),
    'shell.shell-012700e3-020': ('309ffae7d70cfc73acbec68b8f446c4aa04ccf5c0822df96a3c0a9d61b86dee9', '141', 'Golfdale-Cedarbrae-Woburn', '/golfdale-cedarbrae-woburn/', ('cf7c45f97227ebe14cce5c4469e3d262f397c69a919d75466322ec2e8b5568d8', 'f96ececb4cc33bb330832689d3b74bcbc544afd255f7f6be13acd2d3f2301a65')),
    'shell.shell-012700e3-021': ('a7beafb61d4a736376726608fca5ab9a97fa0ee1ff23eba2b312ee3cccbf2f30', '140', 'Guildwood', '/guildwood/', ('2a3f993ec0c12a3bb0470d82ebb05d392d9177cec69f9581c7054e6f7eb2c9a9', '5317023ca53eca1b34607082a444bee72a541b3e8f916da5e8e1a68618004854')),
    'shell.shell-012700e3-022': ('52665f01a030dd185a4a3027a4f9da8fc729840fa50629a73eccf57bff51c6a2', '134', 'Highland Creek', '/highland-creek/', ('a9beacf9f47715c745ad136a1f5fd6c08c31926ce38da1de10394f0e9c62cbd9', 'da24b3417769d582456e686d1cac0c51129162ec71f2e2e33b47eca021a8d9f9')),
    'shell.shell-012700e3-023': ('c6a601b8b220aa5652bd3f74c61d3a6f15a52758109fc41d5f8e2c575f62e895', '125', 'Ionview', '/ionview/', ('0350a93366ad5b47d41b3bc2033ca631c9db30fbbcfcb96a5ac8c6911f55fa86', 'e1abd95690735b973b0eba70ca960914e943c35c2037c90327278aa18fc9afe3')),
    'shell.shell-012700e3-024': ('7878dd9b86a64f6468bdc7e32e66056486e8da4053fa4174567d0c62c0b1bddb', '124', 'Kennedy Park', '/kennedy-park/', ('4ac17887988459bde5764de5a248c090004ddc46e82428cb7cc7558a42b710c4', '84e3097e270a004627585fed36a8a853892c81d9ff2c23666c595efb0b9a5ff7')),
    'shell.shell-012700e3-025': ('4c80f3750c4b41337e684a9b49ff5fe54e939aec89d75276c45970f049b040cf', '147', "L'Amoreaux West", '/l-amoreaux-west/', ('816ced1144002c9f9a1a799129023049f3dfff6f8e3afbaa7ce1f146ee0e4bcc', '99423d5c19f7d53a5f2105a3f1376a339bc94298e4e1d2a05aa4a2e6ad63ad63')),
    'shell.shell-012700e3-026': ('80f57f39cef6e560a20005d3d0c670c6ee32920d65010596de16ea2c68baa2b0', '146', 'Malvern East', '/malvern-east/', ('2db08fd860d30a71564f36497115e5168494c6754b5557b68a18d141931dc3cb', '4c7986341a765ce932b11c8b593332214f94e56b99b1b165384084d2d51c13c7')),
    'shell.shell-012700e3-027': ('44d204ec3fa18e416ca5034c0e704ec66cbb2ab7a30f8929e981dccc7eb33308', '145', 'Malvern West', '/malvern-west/', ('47b71df1ee28e85c71bd46468599a92f1b205d623a2570a0ce77ac872855dc7e', 'cf0a3834fc6ce435b16fcf1a895eb50a4da2413fcff7f80a3e8d462bf86d710b')),
    'shell.shell-012700e3-028': ('146bab4205e5ce8cc5c77bb88c7394ec9316755a3b380f698fa76c7c43cba52d', '130', 'Milliken', '/milliken/', ('3890431d1c56a2f68e7d5d58e956166a4bd84e7e962159b6a8a95e836c462051', 'ffb54fc311276a5635a7f976ae01a843f07086f351c424c82d8b08941561c6ca')),
    'shell.shell-012700e3-029': ('9869156f1dab1044948b87bb1e7705020cf9987c5f1822e9f01174593ac1ca2a', '135', 'Morningside', '/morningside/', ('90d207cc69e1ca666a20bdaf7b03292073839149e95fe5c66bcb87e2e7e56708', 'e1781875295f1c52001d9ec523270d333459eb79889714536d9e89b181224fdf')),
    'shell.shell-012700e3-030': ('cfda571b16727f352b183b68d61a6571ebf2291624e4aee1cf1608e01f9f7d32', '144', 'Morningside Heights', '/morningside-heights/', ('0ef25cf528b09d8aa8b1ae6d99931352bb9e57ce731781013a89acf46d4d5ca5', '58e0a15ecf54e60ce9eac00ed10ce8b2aee3bb44f995be9c5384baecd17e8e3d')),
    'shell.shell-012700e3-031': ('45fd91412585580dd3804a4c81f1307493955d7a3dfa230f3ae00b6474964c13', '121', 'Oakridge', '/oakridge/', ('26a8ad941d0bb8659bb1c167a43f5b5479aac2bc70527386dcdcaed2d7c28613', 'd34c820c00837048a75dd4acd966592b819e970cdb46e866b36e85b311029569')),
    'shell.shell-012700e3-033': ('157d05dd89d21ca1d2b3345871c827a8faa663de0c30747f529c2dd9f19763c3', '116', 'Steeles', '/steeles/', ('76d3adbd8e5342c255de9ff2cfd5d4342219c21e80b06b1e927cb81628e67ccc', 'f0f9b695c07f66b8c5982194255ff77763d3415ea1215a61114c5b5a326a9eaf')),
    'shell.shell-012700e3-034': ('23357847a573e10d9354d153277ac7e842a46040833483e33c5f4df65c19d0ce', '118', "Tam O'Shanter-Sullivan", '/tam-o-shanter-sullivan/', ('3f49248f77785b666c1a7ba60fc4e61ecc2102dec9613dc17c2d5d04b25d123a', '74a2a835f610f3a2306f5737146769f6ddd9c1edd37940564864508847684446')),
    'shell.shell-012700e3-035': ('c5ff38a2c0d64619e2d73f50a4f16b1ecf7458fed64ebc1dfee44eef127f5f06', '136', 'West Hill', '/west-hill/', ('1ba72890e92d8ca4ffb47d0dfafc2b3709e81d224fc1080b1267c8a98d472d2e', '8e841960358684fb4c5972794ae38304a73bedf35412e0aff9932b672fddc8c3')),
    'shell.shell-012700e3-036': ('9818c294f0785d11a6f760fb06b79b6fd52874ebfeb182305d67d281785c3c91', '143', 'West Rouge', '/west-rouge/', ('5c18cad95a15dc9853c0dce327e76fe986d7963f0fd4f808e0c0a385e194e344', '77d3b34dbf152ffe7f563d8262422b3d6a3d7aa087c2210cec91b617ed66c850')),
    'shell.shell-012700e3-037': ('c9e3d18bbb76ea308c7ecc536c939ff96f3272bee31d75be1192d81198748fa1', '119', 'Wexford/Maryvale', '/wexford-maryvale/', ('058d864a1be90bccadf750f5d68a6ee0db48e1195fa65e13ce127a19382870ce', '0e94a6656ec7a322c1a374814ec75f0a164fbceabfc1dca667013b7ab6dabb69')),
    'shell.shell-012700e3-038': ('6dd946e801d44da8e68e264975f4962bdc85db73a80bacc1321e2e0d862a645c', '142', 'Woburn North', '/woburn-north/', ('792afe134c687dfec15fa939633bfce704416a991930ae2c66ef5613dfb00770', '99e3dbc3d6ab11de56aebd62b85cebb6ad9df27c57613478dcc07993bffba3a2')),
}


HOME_BOUNDARY = {
    'shell.shell-b04b38d4-018': ('536e2a2d2400b4343cef677165d167a9d38e703cafd9c9f2614bf443f3835679', 'span', '<span class="area-controls-label">', 'Boundaries', 2497, 2507),
    'shell.shell-b04b38d4-019': ('0da085162e0564da083e207a1afd69e38e6f07e2652e32ee3702895379801fbb', 'button', '<button type="button" class="area-toggle selected" data-area-overlay="off" aria-pressed="true">', 'Off', 2663, 2666),
    'shell.shell-b04b38d4-020': ('4356b4d950813066d988c282726dd7ec003fb56569d40c61bd05974a1bdcf049', 'button', '<button type="button" class="area-toggle" data-area-overlay="neighbourhood" aria-pressed="false">', 'Neighbourhoods', 2785, 2799),
    'shell.shell-b04b38d4-021': ('0867f567e041a9cacc64c9a26f9fb5a485eeb00ce796c2f42b5cf1a102a9fa1f', 'button', '<button type="button" class="area-toggle" data-area-overlay="ward" aria-pressed="false">', 'City wards', 2909, 2919),
    'shell.shell-b04b38d4-022': ('ae9b7f25b84671d2d213be6abb8ef33a8e5a97fb581b2155c958afd5445de17b', 'label', '<label for="area-choice">', 'Choose an area', 3040, 3054),
    'shell.shell-b04b38d4-023': ('1e04d7c99d2322dfafc0eb8ca08ef53f2f11e03df640ee0a11a65308b9cf2554', 'option', '<option value="">', 'Choose an area', 3104, 3118),
}


HOME_SOURCE = 'docs/index.html'
HOME_PINS = {'93283867eba047a32a2866994fb2f496e16aaf5eabc8772407a8823a923eb753',
             '2ec549f9cb4a193c5bae436545533ab093a4ade4e95526648fc825aaf0391db9'}


def _home_boundary_binding(packet):
    identity = packet['id']
    digest, tag, opening, label, start, end = HOME_BOUNDARY[identity]
    v.need(v.digest(packet) == digest and packet['kind'] == 'functional'
           and packet['locks'] == {} and packet['draft'] == label, 'Changed fixed boundary packet')
    raw = (ROOT / HOME_SOURCE).read_bytes()
    v.need(hashlib.sha256(raw).hexdigest() in HOME_PINS, 'Fixed boundary source changed')
    source = raw.decode('utf8').replace('\r\n', '\n')
    v.need(source[start - len(opening):end + len(tag) + 3] == opening + label + '</' + tag + '>',
           'Fixed boundary consumer changed')
    v.need(source.index('id="area-choice"') < HOME_BOUNDARY['shell.shell-b04b38d4-023'][4]
           < source.index('</select>', source.index('id="area-choice"')),
           'Wrong area choice placeholder consumer')
    return {'id': identity, 'packet_sha256': digest, 'text': label, 'locks': {},
            'consumer': opening, 'source_range': [start, end],
            'files': {HOME_SOURCE: sorted(HOME_PINS)}}


HOME_SELECTORS = {
    'shell.shell-b04b38d4-025': ('9899d61296142cd92e3b3421bf09bbc182e003b3ca13caea1b70b387e736e912', 'h2', '<h2 id="saved-areas-title">', 'Your saved areas', 3574, 3590, 'saved-areas-title', 'docs/saved-areas.mjs', ('33a703b709c3bea547cbd565aac77f663b04035f2c6036596e9a2e12cba6d6b7', '73825cb71f9e4260e1fbdce6ada30ddf88788c625baa20a539bc045cc00c368f')),
    'shell.shell-b04b38d4-027': ('72da1460e0566c2c7e61563282c696e635f43d0c21e6a14451438e71ad35341b', 'label', '<label for="saved-area-choice">', 'Choose a public area to save', 3723, 3751, 'saved-area-choice', 'docs/saved-areas.mjs', ('33a703b709c3bea547cbd565aac77f663b04035f2c6036596e9a2e12cba6d6b7', '73825cb71f9e4260e1fbdce6ada30ddf88788c625baa20a539bc045cc00c368f')),
    'shell.shell-b04b38d4-028': ('4ddbfac8358333d8b2eb615d068733e64fa872e99c54439b7f9e5055b553b5ae', 'option', '<option value="">', 'Choose an area', 3827, 3841, 'saved-area-choice', 'docs/saved-areas.mjs', ('33a703b709c3bea547cbd565aac77f663b04035f2c6036596e9a2e12cba6d6b7', '73825cb71f9e4260e1fbdce6ada30ddf88788c625baa20a539bc045cc00c368f')),
    'shell.shell-b04b38d4-029': ('1a2470bb55dadab15327d2d46b2653ce781c1bc242e7bba644cb86e5c24e0e8f', 'button', '<button id="save-public-area" type="button" disabled>', 'Save area', 3923, 3932, 'save-public-area', 'docs/saved-areas.mjs', ('33a703b709c3bea547cbd565aac77f663b04035f2c6036596e9a2e12cba6d6b7', '73825cb71f9e4260e1fbdce6ada30ddf88788c625baa20a539bc045cc00c368f')),
    'shell.shell-b04b38d4-041': ('092e64244345b959b9cb569ffc0f0633d1dbce64010cc4034d33e300b92a4a6a', 'label', '<label for="neighbourhood">', 'Neighbourhood', 5519, 5532, 'neighbourhood', 'docs/app.mjs', ('00dd1b611bb2ff8e1ff47fd14c76ff53ad8c590426e5359e05bef43ce0368f8a', 'f5d46d07bd8a2c670831fa4b60c87930f4af76ee02c8dfc90b002dc8dc007b9d')),
    'shell.shell-b04b38d4-043': ('bc9bab7c73e93dfaa3185be75087a5ec57b49f6149933b13fd5f5753e6f0beff', 'label', '<label for="window">', 'Time period', 5659, 5670, 'window', 'docs/app.mjs', ('00dd1b611bb2ff8e1ff47fd14c76ff53ad8c590426e5359e05bef43ce0368f8a', 'f5d46d07bd8a2c670831fa4b60c87930f4af76ee02c8dfc90b002dc8dc007b9d')),
    'shell.shell-b04b38d4-047': ('c2329b01c057380dd1dd29272357bbdbc633802bf3a7cf9b39f5ac575d9155c5', 'option', '<option value="all">', 'Any date', 5871, 5879, 'window', 'docs/app.mjs', ('00dd1b611bb2ff8e1ff47fd14c76ff53ad8c590426e5359e05bef43ce0368f8a', 'f5d46d07bd8a2c670831fa4b60c87930f4af76ee02c8dfc90b002dc8dc007b9d')),
}


def _home_selector_binding(packet):
    identity = packet['id']
    digest, tag, opening, label, start, end, element, producer, pins = HOME_SELECTORS[identity]
    v.need(v.digest(packet) == digest and packet['kind'] == 'functional'
           and packet['locks'] == {} and packet['draft'] == label, 'Changed fixed selector packet')
    raw = (ROOT / HOME_SOURCE).read_bytes()
    v.need(hashlib.sha256(raw).hexdigest() in HOME_PINS, 'Fixed selector source changed')
    source = raw.decode('utf8').replace('\r\n', '\n')
    v.need(source[start-len(opening):end+len(tag)+3] == opening+label+'</'+tag+'>'
           and source.count('id="'+element+'"') == 1, 'Fixed selector consumer changed')
    if tag == 'option':
        at = source.index('id="'+element+'"')
        v.need(at < start < source.index('</select>',at), 'Wrong fixed selector option consumer')
    v.need(hashlib.sha256((ROOT / producer).read_bytes()).hexdigest() in pins,
           'Fixed selector behavior changed')
    return {'id':identity,'packet_sha256':digest,'text':label,'locks':{},'consumer':opening,
            'source_range':[start,end],'control_id':element,'scope':'static HTML only',
            'files':{HOME_SOURCE:sorted(HOME_PINS),producer:list(pins)}}


HOME_STATIC_TABLE = {
    'shell.shell-b04b38d4-003': ('d3dd53ec5d8832973f2fac00b7f597459f4b961d4d217ea7ea3088f2d22312c0', 'a', '<a class="skip-link" href="#results">', None, 'Skip to results', 869, 884, 'body', None),
    'shell.shell-b04b38d4-031': ('485c0dc1642b9af5cc4b7b66e2452b2029480f55147002546af60879e050dfae', 'a', '<a href="/neighbourhoods/">', None, 'neighbourhood directory', 4143, 4166, 'noscript', None),
    'shell.shell-b04b38d4-032': ('f5f4f99f8c8e81b7f141333c60f28f1ee42e2a2713e8823919159de39cc6fc4e', 'div', '<div class="view-tabs" role="group" aria-label="Browse mode">', 'aria-label', 'Browse mode', 4306, 4317, 'div', 'filter-options'),
    'shell.shell-b04b38d4-033': ('c9d4e38928bb4e0fc44b8d4d4872e702860d68269031f315f01cdd604411d9bf', 'button', '<button class="tab active" data-mode="recent" type="button" aria-pressed="true">', None, 'Browse updates', 4410, 4424, 'div', None),
    'shell.shell-b04b38d4-034': ('1ca6b2e343ebf33f43d007825e51a791b516d2b57fd2bc5c422c4b0230b2f72e', 'button', '<button class="tab" data-mode="all" type="button" aria-pressed="false">', None, 'All places', 4515, 4525, 'div', None),
    'shell.shell-b04b38d4-050': ('21773475ec46114a50a34d125ad4c7094f0011f423d0d282209b33d1a2c3b4c4', 'button', '<button class="chip selected" data-status="all" aria-pressed="true" type="button">', None, 'All', 6181, 6184, 'div', None),
    'shell.shell-b04b38d4-062': ('139899b7c6708058991702f60fc8196fef6ad8a017d5f866cdcf826ce532c241', 'div', '<div class="map-legend" id="map-legend" role="group" aria-label="Map key">', 'aria-label', 'Map key', 7980, 7987, 'div', None),
    'shell.shell-b04b38d4-076': ('dcbb24fe5b9ef4b597bdc19134ca36d8124bae5a42d4e3b9ac6110f76a66934c', 'summary', '<summary>', None, 'About these records', 9675, 9694, 'details', 'source-provenance'),
    'shell.shell-b04b38d4-094': ('deb71257f5be759a32ddadef581185b6efcbd8d4774a5a6fc161e63e8c8222c1', 'a', '<a href="https://github.com/justinpfisher/ScarbTO/actions" target="_blank" rel="noopener noreferrer">', None, 'Update history', 11923, 11937, 'div', None),
    'shell.shell-b04b38d4-100': ('a701a857d508ffeb4726b5b6c384811f4621f6a391d84473f5b477baff84e210', 'a', '<a href="/community/">', None, 'create a community publication', 12115, 12145, 'div', None),
}
HOME_STATIC_TABLE_PINS = {'docs/index.html': ('2ec549f9cb4a193c5bae436545533ab093a4ade4e95526648fc825aaf0391db9', '93283867eba047a32a2866994fb2f496e16aaf5eabc8772407a8823a923eb753'), 'docs/app.mjs': ('00dd1b611bb2ff8e1ff47fd14c76ff53ad8c590426e5359e05bef43ce0368f8a', 'f5d46d07bd8a2c670831fa4b60c87930f4af76ee02c8dfc90b002dc8dc007b9d'), 'config/scarb-static-shells.json': ('10529fd88e53b47fb2eb1f831e6e239f2052c75036400f289de3e31b14a8e4c0', '638245570ac56062ffb412203db9f4abb43100d4891772806d7557261521e9bb'), 'docs/area-selection.mjs': ('7f6ac42ebe9c174d28f02d97244267b2baa9efd6f538bd98cecb4d57bcc18313', 'b1616d798b2d9867e9e37cd880a5d2cbd3e12398312afa4b5ca86bdadebc9e33'), 'docs/logic.mjs': ('4987676f9449ffb8cae83f86f782270b2e81154165f1d0c28f5fc0857a6da10c', 'fb5a1f8c91db61fcd4b43beedc08c76f3d9e9c94f3fc45a06620b0f50f2c904f')}


def _home_static_binding(packet):
    from scripts.scarb_static_materialize import discover
    identity = packet['id']
    digest, tag, opening, attribute, label, start, end, parent, parent_id = HOME_STATIC_TABLE[identity]
    v.need(v.digest(packet) == digest and packet['kind'] == 'functional'
           and packet['locks'] == {} and packet['draft'] == label, 'Changed fixed static packet')
    sources = {p:(ROOT / p).read_bytes() for p in HOME_STATIC_TABLE_PINS}
    v.need(all(hashlib.sha256(raw).hexdigest() in HOME_STATIC_TABLE_PINS[p] for p,raw in sources.items()),
           'Fixed static source or controller changed')
    source = sources[HOME_SOURCE].decode().replace('\r\n','\n')
    shell = json.loads(sources['config/scarb-static-shells.json'])[HOME_SOURCE]
    slot = {'start':start,'end':end,'draft':label,'attribute':bool(attribute)}
    v.need(slot in discover(shell['source']) and
           {**slot,'id':identity} in shell['slots'] and shell['source'] == source,
           'Fixed static slot inventory changed')
    if attribute:
        a = opening.index(attribute+'="')+len(attribute)+2
        v.need(opening[a:a+len(label)] == label and source[start-a:start-a+len(opening)] == opening,
               'Fixed static accessible name changed')
    else:
        v.need(source[start-len(opening):end+len(tag)+3] == opening+label+'</'+tag+'>',
               'Fixed static text consumer changed')
    return {'id':identity,'packet_sha256':digest,'text':label,'locks':{},'consumer':opening,
            'source_range':[start,end],'attribute':attribute,'parent':{'tag':parent,'id':parent_id},
            'scope':'static HTML only','files':{p:list(pins) for p,pins in HOME_STATIC_TABLE_PINS.items()}}


def _directory_binding(packet):
    import html
    import re
    identity = packet.get('id')
    v.need(identity in DIRECTORY_WORDING, 'Unknown fixed directory item')
    digest, code, name, route, destination_pins = DIRECTORY_WORDING[identity]
    v.need(v.digest(packet) == digest and packet['kind'] == 'functional'
           and packet['locks'] == {} and packet['draft'] == name, 'Changed fixed directory packet')
    matches = [row['AREA_NAME'] for row in json.loads(_source(SOURCE))['registry']
               if row['AREA_SHORT_CODE'] == code]
    v.need(matches == [name], 'Registry name differs')
    anchors = re.findall(r'<a href="'+re.escape(route)+r'">([^<>]+)</a>', _source(DIRECTORY).decode())
    v.need([html.unescape(value) for value in anchors] == [name], 'Fixed wording consumer differs')
    dest = 'docs' + route + 'index.html'
    v.need(hashlib.sha256((ROOT / dest).read_bytes()).hexdigest() in destination_pins,
           'Fixed wording destination changed')
    return {'id': identity, 'packet_sha256': digest, 'text': name, 'locks': {},
            'official_registry_code': code, 'route': route,
            'files': {SOURCE: sorted(PINS[SOURCE]), DIRECTORY: sorted(PINS[DIRECTORY]),
                      dest: sorted(destination_pins)}}


def _source(path):
    raw = (ROOT / path).read_bytes()
    v.need(hashlib.sha256(raw).hexdigest() in PINS[path], 'Fixed wording source changed')
    return raw


def exact_binding(packet):
    if packet.get('id') in HOME_STATIC_TABLE:
        return _home_static_binding(packet)
    if packet.get('id') in HOME_SELECTORS:
        return _home_selector_binding(packet)
    if packet.get('id') in HOME_BOUNDARY:
        return _home_boundary_binding(packet)
    if packet.get('id') != ITEM:
        return _directory_binding(packet)
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
    v.need(isinstance(excluded_ids, frozenset) and packet.get('id') not in excluded_ids,
           'Fixed item excluded by existing history')
    v.need(independent_sha256 and v.digest(record) == independent_sha256,
           'Exact independent fixed wording record required')
    v.need(record == {'version': 'scarb-fixed-wording-review-1', 'decision': 'verified-unchanged',
                      'binding': exact_binding(packet)}, 'Fixed wording evidence differs')
    return {'text': record['binding']['text'], 'packet_sha256': record['binding']['packet_sha256'],
            'receipt_sha256': independent_sha256, 'origin': 'scarb-fixed-wording-review-1'}


def require_complete_partition(canonical, editorial, fixed):
    """Sets of exact catalogue IDs from already-verified, independent evidence lanes."""
    v.need(len(canonical) == 736 and not (editorial & fixed)
           and (editorial | fixed) == canonical, 'Complete disjoint 736-item catalogue required')



def verify_from_private_state(state, packet, record, independent_sha256):
    """Offline bridge only. Reuse the existing private history gate; never accept a caller's exclusion list."""
    from scripts import scarb_packet_consumption_candidate as history
    identity = packet.get('id')
    family = HOME_SELECTORS if identity in HOME_SELECTORS else (HOME_BOUNDARY if identity in HOME_BOUNDARY else DIRECTORY_WORDING)
    if identity in HOME_STATIC_TABLE:
        family = HOME_STATIC_TABLE
    v.need(identity in family and v.digest(packet) == family[identity][0],
           'Unknown or changed fixed packet')
    history.assert_unconsumed(state, {identity: v.digest(packet)}, expected_root=history.protected_root())
    # The native gate verifies the index and each immutable claim under this lock.
    # An older digest for the same business ID is not a new fixed-wording candidate.
    folder = Path(state) / 'grouped-consumption'
    for claim in folder.glob('*.json'):
        v.need(identity not in json.loads(claim.read_bytes())['bindings'],
               'A prior attempt consumed this fixed wording ID')
    return verify_fixed_evidence(packet, record, independent_sha256, excluded_ids=frozenset())



# Only an independently reviewed repository change can populate this allowlist.
# No real receipt has been admitted. The disabled bridge cannot mint authority.
from types import MappingProxyType
TRUSTED_FIXED_REVIEWS = MappingProxyType({
    (ITEM, PACKET): '0240258254e033e162abe95163d44178cf4b02bda2d7bc502062e78e1763fafe',
    ('shell.shell-012700e3-010', 'f9cf5563118746c830c9380b2d715492fe0420781718fc0ab2e9270824bdb839'): '4d657a6e5e15397a5f839a41fcc1243f282e2d381004ab7b6d06b5c001d54f35',
    ('shell.shell-012700e3-011', '1304a9f6c17a84b1df6e1e761f93b18d773dc4d1055576e1284fa2e405a05233'): '434c548a025399db3f2d4e451d18cdfd9a5e5086923513bd8b7b976206260f84',
    ('shell.shell-012700e3-012', 'e349c825d3652f449c541e3e1996fb635119dbac89861424177469f566c5e404'): '74dc599a3fac58c9cfa18cdbed087587027895673cadf51472db50baafa8c961',
    ('shell.shell-012700e3-013', '86495560406bdfb54d39b0efea71859c490c88e6f25b82e728eea4eb8f99bdce'): 'bb27df3a905683f2d4208948e046e6ffcc4537d504387af9a84e555b84c10756',
    ('shell.shell-012700e3-015', 'b2855b957722d91d3965b3b7c9f889f6128c3bb46592ead4b1c71fbf80dd4e3d'): '7d597efc5ddef5cf7de789faf57501462db5089d7579891cea7f274d8e0f8781',
    ('shell.shell-012700e3-016', '802f46512620c6eaeb882a8a3c1d583d9d56e6acb6793528ed3954fff7a5fdf6'): '27c9e87152fe08cb8fd24c3a170dedb020963b3ce0fe4852d5d773d34ad383ac',
    ('shell.shell-012700e3-017', '16f960bf764f69657d8943697ac128ccdce9a5ab5633ea5a0c5aaaf7b4e93b15'): 'c3ec595527e9f8bee020db688dd35faeea2cad9faedd6168821e8872b341042e',
    ('shell.shell-012700e3-018', 'be2ee395309d4ca9a326d71528bd155ab22f45d1490731bbeee3608df13173f1'): 'c94a5486be5d097702d82df14261e62e2fefa8e72b7313125d6c886845aae479',
    ('shell.shell-012700e3-019', '5901a6a016b52cbb8ef7c71ca6faeb4f3c89cfc13ac734d53d988057dd2011e6'): '0822c74e0821d95bde558e037e56e3291ee2f76f60846a32e530720901ba5934',
    ('shell.shell-012700e3-020', '309ffae7d70cfc73acbec68b8f446c4aa04ccf5c0822df96a3c0a9d61b86dee9'): 'a1060b3068d69827b39835ee0f72184084d6bd80f1554db0dc1efa885dd4a79d',
    ('shell.shell-012700e3-021', 'a7beafb61d4a736376726608fca5ab9a97fa0ee1ff23eba2b312ee3cccbf2f30'): 'e3f1599212cbb8f3a0448f090d8c7a71b4665b84869a40728375794bd1f79a14',
    ('shell.shell-012700e3-022', '52665f01a030dd185a4a3027a4f9da8fc729840fa50629a73eccf57bff51c6a2'): '5bb222382f50a6edc14a8d452ff28d007c5c15d2f0c3142fd0eab18a281af8e6',
    ('shell.shell-012700e3-023', 'c6a601b8b220aa5652bd3f74c61d3a6f15a52758109fc41d5f8e2c575f62e895'): '9295f2925cdcef54435ff6ae06d54dd34f0432311d755d8cc40e76f31e635fd8',
    ('shell.shell-012700e3-024', '7878dd9b86a64f6468bdc7e32e66056486e8da4053fa4174567d0c62c0b1bddb'): '2f6bbd1efccee012aa115a8132a33d45c30dfc186a25fc3a87158c761515a59d',
    ('shell.shell-012700e3-025', '4c80f3750c4b41337e684a9b49ff5fe54e939aec89d75276c45970f049b040cf'): 'd91c82ae9d96ce65811c2481f9743516b7262a4321079bfeec5ed3d6833b01f8',
    ('shell.shell-012700e3-026', '80f57f39cef6e560a20005d3d0c670c6ee32920d65010596de16ea2c68baa2b0'): '2be8c61b98e3d3c7549fa7d270c2e5e10b49a1c38bd5de8366decb96a14c967e',
    ('shell.shell-012700e3-027', '44d204ec3fa18e416ca5034c0e704ec66cbb2ab7a30f8929e981dccc7eb33308'): '348c55faa7420bef6dbd48a7e91bbd7ffb59ee3a08bbf56bb891141947b90b69',
    ('shell.shell-012700e3-028', '146bab4205e5ce8cc5c77bb88c7394ec9316755a3b380f698fa76c7c43cba52d'): '75d2bf3662203f2cc749fda07573ea46925d9bc8d619ac232d4d65b2698a913f',
    ('shell.shell-012700e3-029', '9869156f1dab1044948b87bb1e7705020cf9987c5f1822e9f01174593ac1ca2a'): 'bb31c3cbb2b8a09f92475a98f08ff41eac9c61265f091ffeb66ae3c302237e3e',
    ('shell.shell-012700e3-030', 'cfda571b16727f352b183b68d61a6571ebf2291624e4aee1cf1608e01f9f7d32'): '5b6e2efe4a587e5961d7d1425214d65a3c4c8d2d2a772f3bccf4057acfa0e316',
    ('shell.shell-012700e3-031', '45fd91412585580dd3804a4c81f1307493955d7a3dfa230f3ae00b6474964c13'): '0a12cca2952f1ceb10ec9a73ba73d7c95f2410424341ad638df3c7d8895e1e07',
    ('shell.shell-012700e3-033', '157d05dd89d21ca1d2b3345871c827a8faa663de0c30747f529c2dd9f19763c3'): 'fb4ab8f6c32f90da34328d3f70d980fde5d4bd214cf58edcd44dd61daf396553',
    ('shell.shell-012700e3-034', '23357847a573e10d9354d153277ac7e842a46040833483e33c5f4df65c19d0ce'): 'e711a295c5c37dd8467c0c1615d29a159b6fd196bc33f2582afa0b49841bcf42',
    ('shell.shell-012700e3-035', 'c5ff38a2c0d64619e2d73f50a4f16b1ecf7458fed64ebc1dfee44eef127f5f06'): '490db1400e7edef91bc9c9205ed4dca412c68253c2b4848cb7e96187c6dcda78',
    ('shell.shell-012700e3-036', '9818c294f0785d11a6f760fb06b79b6fd52874ebfeb182305d67d281785c3c91'): '6d2440208991cdcf36b70e946de15cc83313d474a26799e37242d71ce6644eab',
    ('shell.shell-012700e3-037', 'c9e3d18bbb76ea308c7ecc536c939ff96f3272bee31d75be1192d81198748fa1'): 'b772ee02c54d7804e859d7059c673cbea42d89f7c8c1222af51e0098b135f719',
    ('shell.shell-012700e3-038', '6dd946e801d44da8e68e264975f4962bdc85db73a80bacc1321e2e0d862a645c'): '885bea06b247101f1c5056a0b75b7b648d4dab34a6e8af3e5258dfe30f2efa60',
    ('shell.shell-b04b38d4-018', '536e2a2d2400b4343cef677165d167a9d38e703cafd9c9f2614bf443f3835679'): 'a75f752cc20fc9d6c8affc4d3a38e50e41842ff4bd134e2f62efeef4d0d9957c',
    ('shell.shell-b04b38d4-019', '0da085162e0564da083e207a1afd69e38e6f07e2652e32ee3702895379801fbb'): '7ec411990eabe813263cff15988e1fbe0a60c11fd762a59fced58a5cc171b419',
    ('shell.shell-b04b38d4-020', '4356b4d950813066d988c282726dd7ec003fb56569d40c61bd05974a1bdcf049'): '1c470a43ebb0d1e9f8155245b2ae56362269559d53144c8747cd0c6b4d8eb23e',
    ('shell.shell-b04b38d4-021', '0867f567e041a9cacc64c9a26f9fb5a485eeb00ce796c2f42b5cf1a102a9fa1f'): '7614c5dec6ef5d9b74b084d13cdf38fb9812fc457a28d986629f6b080f034c04',
    ('shell.shell-b04b38d4-022', 'ae9b7f25b84671d2d213be6abb8ef33a8e5a97fb581b2155c958afd5445de17b'): 'fa90f5508f1d03d3414e15e7a0f43b834e68499d2dc178605032b4b656106a2f',
    ('shell.shell-b04b38d4-023', '1e04d7c99d2322dfafc0eb8ca08ef53f2f11e03df640ee0a11a65308b9cf2554'): '4ba0dc5b76cdbe9906e99d961ee523fe170ba9fc8555db00c72d64332b189f02',
    ('shell.shell-b04b38d4-025', '9899d61296142cd92e3b3421bf09bbc182e003b3ca13caea1b70b387e736e912'): 'dea537b5e65becf8ec4ac1c48c7a88583e47833f7f478a9d8359d89d9b316b1e',
    ('shell.shell-b04b38d4-027', '72da1460e0566c2c7e61563282c696e635f43d0c21e6a14451438e71ad35341b'): 'b70db70e5c89b3c35760b0128fd0b3e0248326b9b2d5b920db6e549dc624af3b',
    ('shell.shell-b04b38d4-028', '4ddbfac8358333d8b2eb615d068733e64fa872e99c54439b7f9e5055b553b5ae'): '608c0cb24e124f10f8cd9aed092cbfdface6373020cff0cb601ddd97711f4c59',
    ('shell.shell-b04b38d4-029', '1a2470bb55dadab15327d2d46b2653ce781c1bc242e7bba644cb86e5c24e0e8f'): '51e0d233b2fb5412ccb03e46fb2a04321fc448690717ce18868746994880df5a',
    ('shell.shell-b04b38d4-041', '092e64244345b959b9cb569ffc0f0633d1dbce64010cc4034d33e300b92a4a6a'): 'd21b7e5ff157cd772345268b82af7cf160e2e077bdb126a0fac851fee27e0c59',
    ('shell.shell-b04b38d4-043', 'bc9bab7c73e93dfaa3185be75087a5ec57b49f6149933b13fd5f5753e6f0beff'): '49a53b5af6ccd861531ed4045fd880aeedb29b5c65118a22ef24dc25f944edd1',
    ('shell.shell-b04b38d4-047', 'c2329b01c057380dd1dd29272357bbdbc633802bf3a7cf9b39f5ac575d9155c5'): '4ac60ac67ca6c84bc74c4624d6a7b34a045fa21358434cda61f8d044bb8ace13',
    ('shell.shell-b04b38d4-003', 'd3dd53ec5d8832973f2fac00b7f597459f4b961d4d217ea7ea3088f2d22312c0'): '579b77d2023656ffcaf39bd24a6d77d1a0e4325ac12f5f4763ec05b3d10526c1',
    ('shell.shell-b04b38d4-031', '485c0dc1642b9af5cc4b7b66e2452b2029480f55147002546af60879e050dfae'): '25b7ac2116c47eae6f08b30046e04bc0de0201b7b1e7fcf80c0e165603a11477',
    ('shell.shell-b04b38d4-032', 'f5f4f99f8c8e81b7f141333c60f28f1ee42e2a2713e8823919159de39cc6fc4e'): 'b98d2a906bf1f4f84f5e16bf5b81e1286b35b3c7965fbf9c7297d30bdde5dcc4',
    ('shell.shell-b04b38d4-033', 'c9d4e38928bb4e0fc44b8d4d4872e702860d68269031f315f01cdd604411d9bf'): '73308676e32dcad994578a830388f4f8e72490481362add2b28089e25be50f2b',
    ('shell.shell-b04b38d4-034', '1ca6b2e343ebf33f43d007825e51a791b516d2b57fd2bc5c422c4b0230b2f72e'): '3353c67d6cfdf12fa93154c977fc17883478a1b5008d26e0fe3d23db94ab77a0',
    ('shell.shell-b04b38d4-050', '21773475ec46114a50a34d125ad4c7094f0011f423d0d282209b33d1a2c3b4c4'): '13881444b46a2399e3e8ee33c5f616f67fe3fb445a5c0e2ebc517b950a2dedc7',
    ('shell.shell-b04b38d4-062', '139899b7c6708058991702f60fc8196fef6ad8a017d5f866cdcf826ce532c241'): 'ced44f35774499f095a88754be0ebd0088e4bd1491bf2989f1da75aad1264c48',
    ('shell.shell-b04b38d4-076', 'dcbb24fe5b9ef4b597bdc19134ca36d8124bae5a42d4e3b9ac6110f76a66934c'): 'b0987fa9fe0f0be4894316249715e83218612f1a2f911f98b215520ae7b2a95e',
    ('shell.shell-b04b38d4-094', 'deb71257f5be759a32ddadef581185b6efcbd8d4774a5a6fc161e63e8c8222c1'): '3c754bbc423d7b71d636ef133ff67d9935bd9e43bd7818bc56411e97f609fb24',
    ('shell.shell-b04b38d4-100', 'a701a857d508ffeb4726b5b6c384811f4621f6a391d84473f5b477baff84e210'): '6d90b652dcd090bd408ad92407037e7b9330b4b024e85b1f2eecccb42938ac34',
})


def verify_reviewed_private_record(state, packet, record):
    """Disabled private readback; do not invoke from a production artifact writer."""
    pin = TRUSTED_FIXED_REVIEWS.get((packet.get('id'), v.digest(packet)))
    v.need(isinstance(pin, str) and len(pin) == 64, 'No admitted independent fixed wording review')
    return verify_from_private_state(state, packet, record, pin)
