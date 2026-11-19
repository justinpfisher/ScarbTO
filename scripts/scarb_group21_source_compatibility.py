"""One exact source-copy correction compatibility proof; not a generic hash exception."""
import copy,hashlib
from pathlib import Path
from scripts import scarb_ai_voice as v
ROOT=Path(__file__).resolve().parents[1]
MANIFEST='f4f40637d3584ceec0b9cdcdc479c232d591a47db7cc5342073df360ea9f5e50'
BINDINGS={'static.finding-explanation-fcf37504d73b4996':'e96dd32122b1b75068399ad21845f7a4710b3d45d304636783693e895fc62f1a','static.finding-explanation-ff5650b4f3e1d752':'7d6bb810c9dfc9ec2cd2ee57ed89ffea2ff195097dff3cbc4dfdc9898359c012'}
OLD=b'Reusable articles were not designed so they could be readily cleaned.'
NEW=b'Multi-service articles that were not readily cleanable were being used.'
TRANSITIONS={
 'docs/scarb-voice.mjs':('fb611778955e6a0bb4f7dfa710d60b06d8519e522e067baea7b94a862b3504e5','8708e788185e8dcc7f38803b5babee8196a34a9a6d18bcf19103493d31fe2afe'),
 'docs/inspection-translations.mjs':('adfed96feea0e0433e0c1c34182d8f0e47267ab7b519dfb65779feaeed23fae9','0e97e5184e8582670371606451bf3caa5e990be171af1de22a82a168edfbc335')}
def _historical_context(pin,current,recorded):
 if current==recorded:return current
 if pin.get('manifest_sha256') in COMMUNITY15_PINS:return community15_context(pin,current,recorded)
 v.need(pin.get('manifest_sha256')==MANIFEST and pin.get('packet_bindings')==BINDINGS,'No exact source transition authority')
 v.need(set(current)==set(recorded)==set(BINDINGS),'Source transition membership differs')
 old=copy.deepcopy(current)
 for path,(before,after) in TRANSITIONS.items():
  raw=_source_bytes(pin,path)
  v.need(hashlib.sha256(raw).hexdigest()==after and raw.count(NEW)==1 and OLD not in raw,'Current source transition bytes differ')
  restored=raw.replace(NEW,OLD)
  v.need(restored.count(OLD)==1 and hashlib.sha256(restored).hexdigest()==before,'Historical source reconstruction differs')
  for identity in BINDINGS:
   v.need(current[identity].get('source_sha256',{}).get(path)==after and recorded[identity].get('source_sha256',{}).get(path)==before,'Source transition hash bindings differ')
   old[identity]['source_sha256'][path]=before
 v.need(old==recorded,'Unrelated packet source context changed')
 return old

