import unittest,copy,tempfile,json
from pathlib import Path
from scripts import scarb_grouped_membership_candidate as m
class MembershipTests(unittest.TestCase):
 def setUp(self):
  self.zero={'reserved_nusd':0,'consumed_batches':{},'packet_membership':{}};self.h={x:m.v.digest(x) for x in 'ABCD'}
 def bindings(self,letters):return {x:self.h[x] for x in letters}
 def test_success_regroup_refused_disjoint_allowed(self):
  ab=m.reserve(self.zero,self.bindings('AB'),10,{})
  with self.assertRaises(m.v.VoiceError):m.reserve(ab,self.bindings('BC'),10,{})
  cd=m.reserve(ab,self.bindings('CD'),10,{})
  self.assertEqual(len(cd['packet_membership']),4);self.assertEqual(cd['reserved_nusd'],20)
 def test_crash_orphan_membership_consumed_not_retried(self):
  reserved=m.reserve(self.zero,self.bindings('AB'),10,{})
  # No result or completion is needed for membership to be consumed.
  reopened=json.loads(json.dumps(reserved))
  with self.assertRaises(m.v.VoiceError):m.reserve(reopened,self.bindings('BC'),10,{})
 def test_tampered_orphan_fails_closed(self):
  state=m.reserve(self.zero,self.bindings('AB'),10,{})
  for change in ['empty','unknown','sum']:
   x=copy.deepcopy(state)
   if change=='empty':x['packet_membership']={}
   elif change=='unknown':x['packet_membership'][self.h['A']]='wrong'
   else:x['reserved_nusd']=0
   with self.assertRaises(m.v.VoiceError):m.reserve(x,self.bindings('CD'),10,{})
 def test_each_solo_lane_blocks_and_files_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for lane in ['held','accepted','accepted-v2']:
    folder=root/lane;folder.mkdir();path=folder/'record.json';path.write_text(json.dumps({'packet_sha256':self.h['B']}));before=path.read_bytes()
    snap=m.snapshot(root)
    with self.assertRaises(m.v.VoiceError):m.reserve(self.zero,self.bindings('AB'),10,snap)
    self.assertEqual(path.read_bytes(),before)
if __name__=='__main__':unittest.main()
