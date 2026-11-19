import unittest,copy
from scripts import scarb_grouped_queue_candidate as q
class QueueTests(unittest.TestCase):
 def fixture(self):
  groups=[];before=1860532000
  for n,res,debit in [(10,59991300,59992000),(11,59955600,59956000)]:
   bindings={f'fictional.{n}.{i}':q.v.digest({'fixture':n,'item':i}) for i in range(3)}
   groups.append(dict(scope_sha256=q.v.digest(bindings),packet_bindings=bindings,checkpoint_sha256=q.v.digest({'fixture':n}),reservation_nusd=res,rounded_debit_nusd=debit,before_cumulative_nusd=before,cumulative_nusd=before+debit));before+=debit
  return dict(version='scarb-exact-sequential-queue-1',head='fictional',source_pins={'fixture':'not-production'},groups=groups,maximum_calls=4,maximum_debit_nusd=119948000,final_cumulative_nusd=1980480000)
 def select(self,queue,statuses,completed=True,ready=True):
  return q.next_scope(queue,q.v.digest(queue),lambda g:statuses[queue['groups'].index(g)],lambda g:completed,lambda g:ready)
 def test_dry_run_and_confirmed_resume(self):
  x=self.fixture();self.assertEqual(self.select(x,['untouched']*2),x['groups'][0]);self.assertEqual(self.select(x,['completed','untouched']),x['groups'][1]);self.assertIsNone(self.select(x,['completed']*2))
 def test_every_uncertain_status_stops(self):
  for s in ['held-adverse','held-uncertain','running','queued','interrupted','unknown','preflight-refused']:
   with self.subTest(s=s),self.assertRaises(ValueError):self.select(self.fixture(),[s,'untouched'])
 def test_unverified_predecessor_no_skip(self):
  with self.assertRaises(ValueError):self.select(self.fixture(),['completed','untouched'],completed=False)
 def test_stale_funds_or_binding_no_start(self):
  with self.assertRaises(ValueError):self.select(self.fixture(),['untouched']*2,ready=False)
 def test_later_started_cannot_reorder(self):
  with self.assertRaises(ValueError):self.select(self.fixture(),['untouched','completed'])
 def test_manifest_digest_and_exact_fields(self):
  x=self.fixture();pin=q.v.digest(x);x['groups'].reverse()
  with self.assertRaises(ValueError):q.validate(x,pin)
  x=self.fixture();x['new_gate']=True
  with self.assertRaises(ValueError):q.validate(x,q.v.digest(x))
 def test_accounting_caps_and_no_overlap(self):
  for field,value in [('reservation_nusd',60000001),('rounded_debit_nusd',59991300),('before_cumulative_nusd',0),('checkpoint_sha256','bad')]:
   x=self.fixture();x['groups'][0][field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):q.validate(x,q.v.digest(x))
  x=self.fixture();x['groups'][1]['packet_bindings']=x['groups'][0]['packet_bindings']
  with self.assertRaises(ValueError):q.validate(x,q.v.digest(x))
 def test_no_dispatch_or_write_capability(self):
  import inspect
  source=inspect.getsource(q)
  for token in ('subprocess','requests.post','write_text','write_bytes','open('):self.assertNotIn(token,source)

 def test_singleton_deferred_not_solo_dispatched(self):
  x=self.fixture();g=x['groups'][0];g['packet_bindings']=dict(list(g['packet_bindings'].items())[:1]);g['scope_sha256']=q.v.digest(g['packet_bindings'])
  with self.assertRaises(ValueError):q.validate(x,q.v.digest(x))
