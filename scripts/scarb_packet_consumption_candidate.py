"""Shared candidate pre-dispatch check. Caller holds generation.lock."""
import json,os,re
from pathlib import Path
from scripts import scarb_ai_voice as v
HEX=re.compile(r'^[0-9a-f]{64}$');ID=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}$')
def bindings_check(bindings):
 v.need(isinstance(bindings,dict) and bool(bindings) and all(isinstance(k,str) and ID.fullmatch(k) and isinstance(h,str) and HEX.fullmatch(h) for k,h in bindings.items()) and len(set(bindings.values()))==len(bindings),'Invalid packet bindings')
def check_root(root,expected_root):
 root=Path(root);expected=Path(expected_root)
 v.need(root.is_dir() and not root.is_symlink() and root.resolve()==expected.resolve(),'Missing or wrong consumption state root')
 lock=root/'generation.lock';v.need(lock.is_file() and lock.read_text()==str(os.getpid()),'Shared generation lock required')
 return root

def grouped_claim_bindings(root):
 """Read every indexed, immutable grouped claim without acquiring a write lock."""
 import hashlib
 folder=root/'grouped-consumption'
 if folder.exists():
  v.need(folder.is_dir() and not folder.is_symlink(),'Invalid grouped consumption folder')
  index=root/'grouped-consumption-index.json';v.need(index.is_file(),'Missing grouped consumption index')
  record=json.loads(index.read_text(encoding='utf8'))
  v.need(set(record)=={'root','claims'} and record['root']==str(root.resolve()),'Wrong grouped consumption root')
  v.need(set(record['claims'])=={p.name for p in folder.iterdir()},'Grouped consumption inventory mismatch')
  for name,digest in record['claims'].items():
   path=folder/name;v.need(path.is_file() and not path.is_symlink() and HEX.fullmatch(digest),'Invalid claim path/hash')
   v.need(hashlib.sha256(path.read_bytes()).hexdigest()==digest,'Changed immutable consumption claim')
   claim=json.loads(path.read_text(encoding='utf8'));v.need(set(claim)=={'version','bindings'} and claim['version']=='scarb-grouped-consumption-1','Invalid consumption claim')
   bindings_check(claim['bindings']);v.need(name==v.digest(claim['bindings'])+'.json','Claim identity mismatch')
   yield claim['bindings']
 else:v.need(not (root/'grouped-consumption-index.json').exists(),'Missing grouped claim directory')


def assert_unconsumed(root,bindings,*,expected_root,pending_proof=None):
 root=check_root(root,expected_root);bindings_check(bindings)
 pending=root/"grouped-accounting-pending.json"
 if pending.exists():
  v.need(pending_proof is not None and json.loads(pending.read_text())==pending_proof and pending_proof.get("bindings")==bindings and pending_proof.get("root")==str(root.resolve()),"Interrupted shared debit requires reconciliation; no dispatch/replay")
 from scripts.scarb_grouped_membership_candidate import snapshot
 blocked={r['packet_sha256'] for r in snapshot(root).values()}
 for claimed in grouped_claim_bindings(root):
  v.need(not blocked.intersection(claimed.values()),'Conflicting consumption claims')
  blocked.update(claimed.values())
 from scripts.scarb_ai_fact_slots import SEALED_PACKET_SHA256
 blocked.update(SEALED_PACKET_SHA256)
 v.need(not blocked.intersection(bindings.values()),'A prior attempt consumed this packet in solo or grouped lane')
 return True


def protected_root():
 return Path(os.environ["LOCALAPPDATA"])/"ScarbTO"/"voice-private"


def consume_grouped_locked(root,bindings,*,expected_root,pending_proof=None):
 """Persist consumption before any dispatch; claim means consumed, not adverse."""
 root=check_root(root,expected_root);assert_unconsumed(root,bindings,expected_root=expected_root,pending_proof=pending_proof)
 folder=root/'grouped-consumption';folder.mkdir(exist_ok=True)
 index=root/'grouped-consumption-index.json'
 record=json.loads(index.read_text(encoding='utf8')) if index.exists() else {'root':str(root.resolve()),'claims':{}}
 claim={'version':'scarb-grouped-consumption-1','bindings':bindings};name=v.digest(bindings)+'.json'
 import hashlib
 raw=v.encoded(claim);v.need(not (folder/name).exists(),'Immutable claim exists')
 record['claims'][name]=hashlib.sha256(raw).hexdigest()
 # Index first: interruption before claim is an explicit inconsistent/orphan
 # reservation and blocks dispatch/reuse. Never infer that it was not consumed.
 v.atomic_json(index,record)
 with (folder/name).open('xb') as handle:handle.write(raw)
