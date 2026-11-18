"""Offline grouped provenance verifier candidate. No trusted live runs enrolled.

A self-reported origin or rehashed envelope is NOT a trust anchor. Production
entry requires an independently pinned runner manifest; diagnostic/fixture
records never qualify. This module is not wired to the publication bridge.
"""
import json,hashlib
from pathlib import Path
from scripts import scarb_ai_voice as v,scarb_ai_fact_slots as f
from scripts import scarb_grouped_fixture_envelope as contract
# Deliberately empty: no real production-qualified grouped runner records exist.
from types import MappingProxyType
TRUSTED_GROUPED_RUNS=MappingProxyType({})
FILES={'envelope.json','journal.json','seal.json','funding.json','prices.json','budget.json','ledger-before.json','ledger-after.json'}
def file_hash(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def _verify_pinned(root,pin,current_packets):
    """Pure verification seam; callers cannot turn this test helper into a grant."""
    root=Path(root);manifest_path=root/'manifest.json'
    v.need(not root.is_symlink() and manifest_path.is_file() and not manifest_path.is_symlink(),'Invalid protected record path')
    v.need(file_hash(manifest_path)==pin['manifest_sha256'],'Untrusted manifest bytes')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    v.need(set(manifest)=={'version','purpose','runner_sha256','files'} and manifest['version']=='scarb-grouped-run-manifest-1'
           and manifest['purpose']==pin.get('expected_purpose','production-grouped-review') and manifest['runner_sha256']==pin['runner_sha256'],'Diagnostic/fixture or wrong runner provenance')
    membership=pin.get('membership_version')==1
    v.need(set(manifest['files'])==FILES|({'solo-state.json'} if membership else set())|({'membership-before.json','membership-after.json'} if pin.get('cost_version')==2 else set()),'Complete exact record set required')
    records={}
    for name,digest in manifest['files'].items():
        path=root/name;v.need(path.is_file() and not path.is_symlink() and file_hash(path)==digest,'Record bytes differ')
        records[name]=json.loads(path.read_text(encoding='utf-8'))
    env=records['envelope.json'];journal=records['journal.json'];seal=records['seal.json']
    versioned=env.get('version')=='scarb-grouped-run-envelope-3'
    contextual=env.get('version') in {'scarb-grouped-run-envelope-2','scarb-grouped-run-envelope-3'}
    prompt_version=contract.CITATION_PROMPT if versioned else contract.LEGACY_PROMPT
    if versioned:
        v.need(env.get('prompt_version')==pin.get('prompt_version')==journal.get('prompt_version')==prompt_version,'Prompt version binding mismatch')
    else:
        v.need(all('prompt_version' not in x for x in (env,pin,journal)),'Legacy prompt version substitution')
    fields={'version','packets','models','author_request','review_request','author_response','review_response'}
    v.need(set(env)==fields|({'source_context'} if contextual else set())|({'prompt_version'} if versioned else set()) and env['version'] in {'scarb-grouped-run-envelope-1','scarb-grouped-run-envelope-2','scarb-grouped-run-envelope-3'},'Not a production grouped envelope')
    expected={p['id']:v.digest(p) for p in current_packets}
    v.need(len(expected)==len(current_packets) and expected==pin['packet_bindings'] and env['packets']==current_packets
           and env['models']==pin['requested_models'],'Current packet/model eligibility differs')
    ar=env['author_response'];rr=env['review_response']
    for role,response in [('author',ar),('reviewer',rr)]:
        v.need(response.get('model')==pin['returned_models'][role] and isinstance(response.get('id'),str) and response['id'],'Returned model/response ID mismatch')
    v.need(ar['id']!=rr['id'] and pin['requested_models']['author']!=pin['requested_models']['reviewer'],'Separate independent reviewer required')
    authors,author_usage=v.unpack(ar);reviews,review_usage=v.unpack(rr)
    if contextual:
        from scripts.scarb_grouped_context_candidate import current_contexts,context_prompts
        v.need(membership,'Contextual admission requires packet membership')
        contexts=current_contexts(current_packets)
        from scripts.scarb_group21_source_compatibility import historical_context
        contexts=historical_context(pin,contexts,env['source_context'])
        v.need(env['source_context']==contexts and pin.get('source_context_sha256')==v.digest(contexts),'Current source context mismatch')
        a,r=context_prompts(current_packets,pin['requested_models'],contexts,authors,prompt_version=prompt_version)
    else:
        a,r=contract.prompts(current_packets,pin['requested_models'],authors)
    v.need(env['author_request']==a and env['review_request']==r,'Prompt/schema/candidate provenance mismatch')
    contract.check_membership(reviews,list(expected));texts={}
    for packet in current_packets:
        identity=packet['id'];w=f.assemble(packet,authors[identity]);v.review_check(reviews[identity]);texts[identity]=v.text_check(packet,w)
    v.need(set(journal)=={'version','status','calls','packet_bindings','stages','started_at','completed_at'}|({'prompt_version'} if versioned else set()) and journal['version']=='scarb-grouped-execution-journal-1'
           and journal['status']=='completed' and journal['calls']==2 and journal['packet_bindings']==expected,'Incomplete or ineligible execution journal')
    stages=[]
    for role,request,response,usage in [('author',a,ar,author_usage),('reviewer',r,rr,review_usage)]:
        v.need(usage['input_tokens']<=48000 and usage['output_tokens']<=2000,'Usage outside recorded bounds')
        stages.append({'role':role,'request_sha256':v.digest(request),'response_sha256':v.digest(response),'response_id':response['id'],'model':response['model'],'usage':usage})
    v.need(journal['stages']==stages,'Execution journal does not bind exact requests/responses/usage')
    cost_proof=_verify_cost(records,pin,a,r,journal,stages)
    v.need(seal=={'version':'scarb-grouped-consumed-seal-1','status':'consumed-completed','packet_bindings':expected,
           'envelope_sha256':v.digest(env),'journal_sha256':v.digest(journal),'budget_sha256':v.digest(records['budget.json']),'ledger_after_sha256':v.digest(records['ledger-after.json']),**({'packet_membership_sha256':v.digest(records['membership-after.json'] if pin.get('cost_version')==2 else records['ledger-after.json']['packet_membership']),'solo_state_sha256':v.digest(records['solo-state.json'])} if membership else {})},'Missing/altered consumed seal')
    return {'version':'scarb-grouped-verified-provenance-1','manifest_sha256':pin['manifest_sha256'],
            'packet_bindings':expected,'models':env['models'],'text_sha256':{i:v.digest(t) for i,t in texts.items()},'cost_proof':cost_proof}

def verify_grouped_provenance(root,current_packets):
    path=Path(root)/'manifest.json'
    v.need(path.is_file(),'Trusted grouped record is absent')
    digest=file_hash(path)
    v.need(digest in TRUSTED_GROUPED_RUNS,'No trusted production grouped run enrolled; diagnostic and fixture promotion refused')
    from scripts.scarb_grouped_membership_candidate import snapshot
    pin=TRUSTED_GROUPED_RUNS[digest]
    v.need(pin.get('expected_purpose','production-grouped-review')=='production-grouped-review','Synthetic runner cannot be admitted')
    v.need(pin.get('membership_version')==1 and v.digest(snapshot(pin['solo_state_root']))==pin.get('solo_state_sha256'),'Current solo holds/acceptances differ')
    env=json.loads((Path(root)/'envelope.json').read_text(encoding='utf8'))
    v.need(env.get('version') in {'scarb-grouped-run-envelope-2','scarb-grouped-run-envelope-3'},'Context-bound grouped version required for actual admission')
    return _verify_pinned(root,TRUSTED_GROUPED_RUNS[digest],current_packets)


def _verify_cost(records,pin,author,review,journal,stages):
    """Integer nanodollars only: no float rounding, inferred refund or free replay."""
    funding=records['funding.json'];prices=records['prices.json'];budget=records['budget.json']
    before=records['ledger-before.json'];after=records['ledger-after.json']
    v.need(v.digest(funding)==pin['funding_sha256'] and v.digest(prices)==pin['prices_sha256']
           and v.digest(before)==pin['ledger_before_sha256'],'Funding/price/preledger provenance mismatch')
    v.need(set(funding)=={'observed_at','expires_at','balance_nusd','auto_recharge_disabled','organization','project','cap_nusd'}
           and funding['auto_recharge_disabled'] is True,'Funding observation incomplete')
    for n in ['balance_nusd','cap_nusd']:v.need(type(funding[n]) is int and funding[n]>=0,'Integer funding amount required')
    started=v.instant(journal['started_at']);ended=v.instant(journal['completed_at']);observed=v.instant(funding['observed_at']);expires=v.instant(funding['expires_at'])
    v.need(observed<=started<=expires and 0<=(started-observed).total_seconds()<=3600 and ended>=started,'Funding stale or execution chronology invalid')
    v.need(set(prices)==set(pin['requested_models'].values()),'Exact model price inputs required')
    for rates in prices.values():
        v.need(set(rates)=={'input_nusd_per_million','output_nusd_per_million'} and all(type(x) is int and x>=0 for x in rates.values()),'Invalid integer price inputs')
    def cost(model,inputs,outputs):
        rates=prices[model];n=inputs*rates['input_nusd_per_million']+outputs*rates['output_nusd_per_million']
        return (n+999999)//1000000
    bounds={'author':len(v.encoded(author)),'reviewer':48000};outputs={'author':2000,'reviewer':2000}
    reserve=sum(cost(pin['requested_models'][role],bounds[role],outputs[role]) for role in bounds)
    actual=sum(cost(pin['requested_models'][s['role']],s['usage']['input_tokens'],s['usage']['output_tokens']) for s in stages)
    for stage in stages:
        role=stage['role'];u=stage['usage']
        v.need(all(type(u[k]) is int and u[k]>=0 for k in ['input_tokens','output_tokens']) and u['input_tokens']<=bounds[role] and u['output_tokens']<=outputs[role],'Actual usage exceeds reserved envelope')
    v.need(type(pin['reservation_nusd']) is int and reserve==pin['reservation_nusd'] and actual<=reserve,'Missing/mismatched or exceeded reservation')
    if pin.get('cost_version')==2:
        from scripts.scarb_shared_cost_proof_candidate import proof
        mb=records['membership-before.json'];ma=records['membership-after.json']
        v.need(v.digest(mb)==pin.get('membership_before_sha256'),'Prior membership provenance mismatch')
        solo_state=records['solo-state.json']
        v.need(v.digest(solo_state)==pin.get('solo_state_sha256'),'Solo provenance mismatch')
        from scripts.scarb_grouped_membership_candidate import HEX
        blocked=set(f.SEALED_PACKET_SHA256)
        for record in solo_state.values():
            v.need(set(record)=={'sha256','packet_sha256'} and all(isinstance(x,str) and HEX.fullmatch(x) for x in record.values()),'Invalid solo snapshot')
            blocked.add(record['packet_sha256'])
        v.need(not blocked.intersection(pin['packet_bindings'].values()),'Prior solo consumption')
        month=journal['started_at'][:7]
        value=proof(before,after,month,reserve,actual,pin['month_cap_nusd'],funding['cap_nusd'],pin['packet_bindings'],mb,ma)
        value.update(funding_sha256=v.digest(funding),prices_sha256=v.digest(prices),input_bounds=bounds,output_bounds=outputs)
        v.need(budget==value,'Shared cost proof mismatch')
        v.need(funding['balance_nusd']>=5_000_000_000+funding['cap_nusd'],'Funding buffer exceeded')
        return {'reserved_nusd':reserve,'debited_nusd':value['debited_nusd'],'actual_usage_cost_nusd':actual,'no_refund':True}
    expected={'version':'scarb-grouped-cost-proof-1','reservation_nusd':reserve,'actual_usage_cost_nusd':actual,'input_bounds':bounds,'output_bounds':outputs,
              'funding_sha256':v.digest(funding),'prices_sha256':v.digest(prices),'ledger_before_sha256':v.digest(before),'ledger_after_sha256':v.digest(after)}
    v.need(type(budget.get('reservation_nusd')) is int and type(budget.get('actual_usage_cost_nusd')) is int
           and all(type(x) is int for key in ['input_bounds','output_bounds'] for x in budget.get(key,{}).values()),'Integer deterministic cost proof required')
    v.need(budget==expected,'Cost/reservation proof mismatch')
    if pin.get('membership_version')==1:
        from scripts.scarb_grouped_membership_candidate import reserve as reserve_membership
        solo_state=records['solo-state.json']
        v.need(v.digest(solo_state)==pin.get('solo_state_sha256'),'Solo state provenance mismatch')
        v.need(after==reserve_membership(before,pin['packet_bindings'],pin['reservation_nusd'],solo_state),'Packet membership transition differs')
    else:
        for ledger in [before,after]:
            v.need(set(ledger)=={'reserved_nusd','consumed_batches'} and type(ledger['reserved_nusd']) is int and ledger['reserved_nusd']>=0
                   and isinstance(ledger['consumed_batches'],dict) and all(type(x) is int and x>0 for x in ledger['consumed_batches'].values()),'Invalid consuming ledger')
            v.need(ledger['reserved_nusd']==sum(ledger['consumed_batches'].values()),'Ledger reservation sum mismatch')
        scope=v.digest(pin['packet_bindings'])
        v.need(scope not in before['consumed_batches'],'Attempt already consumed')
        v.need(after=={'reserved_nusd':before['reserved_nusd']+reserve,'consumed_batches':{**before['consumed_batches'],scope:reserve}},'Refund, reuse or changed prior consumption')
    v.need(after['reserved_nusd']<=funding['cap_nusd'] and funding['balance_nusd']>=5_000_000_000+funding['cap_nusd'],'Budget/buffer exceeded')
    return {'reserved_nusd':reserve,'actual_usage_cost_nusd':actual,'no_refund':True}

