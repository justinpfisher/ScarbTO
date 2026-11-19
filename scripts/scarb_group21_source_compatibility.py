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
def historical_context(pin,current,recorded):
 if current==recorded:return current
 if pin.get('manifest_sha256') in COMMUNITY15_PINS:return community15_context(pin,current,recorded)
 v.need(pin.get('manifest_sha256')==MANIFEST and pin.get('packet_bindings')==BINDINGS,'No exact source transition authority')
 v.need(set(current)==set(recorded)==set(BINDINGS),'Source transition membership differs')
 old=copy.deepcopy(current)
 for path,(before,after) in TRANSITIONS.items():
  raw=(ROOT/path).read_bytes()
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
 path='docs/scarb-voice.mjs';raw=(ROOT/path).read_bytes()
 v.need(hashlib.sha256(raw).hexdigest()==COMMUNITY15_AFTER and raw.count(COMMUNITY15_NEW)==1 and COMMUNITY15_OLD not in raw,'Community15 current bytes changed')
 restored=raw.replace(COMMUNITY15_NEW,COMMUNITY15_OLD)
 v.need(hashlib.sha256(restored).hexdigest()==COMMUNITY15_BEFORE and restored.count(COMMUNITY15_OLD)==1,'Community15 historical bytes changed')
 old=copy.deepcopy(current)
 for identity in bindings:
  v.need(current[identity].get('source_sha256',{}).get(path)==COMMUNITY15_AFTER and recorded[identity].get('source_sha256',{}).get(path)==COMMUNITY15_BEFORE,'Community15 exact digest transition differs')
  old[identity]['source_sha256'][path]=COMMUNITY15_BEFORE
 v.need(old==recorded,'Community15 unrelated context changed')
 return old
