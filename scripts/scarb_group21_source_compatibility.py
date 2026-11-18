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
