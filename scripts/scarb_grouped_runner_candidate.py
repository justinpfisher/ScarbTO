"""Protected-runner candidate exercised only with canned injected transport.
No key lookup, network transport, registry enrollment or publication entry point.
"""
import json,hashlib
from pathlib import Path
from scripts import scarb_ai_voice as v,scarb_ai_fact_slots as f
from scripts import scarb_grouped_context_candidate as c,scarb_grouped_provenance_candidate as verifier
from scripts import scarb_grouped_membership_candidate as membership
from scripts import scarb_shared_cost_proof_candidate as accounting
PURPOSE='synthetic-grouped-run'
def load(path):return json.loads(Path(path).read_text(encoding='utf8'))
def save(root,name,value):v.atomic_json(root/name,value)
def members(state):
 folder=state/'grouped-consumption';result={}
 for path in folder.glob('*.json') if folder.exists() else []:
  claim=load(path);scope=v.digest(claim['bindings'])
  for h in claim['bindings'].values():
   v.need(h not in result,'Duplicate membership');result[h]=scope
 return result

def review_diagnostics(packets,answer,requests,raws):
 # Exact membership and request/response validation precede any item observation.
 c.contract.check_membership(answer,[x['id'] for x in packets]);items={}
 for packet in packets:
  identity=packet['id'];dims=f.review_dimensions(answer[identity])
  adverse=dims['schema_valid'] and (not all(dims[k] for k in ['approve','meaning_preserved','limitations_preserved','voice_pass']) or dims['issues_present'])
  items[identity]={'packet_sha256':v.digest(packet),'dimensions':dims,'outcome':'malformed' if not dims['schema_valid'] else 'adverse' if adverse else 'favorable-observed'}
 return {'version':'scarb-grouped-review-observations-1','items':items,'request_sha256':{k:v.digest(x) for k,x in requests.items()},'response_sha256':{k:v.digest(x) for k,x in raws.items()},'acceptance_granted':False}

