"""Versioned v2 fact-slot contract. Live dispatch is explicitly disabled by default.

Does not change v1 receipts, held attempts, cache keys or accepted catalogues.
All implementation tests are offline. No live v2 qualification is claimed.
"""
from scripts import scarb_ai_voice as v

VERSION = "scarb-ai-fact-slots-2"
FRESH_HEADLINE_PACKET_SHA256 = "a014d351e20bf0b97d4e77311dc626b9ba756deb3a7558f7187476732fb3e6c2"
QUALIFICATION_PACKET_SHA256 = "d17d1dc701dfaf10f04144afab0b7f2cfe2c61d549a2e9036220a9a20c10de1a"
# These real qualification attempts are sealed. Prompt/schema/key changes must
# never turn a new cache identity into permission to repeat the same source.
SEALED_PACKET_SHA256 = frozenset({
    "d1ee00949d7848b8046873c82dcd4490ef73f0b64b8bb2b8a204b435131c8fc0",
    "e8f8d7fda9aa2749b15acaf4450a988b9b29882b04fabd194168bce6f5b6fd18",
    QUALIFICATION_PACKET_SHA256,
})

def review_dimensions(result):
    """Finite summary only; never persist free-form issues or response text."""
    names=('approve','meaning_preserved','limitations_preserved','voice_pass')
    valid=(isinstance(result,dict) and set(result)==set(names)|{'issues'}
           and all(type(result[n]) is bool for n in names)
           and isinstance(result['issues'],list) and all(isinstance(x,str) for x in result['issues']))
    if not valid:return {'schema_valid':False}
    return {'schema_valid':True,**{n:result[n] for n in names},'issues_present':bool(result['issues'])}

AUTHOR = v.AUTHOR.replace(
    "Use only its supported meaning. Keep each {{LOCK:...}} token EXACTLY ONCE, intact;\ndo not reproduce its value elsewhere.",
    "Use only its supported meaning. Do not write lock tokens or reproduce their values\nin prose. Every required fact slot will be inserted unchanged by the assembler.")
AUTHOR = AUTHOR.replace(
    "Return body and evidence_ids using the schema. body is plain text with lock tokens.",
    "Return slots, tail and evidence_ids using the schema. Each named slot has a\nunique integer rank from zero through the number of slots minus one, and before\ncontains plain-text prose immediately preceding that fact. Choose the fact order\nand all connective prose freely; the assembler inserts the corresponding value\nafter each before field and appends tail. Empty connective fields are allowed.\nUse punctuation and spacing deliberately. Do not duplicate or omit a fact.")
REVIEWER = v.REVIEWER + "\nAssess the entire deterministically assembled candidate and materialised text, not individual slot fragments. Fact order and connective prose must preserve the evidenced relationships and source prominence.\n"

def schema(packet):
    v.packet_check(packet)
    v.need(packet['kind'] != 'verbatim', 'Verbatim remains in its original protected lane')
    slot = v.object_schema({'rank':{'type':'integer'}, 'before':{'type':'string'}})
    return v.object_schema({'slots':v.object_schema({name:slot for name in packet['locks']}),
                            'tail':{'type':'string'},'evidence_ids':{'type':'array','items':{'type':'string'}}})

def assemble(packet, result):
    schema(packet)
    v.need(isinstance(result,dict) and set(result)=={'slots','tail','evidence_ids'},'Unexpected slot output')
    v.need(len(v.encoded(result)) <= 24000, 'Slot output oversized')
    slots=result['slots']
    v.need(isinstance(slots,dict) and set(slots)==set(packet['locks']),'Incomplete or unknown fact slots')
    ranks=[]
    for item in slots.values():
        v.need(isinstance(item,dict) and set(item)=={'rank','before'},'Unexpected fact slot')
        v.need(type(item['rank']) is int and isinstance(item['before'],str),'Invalid fact slot')
        v.need(not v.TOKEN.search(item['before']),'Model must not supply lock tokens')
        ranks.append(item['rank'])
    v.need(sorted(ranks)==list(range(len(slots))),'Invalid fact ordering')
    v.need(isinstance(result['tail'],str) and not v.TOKEN.search(result['tail']),'Invalid prose tail')
    body=''.join(item['before']+'{{LOCK:'+name+'}}' for name,item in sorted(slots.items(),key=lambda pair:pair[1]['rank']))+result['tail']
    writer={'body':body,'evidence_ids':result['evidence_ids']}
    v.text_check(packet,writer)
    return writer

def cache_key(packet, config):
    return v.digest({'packet':packet,'version':VERSION,'author_prompt':AUTHOR,'reviewer_prompt':REVIEWER,
                     'schemas':[schema(packet),v.REVIEW_SCHEMA],
                     'models':[config['author_model'],config['reviewer_model']]})

