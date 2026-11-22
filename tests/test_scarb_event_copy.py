import json,unittest
from scripts.scarb_accepted_copy import event_copy
class EventCopyTests(unittest.TestCase):
 def test_exact_facts_or_no_explanation(self):
  event={'id':'one','feed':'dinesafe','name':'A','status':'Pass','detected_at':'2026-11-01T00:00:00Z'}
  bindings={'one':{'key':'event.one','facts':json.dumps(event,sort_keys=True,separators=(',',':'))}}
  self.assertEqual(event_copy(event,bindings=bindings,read=lambda k:'Accepted'),'Accepted')
  for changed in ({**event,'status':'Closed'},{**event,'name':'B'},{**event,'id':'new'}):
   self.assertIsNone(event_copy(changed,bindings=bindings,read=lambda k:self.fail('stale copy read')))
 def test_missing_binding_never_calls_reader(self):
  self.assertIsNone(event_copy({'id':'new'},bindings={},read=lambda k:self.fail('unregistered')))