# Exact unrelated-copy transition, scoped to these nine historical finding manifests.
COMMUNITY15_PINS={'1bab99925ed6493e7fdd1d7000b50e0d581ff34f7b848d56093f8bed39238f08': {'static.finding-explanation-3be26fcb2bea0ad3': 'f8afdac54cbb04471a3011a3f93d0f0172bda68349939b21bfc0f1a52d330c02', 'static.finding-explanation-453b1dae8806a855': '66ab8bf620526c00aee3640f6bf9051aee8e88db0523b3dd26f593a03bfccab6', 'static.finding-explanation-4586d24a972736ff': 'fc3b0d27b98661804ec9eebe37f622b2869d14daf148676866c075ac8bb0719e'}, '2b4ed3a50bc7e0d0e64e09c06a80e7ffbe6f5e68caff9f7a20bde4d8e69bd781': {'static.finding-explanation-544b08c684a7ba77': '021c18516425ef72bf9b9e71b0a6c428e77694b25abb16418f462325a4319de9', 'static.finding-explanation-549749191cc32f62': 'bdedfe990dc8bb6ac41d3f1c57f38f4175ec6a9037445885d93c40abe614e3af', 'static.finding-explanation-664e0ed0696a1822': '2a9be7e351370dc71c6055035a3f65f551f8c1c7ff0a3eab9c5e8932564d4821'}, '2e055064514bf3998ad8a695193132515046e233749210fde668fee50f62b181': {'static.finding-explanation-d1a54a8320e2699e': '2c3933e11213e5fb8ec34d5ac629b8496e2d9d6235b6829bbc9a49807a40e163', 'static.finding-explanation-dc61761581abe33d': 'a6c443c22f7107d09668219473c18e8cd4ae326c96292015f18cd942785364cf', 'static.finding-explanation-e30d88d467d25736': '8ed63abce5923d35f483077cfa5a00d53228244f4a108d584773ff1283037a54'}, '42a673d8916f5605c1cc54497a7d5cb0dbbae057d2f6faf026c67d9d24569ce0': {'static.finding-explanation-4ff4bb2e488f0940': 'f1e9d53f2c8f38f6e9bf39ccd0cb9876b873d2b2d8aed2d7ff428cdeb9938b81', 'static.finding-explanation-54a68a5e7db206d7': '2f3f788c8c6148bd72a1554f94a454082ab50dfcbd8d519550c4f725a0720e5b', 'static.finding-explanation-55eb3a9acbeba3d6': '595d68681bc16bae650b3d1c4069e8d2a592e4f7e2c180ea79e0518defb4b608'}, '4934c49beb5058b7ec01fd572b5476c058602ffe78a1f40e7ff5248ecfae3126': {'static.finding-explanation-301b33152fa2ae4e': 'c403a6570d9ec024c5a64a8a5c5a9283a4e802229d3ef669d97f414fd49e9b25', 'static.finding-explanation-311c575d18c08f88': '6fb301ad69156859272f06babd707de80e124b9f68139f190390599ac04ddf1e', 'static.finding-explanation-3fa8b60a24dfb615': '95c6a7e7472db17b569a7dc5c4868ff0b4319b6429b8423aabf40bb9fa3a6a2b'}, '8d4cdb6bf7f281904da0478c496b997f95ad9c0326e64597e174e202d8b6cbc1': {'static.finding-explanation-0ac7faf6108da739': '424c1a6c06d0498169de48a5c1b65b9c70cfdffe733bb7e54b63c6d477bae2ed', 'static.finding-explanation-0bd1898c410b80ab': '45fa3a2099a4170404d06bf32efc52215e25817ba669ddca16571aef0f457260', 'static.finding-explanation-20363154ac4a238b': 'ab74251e792d4001bd8332b3930b8db25512514a16ade33cafa37f0140b939f2'}, 'b69edd70b981f9ba68f1024aca1b187ae37a87f2b4ceedb2cf8aa214d88579fa': {'static.finding-explanation-233b3a3934b6fc0d': '622808c59e231ec46a832183fba66a307ee0ceef0cb84f90cf6059df4c879c01', 'static.finding-explanation-2a5a4167ff430b78': '5a9b93d19452943cfb5878e584339ea552d6e68a4cda65c1da720327ab4dbd4c', 'static.finding-explanation-2f130e4ac268594b': 'b3067bcdb04e6d90cac96d3d56ba0d0a8b33d9fa0dd4244b7d625d06988faf50'}, 'd4679fcfd87c99745ec6818ad40c58ea8615575d002fed26a12bc6381030d0d4': {'static.finding-explanation-e6a840398ac06901': '1fc124c7ad1b8d7c1012874a8243aa4ab7885ec9aa0b990a83d19a501a1ac493', 'static.finding-explanation-e929a3db8cf382f3': '44764ba7aae56c27cb09db1349b22f25309b04f7c6591a311712331e27a2422b', 'static.finding-explanation-f1c3821f2efad5f0': '6d3d18df0a102dd43968af420dcd23527ac79d5653381918dbd84009905e765c'}, 'e56c6434eeb96b0d018bd7ca84377d2c49956ab6d267f6454b76500b1f454f54': {'static.finding-explanation-60f58672d67dea9b': 'a0d9d10f9846426984699445c82c22c695dfa582d6c9fe847e5c10cea303ea4c', 'static.finding-explanation-7507fe18e4efce30': 'a66e7243353672c0c209d0d0e6d237ac2895a7f272408a10bdcee659d926f851', 'static.finding-explanation-97881a45d10a023d': '55f14978629464eccdfcbbf62e54f4a333d882b279adb595e473063978abc3cd'}}
COMMUNITY15_BEFORE='83b88ec5cedd55f190ae2799558e83def6a465130bc06cbc71e90d1807c6227b'
COMMUNITY15_AFTER='fd0108592fc0ab941ccc978984bd143f9186cea305861cf5275215c1e80cc28b'
COMMUNITY15_OLD=b'Boundary polygons are missing.'
COMMUNITY15_NEW=b"Supply a non-empty list of boundary polygons within the publishing tool's polygon limit."
def community15_context(pin,current,recorded):
 bindings=COMMUNITY15_PINS.get(pin.get('manifest_sha256'))
 v.need(bindings is not None and pin.get('packet_bindings')==bindings,'Unlisted Community15 transition')
 v.need(set(current)==set(recorded)==set(bindings),'Community15 membership differs')
 from scripts.scarb_grouped_projection_seam import current_canonical_requests
 packets=current_canonical_requests()
 v.need(all(v.digest(packets[i])==h for i,h in bindings.items()),'Community15 canonical packet changed')
 path='docs/scarb-voice.mjs';raw=_source_bytes(pin,path)
 if hashlib.sha256(raw).hexdigest()==COMMUNITY333637_AFTER:
  for old,new in COMMUNITY333637_EDITS:
   v.need(raw.count(new)==1 and old not in raw,'Community333637 exact literal differs')
   raw=raw.replace(new,old)
  v.need(hashlib.sha256(raw).hexdigest()==COMMUNITY15_AFTER,'Community333637 old file reconstruction differs')
 v.need(hashlib.sha256(raw).hexdigest()==COMMUNITY15_AFTER and raw.count(COMMUNITY15_NEW)==1 and COMMUNITY15_OLD not in raw,'Community15 current bytes changed')
 restored=raw.replace(COMMUNITY15_NEW,COMMUNITY15_OLD)
 v.need(hashlib.sha256(restored).hexdigest()==COMMUNITY15_BEFORE and restored.count(COMMUNITY15_OLD)==1,'Community15 historical bytes changed')
 old=copy.deepcopy(current)
 for identity in bindings:
  v.need(current[identity].get('source_sha256',{}).get(path)==hashlib.sha256(_source_bytes(pin,path)).hexdigest() and recorded[identity].get('source_sha256',{}).get(path)==COMMUNITY15_BEFORE,'Community15 exact digest transition differs')
  old[identity]['source_sha256'][path]=COMMUNITY15_BEFORE
 v.need(old==recorded,'Community15 unrelated context changed')
 return old

