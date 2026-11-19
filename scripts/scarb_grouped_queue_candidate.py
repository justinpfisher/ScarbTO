"""Offline exact-scope sequencing helper. No transport, state writes or authority grants.
A coordinator supplies an already-authorized queue digest and existing verification callbacks.
Production dispatch remains exclusively with the existing protected caller.
"""
from scripts import scarb_ai_voice as v, scarb_shared_cost_proof_candidate as amounts

def validate(queue, approved_digest):
 v.need(v.digest(queue)==approved_digest,'Queue binding changed')
 v.need(set(queue)=={'version','head','source_pins','groups','maximum_calls','maximum_debit_nusd','final_cumulative_nusd'},'Queue fields')
 v.need(queue['version']=='scarb-exact-sequential-queue-1' and isinstance(queue['groups'],list) and bool(queue['groups']),'Queue version/groups')
 seen=set();scopes=set();total=0;prior=None
 for g in queue['groups']:
  v.need(set(g)=={'scope_sha256','packet_bindings','checkpoint_sha256','reservation_nusd','rounded_debit_nusd','before_cumulative_nusd','cumulative_nusd'},'Queue scope fields')
  b=g['packet_bindings'];v.need(isinstance(b,dict) and 1<=len(b)<=3 and not seen.intersection(b),'Queue packet membership')
  v.need(g['scope_sha256']==v.digest(b) and g['scope_sha256'] not in scopes,'Queue scope binding')
  for name in ('checkpoint_sha256',):v.need(isinstance(g[name],str) and len(g[name])==64 and all(c in '0123456789abcdef' for c in g[name]),'Checkpoint binding')
  for name in ('reservation_nusd','rounded_debit_nusd','before_cumulative_nusd','cumulative_nusd'):v.need(type(g[name]) is int and g[name]>=0,'Queue accounting type')
  before={'months':{'2000-01':g['before_cumulative_nusd']/1e9},'paid_pilot_usd':g['before_cumulative_nusd']/1e9}
  _,charged=amounts.debit(before,'2000-01',g['reservation_nusd'],g['cumulative_nusd'],g['cumulative_nusd'])
  v.need(g['reservation_nusd']<=60000000 and g['rounded_debit_nusd']==charged,'Queue reservation/debit')
  v.need(g['cumulative_nusd']==g['before_cumulative_nusd']+g['rounded_debit_nusd'] and (prior is None or prior==g['before_cumulative_nusd']),'Queue accounting chain')
  prior=g['cumulative_nusd'];total+=g['rounded_debit_nusd'];seen.update(b);scopes.add(g['scope_sha256'])
 v.need(queue['maximum_calls']==2*len(queue['groups']) and queue['maximum_debit_nusd']==total and queue['final_cumulative_nusd']==prior,'Queue totals')
 return True

def next_scope(queue,approved_digest,observe,verify_completed,verify_ready):
 """Read-only dry run/resumption. All callbacks are existing supported checks.
 Never infer completion from a worker turn; verify the sealed predecessor and ledger.
 No automatic retry of held, uncertain, running or dispatched-without-terminal work.
 """
 validate(queue,approved_digest)
 observations=[observe(g) for g in queue['groups']]
 for i,(g,status) in enumerate(zip(queue['groups'],observations)):
  if status=='completed':
   v.need(verify_completed(g) is True,'Predecessor proof failed')
   continue
  v.need(status=='untouched','Queue stopped: non-completed attempt; no retry')
  v.need(all(s=='untouched' for s in observations[i:]),'Queue order conflicts with execution state')
  v.need(verify_ready(g) is True,'Current protected preflight not ready')
  return g
 return None
