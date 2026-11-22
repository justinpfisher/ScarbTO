import unittest,tempfile,json
from pathlib import Path
from scripts import scarb_legacy_consumption_bindings as legacy,scarb_grouped_membership_candidate as m
class LegacyTests(unittest.TestCase):
 def test_exact_legacy_hash_and_key_only(self):
  for path,(raw,packet) in legacy.LEGACY.items():
   key=Path(path).stem;self.assertEqual(legacy.interpret(path,raw,key),packet)
   for args in [(path,'0'*64,key),(path,raw,'wrong'),('held/unknown.json',raw,key)]:
    with self.assertRaises(m.v.VoiceError):legacy.interpret(*args)
 def test_unknown_unbound_record_not_inferred(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'held').mkdir();(root/'held/unknown.json').write_text('{"key":"unknown"}')
   with self.assertRaises(m.v.VoiceError):m.snapshot(root)
 def test_nonhex_historical_and_membership_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'held').mkdir();(root/'held/bad.json').write_text(json.dumps({'packet_sha256':'g'*64}))
   with self.assertRaises(m.v.VoiceError):m.snapshot(root)
  zero={'reserved_nusd':0,'consumed_batches':{},'packet_membership':{}}
  with self.assertRaises(m.v.VoiceError):m.reserve(zero,{'A':m.v.digest('A')},1,{'held/a.json':{'sha256':'g'*64,'packet_sha256':m.v.digest('B')}})
  with self.assertRaises(m.v.VoiceError):m.validate({'reserved_nusd':1,'consumed_batches':{'g'*64:1},'packet_membership':{m.v.digest('A'):'g'*64}})
if __name__=='__main__':unittest.main()