COMMUNITY333637_AFTER='1f62b579084f8093a5d653da291b9f322dc74270c04913f2f72e76815924424d'
COMMUNITY333637_EDITS=[(b'Only a reviewed draft can be finalised.', b'Only a draft can be finalised.'), (b'This correction does not preserve its original edition.', b'This correction exceeds the revision limit or has an invalid original-edition link, revision sequence or explanation.'), (b'Create a draft and retain the original before making a correction.', b'A correction requires a draft, and the original edition must remain below the revision limit.')]

# Exact unrelated two-finding correction. Never grants eligibility to the held group.
FINDING22_PINS={'04eabc865f01c39746bf2de0c2abb955fe63a0052e0763db56ccda3cd55f5bb2': {'static.finding-explanation-aa1edc84017fdbca': 'd9de7915fdf213ccfab5990bfcd12d7de27cb0aac1db57c2092ffddd237ef061', 'static.finding-explanation-bc87fa104f07ca31': 'a3b709847755c74e08b1660b06e428cd8e96ec303dd4304269e6fafe352ed5f7', 'static.finding-explanation-c17bbbf70409c000': 'f7a68fcf9e6a6576b408432bd704939de76bedce2c94da4b1d10ecf7e84b8279'}, '1bab99925ed6493e7fdd1d7000b50e0d581ff34f7b848d56093f8bed39238f08': {'static.finding-explanation-3be26fcb2bea0ad3': 'f8afdac54cbb04471a3011a3f93d0f0172bda68349939b21bfc0f1a52d330c02', 'static.finding-explanation-453b1dae8806a855': '66ab8bf620526c00aee3640f6bf9051aee8e88db0523b3dd26f593a03bfccab6', 'static.finding-explanation-4586d24a972736ff': 'fc3b0d27b98661804ec9eebe37f622b2869d14daf148676866c075ac8bb0719e'}, '2b4ed3a50bc7e0d0e64e09c06a80e7ffbe6f5e68caff9f7a20bde4d8e69bd781': {'static.finding-explanation-544b08c684a7ba77': '021c18516425ef72bf9b9e71b0a6c428e77694b25abb16418f462325a4319de9', 'static.finding-explanation-549749191cc32f62': 'bdedfe990dc8bb6ac41d3f1c57f38f4175ec6a9037445885d93c40abe614e3af', 'static.finding-explanation-664e0ed0696a1822': '2a9be7e351370dc71c6055035a3f65f551f8c1c7ff0a3eab9c5e8932564d4821'}, '2e055064514bf3998ad8a695193132515046e233749210fde668fee50f62b181': {'static.finding-explanation-d1a54a8320e2699e': '2c3933e11213e5fb8ec34d5ac629b8496e2d9d6235b6829bbc9a49807a40e163', 'static.finding-explanation-dc61761581abe33d': 'a6c443c22f7107d09668219473c18e8cd4ae326c96292015f18cd942785364cf', 'static.finding-explanation-e30d88d467d25736': '8ed63abce5923d35f483077cfa5a00d53228244f4a108d584773ff1283037a54'}, '42a673d8916f5605c1cc54497a7d5cb0dbbae057d2f6faf026c67d9d24569ce0': {'static.finding-explanation-4ff4bb2e488f0940': 'f1e9d53f2c8f38f6e9bf39ccd0cb9876b873d2b2d8aed2d7ff428cdeb9938b81', 'static.finding-explanation-54a68a5e7db206d7': '2f3f788c8c6148bd72a1554f94a454082ab50dfcbd8d519550c4f725a0720e5b', 'static.finding-explanation-55eb3a9acbeba3d6': '595d68681bc16bae650b3d1c4069e8d2a592e4f7e2c180ea79e0518defb4b608'}, '43815c05be14a6e42085be0b11ff75b948d72b61c445a4ffe5c8fff4f4ec7ffd': {'static.finding-explanation-c4fbfa3a08039d7c': '6f864c06d7187f297767386047b60d5cb59bd568584f786666ec83d2b923ae63', 'static.finding-explanation-c81e84fecdde1720': 'ba22214b42e11b6207b70c8ea9de9b71c48b18e7b267e9b2cc4270075c6bab4a', 'static.finding-explanation-c99c97cd13926bfb': 'bb08a18a7a5b42c5c849bc0369bacb1e5f53222c9d38ce1796620074b72fdb09'}, '4934c49beb5058b7ec01fd572b5476c058602ffe78a1f40e7ff5248ecfae3126': {'static.finding-explanation-301b33152fa2ae4e': 'c403a6570d9ec024c5a64a8a5c5a9283a4e802229d3ef669d97f414fd49e9b25', 'static.finding-explanation-311c575d18c08f88': '6fb301ad69156859272f06babd707de80e124b9f68139f190390599ac04ddf1e', 'static.finding-explanation-3fa8b60a24dfb615': '95c6a7e7472db17b569a7dc5c4868ff0b4319b6429b8423aabf40bb9fa3a6a2b'}, '8d4cdb6bf7f281904da0478c496b997f95ad9c0326e64597e174e202d8b6cbc1': {'static.finding-explanation-0ac7faf6108da739': '424c1a6c06d0498169de48a5c1b65b9c70cfdffe733bb7e54b63c6d477bae2ed', 'static.finding-explanation-0bd1898c410b80ab': '45fa3a2099a4170404d06bf32efc52215e25817ba669ddca16571aef0f457260', 'static.finding-explanation-20363154ac4a238b': 'ab74251e792d4001bd8332b3930b8db25512514a16ade33cafa37f0140b939f2'}, '9e41f5878125adb2c7039d5e327d1f767f4f163e1720d3810f0af12258db7633': {'static.finding-explanation-9f0584588789d2f6': '078086375880557a4e7f5bd9bb62238bfe3246a09fa18160e5dc10663f958640', 'static.finding-explanation-f882cb7b45e3af65': 'f72f24982591a3310cca47035100441e032bd9f35eed6d8e4cc985d6854eb83b'}, 'b69edd70b981f9ba68f1024aca1b187ae37a87f2b4ceedb2cf8aa214d88579fa': {'static.finding-explanation-233b3a3934b6fc0d': '622808c59e231ec46a832183fba66a307ee0ceef0cb84f90cf6059df4c879c01', 'static.finding-explanation-2a5a4167ff430b78': '5a9b93d19452943cfb5878e584339ea552d6e68a4cda65c1da720327ab4dbd4c', 'static.finding-explanation-2f130e4ac268594b': 'b3067bcdb04e6d90cac96d3d56ba0d0a8b33d9fa0dd4244b7d625d06988faf50'}, 'd4679fcfd87c99745ec6818ad40c58ea8615575d002fed26a12bc6381030d0d4': {'static.finding-explanation-e6a840398ac06901': '1fc124c7ad1b8d7c1012874a8243aa4ab7885ec9aa0b990a83d19a501a1ac493', 'static.finding-explanation-e929a3db8cf382f3': '44764ba7aae56c27cb09db1349b22f25309b04f7c6591a311712331e27a2422b', 'static.finding-explanation-f1c3821f2efad5f0': '6d3d18df0a102dd43968af420dcd23527ac79d5653381918dbd84009905e765c'}, 'e56c6434eeb96b0d018bd7ca84377d2c49956ab6d267f6454b76500b1f454f54': {'static.finding-explanation-60f58672d67dea9b': 'a0d9d10f9846426984699445c82c22c695dfa582d6c9fe847e5c10cea303ea4c', 'static.finding-explanation-7507fe18e4efce30': 'a66e7243353672c0c209d0d0e6d237ac2895a7f272408a10bdcee659d926f851', 'static.finding-explanation-97881a45d10a023d': '55f14978629464eccdfcbbf62e54f4a333d882b279adb595e473063978abc3cd'}, 'e8337593a178e3d15d8d9f3ec04ba3f603d16f9eb1c77b37bb9774dc8b6230c1': {'static.finding-explanation-7155e6e6c00df05f': '342e5170148d10c053199fe229ddada15de94fa4d423cba955218311cd52d21f', 'static.finding-explanation-81cb5ba276533b89': '374810b619c7bc6f96d9d79dab4b5460593e5b478b8291c49f19e222438b392f', 'static.finding-explanation-88eeb889ed6c8232': '43ab4db20d213e6c71f2cb9b9d04309b8ee6e0cb932aad6f9a80da2ac3f73884'}, 'fe2eb333e9d6a9c78484e56fffcb60914963d625cafe7778b795590b8737fa55': {'static.finding-explanation-e9be03fc092ac361': '610d22b15d3c980e9af1d7099f7186b5ea9a44e21820801937cec4141cc9ec75', 'static.finding-explanation-f9ae482f2342e759': 'd50ac82e4a98fb6e44545e5c45f30fc19e604dd1e66113a7afaa26d17cef9052', 'static.finding-explanation-f9eb75190a51c30d': '0b79a1cef26ec91432bb0bba3add2806f35b448b7f7751cc225da8bd76313aae'}}
FINDING22_TRANSITIONS={'docs/inspection-translations.mjs': ('9d61f617e2cfbe12bc286cd9e8d34be9fe682ef1394b8b10200417b8bd4b5719', '97730aba61ff9be8c6166327bd5107df7085720afaef6fe00ceeb130d58a0631'), 'docs/scarb-voice.mjs': ('1f62b579084f8093a5d653da291b9f322dc74270c04913f2f72e76815924424d', 'd8b587486c93ed0d1e910b9e66f0e120948b268cf0e4f6056559bb934ab5fdbb')}
FINDING22_EDITS=[(b'A food handler was not following good personal hygiene practices.',b'The inspection found a failure to ensure that food handlers practised good personal hygiene.'),(b'A food handler was not taking the required precautions to keep hair from contaminating food.',b'The inspection found a failure to ensure that food handlers protected against contamination by hair.')]