def _run_sequence(state,packets,models,funding,prices,*,transport,started_at,completed_at,crash_at=None,production=False,approved_manifest_sha256=None):
 state=Path(state)
 from scripts.scarb_grouped_protected_caller_candidate import FixedResponsesInjected,ProtectedResponses,launcher_preflight
 if production:
  launcher_preflight(approved_manifest_sha256);v.need(type(transport) is ProtectedResponses,'Fixed protected transport required')
 else:v.need(type(transport) in (f.FixtureTransport,FixedResponsesInjected),'Only isolated injected transport is supported')
 v.need(production or (state/'SYNTHETIC_GROUPED_ACCOUNTING_ONLY').is_file(),'Synthetic isolated state required')
 contexts=c.current_contexts(packets);bindings={x['id']:v.digest(x) for x in packets};scope=v.digest(bindings)
 root=state/'grouped-runs'/scope;v.need(not root.exists(),'Prior attempt cannot be replayed');root.mkdir(parents=True)
 journal={'version':'scarb-grouped-execution-journal-1','status':'preparing','calls':0,'packet_bindings':bindings,'stages':[],'started_at':started_at,'completed_at':completed_at}
 save(root,'journal.json',journal)
 author=c.context_prompts(packets,models,contexts);bounds={'author':len(v.encoded(author)),'reviewer':48000};outputs={'author':2000,'reviewer':2000}
 def cost(model,i,o):
  rate=prices[model];v.need(set(rate)=={'input_nusd_per_million','output_nusd_per_million'} and all(type(x) is int and x>=0 for x in rate.values()),'Invalid price pin')
  return (i*rate['input_nusd_per_million']+o*rate['output_nusd_per_million']+999999)//1000000
 reserve=sum(cost(models[role],bounds[role],outputs[role]) for role in bounds)
 now=v.instant(started_at);v.need(v.instant(funding['observed_at'])<=now<=v.instant(funding['expires_at']) and (now-v.instant(funding['observed_at'])).total_seconds()<=3600 and funding['auto_recharge_disabled'] is True and funding['balance_nusd']>=5000000000+funding['cap_nusd'],'Stale/insufficient funding')
 month=started_at[:7];mb=members(state);solo=membership.snapshot(state)
 for name,value in [('funding.json',funding),('prices.json',prices),('membership-before.json',mb),('solo-state.json',solo)]:save(root,name,value)
 try:
  reservation=accounting._debit_sequence(state,state,bindings,reserve,month,funding['cap_nusd'],funding['cap_nusd'])
  ma=members(state)
  for name,value in [('ledger-before.json',reservation['before']),('ledger-after.json',reservation['after']),('membership-after.json',ma)]:save(root,name,value)
  journal['status']='reserved';save(root,'journal.json',journal)
  if crash_at=='after_reserve':raise RuntimeError('synthetic interruption after reservation')
  raws={};requests={};authors=None
  with v.exclusive(state):
   for role in ['author','reviewer']:
    request=author if role=='author' else c.context_prompts(packets,models,contexts,authors)[1]
    requests[role]=request;save(root,role+'-request.json',request)
    journal['calls']+=1;journal['status']=role+'-dispatched';save(root,'journal.json',journal)
    raw=transport.exchange(request);save(root,role+'-response.json',raw);raws[role]=raw
    if crash_at=='after_'+role+'_response':raise RuntimeError('synthetic interruption after response')
    v.need(raw.get('model')==models[role] and isinstance(raw.get('id'),str) and raw['id'],'Wrong returned model/response')
    answer,usage=v.unpack(raw)
    v.need(usage['input_tokens']<=bounds[role] and usage['output_tokens']<=outputs[role],'Response usage exceeds reserved envelope')
    journal['stages'].append({'role':role,'request_sha256':v.digest(request),'response_sha256':v.digest(raw),'response_id':raw['id'],'model':raw['model'],'usage':usage})
    save(root,'journal.json',journal)
    if role=='author':
     authors=answer;c.context_prompts(packets,models,contexts,authors)
    else:
     diagnostics=review_diagnostics(packets,answer,requests,raws)
     save(root,'review-diagnostics.json',diagnostics)
     outcomes=[x['outcome'] for x in diagnostics['items'].values()]
     if any(x=='adverse' for x in outcomes):journal['status']='held-adverse'
     elif any(x=='malformed' for x in outcomes):journal['status']='held-uncertain'
     save(root,'journal.json',journal)
     v.need(all(x=='favorable-observed' for x in outcomes),'Grouped review not wholly favorable; no split acceptance')
   journal['status']='completed';journal['completed_at']=v.dt.datetime.now(v.dt.timezone.utc).isoformat() if production else completed_at;save(root,'journal.json',journal)
   envelope={'version':'scarb-grouped-run-envelope-2','packets':packets,'models':models,'source_context':contexts,'author_request':requests['author'],'review_request':requests['reviewer'],'author_response':raws['author'],'review_response':raws['reviewer']}
   save(root,'envelope.json',envelope)
   actual=sum(cost(models[x['role']],x['usage']['input_tokens'],x['usage']['output_tokens']) for x in journal['stages'])
   budget=accounting.proof(reservation['before'],reservation['after'],month,reserve,actual,funding['cap_nusd'],funding['cap_nusd'],bindings,mb,ma)
   budget.update(funding_sha256=v.digest(funding),prices_sha256=v.digest(prices),input_bounds=bounds,output_bounds=outputs);save(root,'budget.json',budget)
   seal={'version':'scarb-grouped-consumed-seal-1','status':'consumed-completed','packet_bindings':bindings,'envelope_sha256':v.digest(envelope),'journal_sha256':v.digest(journal),'budget_sha256':v.digest(budget),'ledger_after_sha256':v.digest(reservation['after']),'packet_membership_sha256':v.digest(ma),'solo_state_sha256':v.digest(solo)};save(root,'seal.json',seal)
   files=verifier.FILES|{'solo-state.json','membership-before.json','membership-after.json'}
   manifest={'version':'scarb-grouped-run-manifest-1','purpose':'production-grouped-review' if production else PURPOSE,'runner_sha256':verifier.file_hash(Path(__file__)),'files':{name:verifier.file_hash(root/name) for name in files}};save(root,'manifest.json',manifest)
   pin={'manifest_sha256':verifier.file_hash(root/'manifest.json'),'runner_sha256':manifest['runner_sha256'],'packet_bindings':bindings,'requested_models':models,'returned_models':models,'funding_sha256':v.digest(funding),'prices_sha256':v.digest(prices),'ledger_before_sha256':v.digest(reservation['before']),'reservation_nusd':reserve,'source_context_sha256':v.digest(contexts),'membership_version':1,'solo_state_sha256':v.digest(solo),'solo_state_root':str(state),'cost_version':2,'month_cap_nusd':funding['cap_nusd'],'membership_before_sha256':v.digest(mb),'expected_purpose':'production-grouped-review' if production else PURPOSE}
   verified=verifier._verify_pinned(root,pin,packets);save(root,'candidate-pin.json' if production else 'fixture-pin.json',pin)
   return {'root':str(root),'pin':pin,'verified':verified,'calls':journal['calls']}
 except (Exception,KeyboardInterrupt) as error:
  journal['status']='held-adverse' if journal['status']=='held-adverse' else 'held-uncertain';save(root,'journal.json',journal)
  save(root,'interruption.json',{'kind':type(error).__name__,'replay_allowed':False})
  raise