def author_request(packet, config):
    return v.request_body(config['author_model'],AUTHOR,{'request':packet},schema(packet))

def review_request(packet, result, config):
    writer=assemble(packet,result)
    return v.request_body(config['reviewer_model'],REVIEWER,
                          {'request':packet,'candidate':writer,'materialised_text':v.text_check(packet,writer)},v.REVIEW_SCHEMA)

def fixture_accept(packet,result,review,config):
    """Offline witness only; cannot impersonate a production accepted receipt."""
    writer=assemble(packet,result);v.review_check(review)
    return {'version':VERSION,'key':cache_key(packet,config),'origin':'test-fixture',
            'slot_output':result,'writer':writer,'text':v.text_check(packet,writer),'review':review}


class FixtureTransport:
    """Canned responses only: no callback, URL opener or live credential input."""
    def __init__(self, responses):
        import copy
        self.responses=copy.deepcopy(responses);self.calls=[]
    def exchange(self, body):
        self.calls.append(body)
        v.need(bool(self.responses),'Fixture response missing')
        result=self.responses.pop(0)
        if isinstance(result, Exception):raise result
        return result

def reservation_bound(packet,config):
    # Include dynamic schema + both prompts + maximum reconstructed reviewer
    # payload, counting UTF-8 bytes conservatively as input tokens.
    bound=len(v.encoded(author_request(packet,config)))+len(REVIEWER.encode())+48000+16000
    reserve=sum((bound*v.MODELS[m][0]+2000*v.MODELS[m][1])/1000000 for m in (config['author_model'],config['reviewer_model']))
    return bound,reserve

def receipt_check(receipt,packet,config,*,fixture=False):
    expected='test-fixture' if fixture else 'openai-api-reviewed'
    v.need(receipt.get('version')==VERSION and receipt.get('origin')==expected,'Unqualified v2 receipt')
    v.need(receipt.get('key')==cache_key(packet,config) and receipt.get('packet_sha256')==v.digest(packet),'Fixture input changed')
    v.need(receipt.get('sha256')==v.digest({k:x for k,x in receipt.items() if k!='sha256'}),'Fixture receipt changed')
    writer=assemble(packet,receipt['slot_output']);v.review_check(receipt['review'])
    v.need(writer==receipt['writer'] and v.text_check(packet,writer)==receipt['text'],'Fixture assembly changed')
    return receipt['text']