def _finding22_sources(pin):
 bindings=FINDING22_PINS.get(pin.get('manifest_sha256'))
 v.need(bindings is not None and pin.get('packet_bindings')==bindings,'Unlisted finding22 transition')
 restored={}
 for path,(before,after) in FINDING22_TRANSITIONS.items():
  raw=(ROOT/path).read_bytes()
  v.need(hashlib.sha256(raw).hexdigest()==after,'Finding22 current source differs')
  for old,new in FINDING22_EDITS:
   v.need(raw.count(new)==1 and old not in raw,'Finding22 exact literal differs')
   raw=raw.replace(new,old)
  v.need(hashlib.sha256(raw).hexdigest()==before,'Finding22 historical source differs')
  restored[path]=raw
 return restored

def _source_bytes(pin,path):
 raw=(ROOT/path).read_bytes()
 if path in FINDING22_TRANSITIONS and hashlib.sha256(raw).hexdigest()==FINDING22_TRANSITIONS[path][1]:
  return _finding22_sources(pin)[path]
 return raw

def historical_context(pin,current,recorded):
 if current==recorded:return current
 path='docs/scarb-voice.mjs'
 if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=FINDING22_TRANSITIONS[path][1]:
  return _historical_context(pin,current,recorded)
 bindings=FINDING22_PINS.get(pin.get('manifest_sha256'))
 _finding22_sources(pin)
 v.need(set(current)==set(recorded)==set(bindings),'Finding22 membership differs')
 from scripts.scarb_grouped_projection_seam import current_canonical_requests
 packets=current_canonical_requests()
 v.need(all(v.digest(packets[i])==h for i,h in bindings.items()),'Finding22 canonical packet changed')
 prior=copy.deepcopy(current)
 for item in prior.values():
  for path,(before,after) in FINDING22_TRANSITIONS.items():
   v.need(item.get('source_sha256',{}).get(path)==after,'Finding22 context digest differs')
   item['source_sha256'][path]=before
 # Existing exact older transitions remain responsible for their original scope.
 return _historical_context(pin,prior,recorded)
