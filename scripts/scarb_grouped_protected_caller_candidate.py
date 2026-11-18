"""Offline counterpart of the protected exact-manifest wrapper.
No CLI, DPAPI lookup or live enable flag. Existing production caller unchanged.
"""
import json,hashlib
from pathlib import Path
from scripts import scarb_ai_voice as v,scarb_ai_fact_slots as f
from scripts import scarb_grouped_runner_candidate as emitter
from scripts import scarb_shared_cost_proof_candidate as amounts
LIVE_GROUPED_ENABLED=False
ORG='org-EIn1HXt0x19rnOSvte7dVrB9'
PROJECT='proj_ZiSvyeNLotSbqtH2vDEKqNxx'
ROOT=Path(__file__).resolve().parents[1]
SOURCES=frozenset('scarb_ai_voice scarb_ai_fact_slots scarb_grouped_runner_candidate scarb_grouped_context_candidate scarb_grouped_provenance_candidate scarb_grouped_fixture_envelope scarb_grouped_projection_seam scarb_grouped_membership_candidate scarb_packet_consumption_candidate scarb_legacy_consumption_bindings scarb_shared_cost_proof_candidate scarb_grouped_protected_caller_candidate'.split())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def source_pins():return {name:sha(ROOT/'scripts'/(name+'.py')) for name in sorted(SOURCES)}|{'launcher_python':sha(ROOT/'scripts/launch_scarb_grouped_candidate.py'),'launcher_powershell':sha(ROOT/'scripts/run-scarb-grouped-candidate.ps1')}

def invoke_fixture(manifest_path,approved_manifest_sha256,*,state,expected_state,env,transport,now,completed_at):
 # Same ordering: immutable manifest/code/config/packet/root identity, then
 # funding+credential identity, then shared reservation and bounded dispatch.
 v.need(type(transport) in (f.FixtureTransport,FixedResponsesInjected),'Only isolated injected transport')
 state=Path(state);v.need(state.is_dir() and state.resolve()==Path(expected_state).resolve() and (state/'SYNTHETIC_GROUPED_ACCOUNTING_ONLY').is_file(),'Wrong isolated state root')
 manifest_path=Path(manifest_path);v.need(sha(manifest_path)==approved_manifest_sha256,'Exact manifest changed')
 manifest=json.loads(manifest_path.read_text(encoding='utf8'))
 v.need(set(manifest)=={'version','code_sha256','config_path','config_sha256','requests_path','requests_sha256','packet_bindings','models','maximum_reservation_nusd','prices','state_root','pilot_cap_nusd'} and manifest['version']=='scarb-grouped-wrapper-fixture-1','Wrong wrapper manifest')
 v.need(manifest['code_sha256']==source_pins(),'Imported code changed')
 v.need(Path(manifest['state_root']).resolve()==state.resolve(),'Manifest state root changed')
 config_path=Path(manifest['config_path']);requests_path=Path(manifest['requests_path'])
 v.need(sha(config_path)==manifest['config_sha256'] and sha(requests_path)==manifest['requests_sha256'],'Exact config or requests changed')
 config=json.loads(config_path.read_text());packets=json.loads(requests_path.read_text())
 v.need(len(packets)==2 and {p['id']:v.digest(p) for p in packets}==manifest['packet_bindings'],'Wrong exact two-packet scope')
 models={'author':config['author_model'],'reviewer':config['reviewer_model']};v.need(models==manifest['models'],'Model scope changed')
 v.check_config(config)
 # Only a sentinel, supplied by test, may reach funding_check. Never read os.env.
 v.need(env.get('OPENAI_API_KEY')=='fixture-not-a-key','No real credentials accepted by offline caller')
 credentials=exact_prepaid_funding(config,manifest,now,env)
 funding=config['funding']
 cap=amounts.amount(funding['pilot_cap_usd']);v.need(cap<=amounts.amount(config['month_cap_usd']),'Pilot exceeds month cap')
 prices={model:{'input_nusd_per_million':amounts.amount(v.MODELS[model][0]),'output_nusd_per_million':amounts.amount(v.MODELS[model][1])} for model in models.values()}
 v.need(prices==manifest['prices'],'Pinned model prices differ')
 contexts=emitter.c.current_contexts(packets);body=emitter.c.context_prompts(packets,models,contexts)
 def cost(model,i,o):return (i*prices[model]['input_nusd_per_million']+o*prices[model]['output_nusd_per_million']+999999)//1000000
 reserve=cost(models['author'],len(v.encoded(body)),2000)+cost(models['reviewer'],48000,2000)
 v.need(type(manifest['maximum_reservation_nusd']) is int and reserve<=manifest['maximum_reservation_nusd']<=60000000,'Exact reservation exceeded')
 observation={'observed_at':funding['verified_at'],'expires_at':funding['expires_at'],'balance_nusd':amounts.amount(funding['remaining_usd']),'auto_recharge_disabled':funding['auto_recharge_disabled'],'organization':credentials['organization'],'project':credentials['project'],'cap_nusd':cap}
 # The unchanged emitter uses FixtureTransport.exchange. Its requests retain
 # request_body's fixed model, no tools/store/background and bounded output.
 # The actual fixed api_request transport remains uncalled in this adapter.
 return emitter.run_fixture(state,packets,models,observation,prices,transport=transport,started_at=now.isoformat(),completed_at=completed_at)


