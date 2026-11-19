import unittest,json,subprocess
from pathlib import Path
from scripts import scarb_grouped_protected_caller_candidate as w
class SourceActions(unittest.TestCase):
 def test_all_nine_exact_source_bound_conditions(self):
  expected={"09a869a514276b26":"Utensils being used were not in good repair.","496fe84fd1aa10a6":"Utensils being used were not designed so they could be readily cleaned.","54a68a5e7db206d7":"Food equipment being used was not made of material that could be readily cleaned.","55eb3a9acbeba3d6":"Shelves being used were not designed so they could be readily cleaned.","7507fe18e4efce30":"Food equipment being used was not designed so it could be readily cleaned.","dc61761581abe33d":"Utensils being used were not made of material that could be readily cleaned.","fcf37504d73b4996":"Food equipment being used was not of sound, tight construction.","ffc9683a1081a818":"Utensils being used were not of sound, tight construction.","453b1dae8806a855":"Utensils were sanitized using an agent for which the testing reagent was not readily available."}
  packets=w.emitter.c.seam.current_canonical_requests();self.assertEqual(len(packets),736)
  contexts=json.loads(subprocess.check_output(["node","scripts/scarb_finding_contexts.mjs"],encoding="utf8"))
  for suffix,text in expected.items():
   with self.subTest(suffix=suffix):
    i="static.finding-explanation-"+suffix;p=packets[i];c=contexts[i]
    self.assertEqual(p["draft"],text);self.assertEqual(c["effective_translation"],text)
    self.assertEqual(p["evidence"][0]["fact"],text);self.assertEqual(p["evidence"][1]["fact"],c["official_wording"])
    self.assertEqual(p["locks"],{});self.assertEqual(p["kind"],"safety")
    self.assertTrue(c["official_wording"].startswith("sanitize utensils using" if suffix=="453b1dae8806a855" else "use "))
if __name__=="__main__":unittest.main()
