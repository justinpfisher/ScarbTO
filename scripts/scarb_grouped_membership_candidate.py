"""Pure per-packet consumption proof; no writes or retries."""
import hashlib,json,re
HEX=re.compile(r"^[0-9a-f]{64}$")
from pathlib import Path
from scripts import scarb_ai_voice as v,scarb_ai_fact_slots as f

def snapshot(root):
 root=Path(root);result={}
 for lane in ('held','accepted','accepted-v2'):
  for path in sorted((root/lane).glob('*.json')):
   v.need(path.is_file() and not path.is_symlink(),'Invalid solo record')
   raw=path.read_bytes();record=json.loads(raw.decode('utf8'))
   relative=str(path.relative_to(root)).replace('\\','/');raw_hash=hashlib.sha256(raw).hexdigest()
   packet_hash=record.get('packet_sha256')
   if packet_hash is None:
    from scripts.scarb_legacy_consumption_bindings import interpret
    packet_hash=interpret(relative,raw_hash,record.get('key',''))
   v.need(isinstance(packet_hash,str) and HEX.fullmatch(packet_hash),'Invalid solo packet hash')
   result[relative]={'sha256':raw_hash,'packet_sha256':packet_hash}
 return result

def validate(ledger):
 v.need(set(ledger)=={'reserved_nusd','consumed_batches','packet_membership'},'Missing packet ledger')
 batches=ledger['consumed_batches'];members=ledger['packet_membership']
 v.need(type(ledger['reserved_nusd']) is int and isinstance(batches,dict) and isinstance(members,dict),'Ledger types')
 v.need(all(isinstance(k,str) and HEX.fullmatch(k) and type(n) is int and n>0 for k,n in batches.items()) and ledger['reserved_nusd']==sum(batches.values()),'Ledger sum')
 v.need(all(isinstance(h,str) and HEX.fullmatch(h) and isinstance(batch,str) and HEX.fullmatch(batch) and batch in batches for h,batch in members.items()),'Membership mismatch')
 v.need(set(members.values())==set(batches),'Orphan reservation lacks consumed membership')

def reserve(before,bindings,amount,solo_state):
 from scripts.scarb_packet_consumption_candidate import bindings_check
 bindings_check(bindings)
 validate(before);v.need(type(amount) is int and amount>0,'Reserve amount')
 hashes=list(bindings.values());v.need(len(set(hashes))==len(hashes) and bool(hashes),'Duplicate or empty source bindings')
 blocked=set(before['packet_membership'])|set(f.SEALED_PACKET_SHA256)
 for name,record in solo_state.items():
  v.need(name.split('/')[0] in {'held','accepted','accepted-v2'} and set(record)=={'sha256','packet_sha256'},'Solo snapshot fields')
  v.need(all(isinstance(record[k],str) and HEX.fullmatch(record[k]) for k in ['sha256','packet_sha256']),'Invalid snapshot hash')
  blocked.add(record['packet_sha256'])
 v.need(not blocked.intersection(hashes),'Canonical packet previously consumed or held')
 scope=v.digest(bindings);v.need(scope not in before['consumed_batches'],'Batch previously consumed')
 after={'reserved_nusd':before['reserved_nusd']+amount,'consumed_batches':{**before['consumed_batches'],scope:amount},'packet_membership':{**before['packet_membership'],**{h:scope for h in hashes}}}
 validate(after);return after


def reserve_in_state(root,expected_root,before,bindings,amount):
 """Candidate only: consume under shared lock before any possible dispatch."""
 from scripts.scarb_packet_consumption_candidate import assert_unconsumed
 assert_unconsumed(root,bindings,expected_root=expected_root)
 after=reserve(before,bindings,amount,snapshot(root))
 from scripts.scarb_packet_consumption_candidate import consume_grouped_locked
 consume_grouped_locked(root,bindings,expected_root=expected_root)
 return after