def recover_fixture(state,packets):
 root=Path(state)/'grouped-runs'/v.digest({x['id']:v.digest(x) for x in packets});journal=load(root/'journal.json')
 if journal['status']=='completed':
  pin_paths=[x for x in [root/'fixture-pin.json',root/'candidate-pin.json'] if x.exists()]
  v.need(len(pin_paths)==1,'Missing or ambiguous completion pin')
  pin=load(pin_paths[0]);verifier._verify_pinned(root,pin,packets)
 else:
  v.need(not (root/'fixture-pin.json').exists() and not (root/'candidate-pin.json').exists(),'Incomplete attempt has success pin')
  if (root/'review-diagnostics.json').exists():
   requests={role:load(root/(role+'-request.json')) for role in ['author','reviewer']}
   raws={role:load(root/(role+'-response.json')) for role in ['author','reviewer']}
   models={role:requests[role]['model'] for role in requests}
   authors,_=v.unpack(raws['author']);answer,_=v.unpack(raws['reviewer'])
   a,b=c.context_prompts(packets,models,c.current_contexts(packets),authors)
   v.need(requests=={'author':a,'reviewer':b},'Recovered review request mismatch')
   expected_stages=[]
   for role in ['author','reviewer']:
    raw=raws[role];_,usage=v.unpack(raw);v.need(raw['model']==models[role],'Recovered model mismatch')
    expected_stages.append({'role':role,'request_sha256':v.digest(requests[role]),'response_sha256':v.digest(raw),'response_id':raw['id'],'model':raw['model'],'usage':usage})
   v.need(journal['stages']==expected_stages,'Recovered stage mismatch')
   expected=review_diagnostics(packets,answer,requests,raws)
   v.need(load(root/'review-diagnostics.json')==expected,'Recovered item observations differ')
   outcomes=[x['outcome'] for x in expected['items'].values()]
   v.need(journal['status']==('held-adverse' if 'adverse' in outcomes else 'held-uncertain'),'Recovered batch outcome differs')
 return {'status':journal['status'],'calls':journal['calls'],'validated_stages':len(journal['stages']),'replay_allowed':False}


def run_fixture(*args,**kwargs):return _run_sequence(*args,**kwargs)