def exact_prepaid_funding(config,manifest,now,env):
 """Exact scoped successor of prior prepaid gate; never claim no postpaid risk."""
 funding=config['funding']
 expected={'kind','organization','project','verified_at','expires_at','remaining_usd','auto_recharge_disabled','pilot_cap_usd','billing_mode','pilot_request_sha256'}
 v.need(set(funding)==expected and funding['kind']=='existing_paid_api_credits' and funding['billing_mode']=='prepaid_cutoff_not_guaranteed','Exact existing prepaid billing mode required')
 v.need(funding['organization']==ORG and funding['project']==PROJECT and funding['auto_recharge_disabled'] is True,'Dedicated prepaid identity/auto-recharge mismatch')
 v.need(funding['pilot_request_sha256']==list(manifest['packet_bindings'].values()),'Exact prepaid scope mismatch')
 cap=amounts.amount(funding['pilot_cap_usd'])
 v.need(type(manifest['pilot_cap_nusd']) is int and cap==manifest['pilot_cap_nusd'] and 0<cap<=amounts.amount(config['month_cap_usd']),'Exact cumulative prepaid cap mismatch')
 age=now-v.instant(funding['verified_at'])
 v.need(v.dt.timedelta(0)<=age<=v.dt.timedelta(hours=1) and now<v.instant(funding['expires_at']),'Fresh prepaid balance observation required')
 v.need(amounts.amount(funding['remaining_usd'])>=5_000_000_000+cap,'Prepaid buffer insufficient')
 v.need(config['enabled'] is True and env.get('SCARB_AI_ENABLE')=='1','Generation disabled')
 values={'key':env.get('OPENAI_API_KEY'),'organization':env.get('OPENAI_ORG_ID'),'project':env.get('OPENAI_PROJECT_ID')}
 v.need(all(v.plain(x,1000) for x in values.values()) and values['organization']==ORG and values['project']==PROJECT,'Protected identity missing/mismatched')
 return values

class FixedResponsesInjected:
 """The production transport function with an explicitly injected test opener.
 This test adapter never resolves credentials or installs a global opener.
 """
 def __init__(self,credentials,opener):
  v.need(credentials.get('key')=='fixture-not-a-key','Only synthetic credentials accepted')
  self.credentials=credentials;self.opener=opener;self.calls=[]
 def exchange(self,body):
  from unittest.mock import patch
  self.calls.append(body)
  with patch.object(v.urllib.request,'build_opener',return_value=self.opener):
   return v.api_request(body,self.credentials)

def launcher_preflight():
 v.need(LIVE_GROUPED_ENABLED,'Grouped protected launcher is not activated; no credential lookup allowed')