def _generate(packet,config,state,*,transport,now,env,live=False):
    """End-to-end offline dispatch simulation. Cannot select live transport.

    Uses the same ledger shape and checks old v1 holds before starting a new key.
    Call only with disposable test state; never an owner credential environment.
    """
    import json,math
    v.need((live and transport is v.api_request) or (not live and type(transport) is FixtureTransport),'Unsupported v2 transport')
    v.need(v.digest(packet) not in SEALED_PACKET_SHA256,'Source packet has a sealed prior attempt')
    v.check_config(config);schema(packet)
    f=config['funding']
    if f.get('billing_mode')=='prepaid_cutoff_not_guaranteed':
        v.need(v.digest(packet) == FRESH_HEADLINE_PACKET_SHA256,'Only the separately scoped fresh homepage-title packet is eligible')
    credentials=v.funding_check(config,now,env)
    key=cache_key(packet,config);target=state/('accepted-v2' if live else 'fixture-v2')/(key+'.json');held=state/'held'/(key+'.json')
    from scripts.scarb_packet_consumption_candidate import protected_root
    expected_state=protected_root() if live else state
    if live:v.need(state.is_dir() and state.resolve()==expected_state.resolve(),"Missing or wrong protected state root")
    with v.exclusive(state):
        v.need(not (state/'held'/(v.cache_key(packet,config)+'.json')).exists(),'Original v1 attempt remains held')
        if target.exists():
            receipt=json.loads(target.read_text());receipt_check(receipt,packet,config,fixture=not live);return receipt
        from scripts.scarb_packet_consumption_candidate import assert_unconsumed
        assert_unconsumed(state,{packet['id']:v.digest(packet)},expected_root=expected_state)
        v.need(not held.exists(),'Prior v2 attempt remains held')
        ledger_path=state/'usage.json';ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'months':{}}
        month=now.strftime('%Y-%m');spent=ledger['months'].get(month,0);pilot=ledger.get('paid_pilot_usd',0)
        v.need(all(type(n) in (int,float) and math.isfinite(n) and n>=0 for n in (spent,pilot)),'Invalid fixture ledger')
        bound,reserve=reservation_bound(packet,config);cap=v.paid_pilot_cap(config)
        v.need(spent+reserve<=config['month_cap_usd'],'Monthly fixture reservation exceeded')
        if cap is not None:v.need(pilot+reserve<=cap,'Pilot fixture reservation exceeded')
        ledger['months'][month]=round(spent+reserve,6)
        if cap is not None:ledger['paid_pilot_usd']=round(pilot+reserve,6)
        v.atomic_json(ledger_path,ledger);journal={'key':key,'packet_sha256':v.digest(packet),'status':'held','origin':'openai-api-reviewed' if live else 'test-fixture','transport_attempts':0,'response_received':False,'stage':'request-preparation'};v.atomic_json(held,journal)
        usage=[]
        try:
            for stage in ('author','review'):
                body=author_request(packet,config) if stage=='author' else review_request(packet,result,config)
                v.need(len(v.encoded(body))<=48000,'Fixture request exceeds reserved envelope')
                journal.update(stage=stage+'-request',transport_attempts=journal['transport_attempts']+1,response_received=False);v.atomic_json(held,journal)
                raw=transport(body,credentials) if live else transport.exchange(body)
                journal.update(stage=stage+'-validation',response_received=True);v.atomic_json(held,journal)
                answer,tokens=v.unpack(raw)
                usage.append({'stage':stage,'model':body['model'],**tokens})
                if tokens['input_tokens']>bound or tokens['output_tokens']>2000:
                    ledger['months'][month]=config['month_cap_usd']
                    if cap is not None:ledger['paid_pilot_usd']=cap
                    v.atomic_json(ledger_path,ledger)
                    raise v.VoiceError('Provider usage exceeded reservation; further calls are held')
                if stage=='author':result=answer;assemble(packet,result)
                else:
                    review=answer; journal['review_dimensions']=review_dimensions(review)
                    v.review_check(review)
        except (v.VoiceError,OSError,ValueError,KeyError,TypeError) as error:
            journal.update(**v.diagnostic_outcome(error));journal['completed_usage_stages']=usage;v.atomic_json(held,journal);raise
        receipt=fixture_accept(packet,result,review,config);receipt.update(packet_sha256=v.digest(packet),usage=usage,generated_at=now.isoformat(),origin='openai-api-reviewed' if live else 'test-fixture')
        receipt['sha256']=v.digest(receipt);receipt_check(receipt,packet,config,fixture=not live)
        v.atomic_json(target,receipt)
        # Keep conservative fixture reservation, never refund a held attempt.
        held.unlink();return receipt


def fixture_receipt_check(receipt,packet,config):
    return receipt_check(receipt,packet,config,fixture=True)

def generate_fixture(packet,config,state,*,transport,now):
    f=config['funding']
    env={'SCARB_AI_ENABLE':'1','OPENAI_API_KEY':'fixture-not-a-key','OPENAI_ORG_ID':f['organization'],'OPENAI_PROJECT_ID':f['project']}
    return _generate(packet,config,state,transport=transport,now=now,env=env)

def generate(packet,config,state,*,enable_v2=False,approved_packet_sha256=(),env=None,now=None):
    """Explicitly disabled by default. No CLI or environment-only activation."""
    v.need(enable_v2 is True,'V2 live dispatch is disabled')
    v.need(v.digest(packet) in approved_packet_sha256,'V2 packet lacks explicit scoped approval')
    # Existing private paid funding whitelist remains a second independent check.
    v.need(env is not None,'Explicit protected environment is required')
    return _generate(packet,config,state,transport=v.api_request,now=now or v.dt.datetime.now(v.dt.timezone.utc),env=env,live=True)

def compile_catalogue(packets,config,state):
    """Same public reader schema; v2 private provenance is verified, never inferred."""
    import json
    v.check_config(config);entries={}
    for packet in packets:
        schema(packet);v.need(packet['id'] not in entries,'Duplicate request ID')
        path=state/'accepted-v2'/(cache_key(packet,config)+'.json')
        v.need(path.is_file(),'Missing accepted v2 translation')
        receipt=json.loads(path.read_text(encoding='utf-8'))
        text=receipt_check(receipt,packet,config)
        entries[packet['id']]={'text':text,'packet_sha256':v.digest(packet),'receipt_sha256':receipt['sha256'],'origin':receipt['origin']}
    v.need(bool(entries),'No translated entries')
    return {'version':v.VERSION,'entries':entries}

def verify_catalogue(packets,config,state,artifact):
    import json
    v.need(artifact.is_file() and artifact.stat().st_size<=10*1024*1024,'Candidate catalogue missing or oversized')
    v.need(v.encoded(json.loads(artifact.read_text(encoding='utf-8')))==v.encoded(compile_catalogue(packets,config,state)),'Public catalogue differs from accepted v2 receipts')
    return True
