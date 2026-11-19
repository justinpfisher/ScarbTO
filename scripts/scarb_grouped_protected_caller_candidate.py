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
SOURCES=frozenset('scarb_ai_voice scarb_ai_fact_slots scarb_grouped_runner_candidate scarb_grouped_context_candidate scarb_rss_contexts scarb_grouped_provenance_candidate scarb_group21_source_compatibility scarb_grouped_fixture_envelope scarb_grouped_projection_seam scarb_grouped_membership_candidate scarb_packet_consumption_candidate scarb_legacy_consumption_bindings scarb_shared_cost_proof_candidate scarb_grouped_protected_caller_candidate'.split())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def source_pins():return {name:sha(ROOT/'scripts'/(name+'.py')) for name in sorted(SOURCES)}|{'community_validation_context_producer':sha(ROOT/'scripts/scarb_community_validation_contexts.mjs'),'finding_context_producer':sha(ROOT/'scripts/scarb_finding_contexts.mjs'),'selected_calls_context_producer':sha(ROOT/'scripts/scarb_selected_calls_contexts.mjs'),'launcher_python':sha(ROOT/'scripts/launch_scarb_grouped_candidate.py'),'launcher_powershell':sha(ROOT/'scripts/run-scarb-grouped-candidate.ps1')}

def _invoke(manifest_path,approved_manifest_sha256,*,state,expected_state,env,transport,now,completed_at,production=False,preflight=False):
 # Same ordering: immutable manifest/code/config/packet/root identity, then
 # funding+credential identity, then shared reservation and bounded dispatch.
 if not production:v.need(type(transport) in (f.FixtureTransport,FixedResponsesInjected),'Only isolated injected transport')
 else:launcher_preflight(approved_manifest_sha256)
 state=Path(state);v.need(state.is_dir() and state.resolve()==Path(expected_state).resolve() and (production or (state/'SYNTHETIC_GROUPED_ACCOUNTING_ONLY').is_file()),'Wrong isolated state root')
 manifest_path=Path(manifest_path);v.need(sha(manifest_path)==approved_manifest_sha256,'Exact manifest changed')
 manifest=json.loads(manifest_path.read_text(encoding='utf8'))
 prefix='scarb-grouped-wrapper-production-' if production else 'scarb-grouped-wrapper-fixture-'
 versioned=manifest.get('version')==prefix+'2'
 prompt_version=emitter.c.contract.CITATION_PROMPT if versioned else emitter.c.contract.LEGACY_PROMPT
 v.need(set(manifest)=={'version','code_sha256','config_path','config_sha256','requests_path','requests_sha256','packet_bindings','models','maximum_reservation_nusd','prices','state_root','pilot_cap_nusd'}|({'prompt_version'} if versioned else set()) and manifest['version'] in (prefix+'1',prefix+'2'),'Wrong wrapper manifest')
 if versioned:v.need(manifest['prompt_version']==prompt_version,'Wrong wrapper prompt version')
 v.need(manifest['code_sha256']==source_pins(),'Imported code changed')
 v.need(Path(manifest['state_root']).resolve()==state.resolve(),'Manifest state root changed')
 config_path=Path(manifest['config_path']);requests_path=Path(manifest['requests_path'])
 v.need(sha(config_path)==manifest['config_sha256'] and sha(requests_path)==manifest['requests_sha256'],'Exact config or requests changed')
 config=json.loads(config_path.read_text(encoding='utf-8'));packets=json.loads(requests_path.read_text(encoding='utf-8'))
 v.need(len(packets) in (2,3) and {p['id']:v.digest(p) for p in packets}==manifest['packet_bindings'],'Wrong exact two-or-three-packet scope')
 models={'author':config['author_model'],'reviewer':config['reviewer_model']};v.need(models==manifest['models'] and models=={'author':'gpt-6-luna','reviewer':'gpt-6.1-terra'},'Model scope changed')
 # Common validation is shared; this pinned route validates its exact cumulative
 # funding cap below rather than the generic initial-pilot cap. No fallback.
 v.check_config_common(config)
 # Only a sentinel, supplied by test, may reach funding_check. Never read os.env.
 v.need(production or env.get('OPENAI_API_KEY')=='fixture-not-a-key','No real credentials accepted by offline caller')
 check_env={'SCARB_AI_ENABLE':'1','OPENAI_API_KEY':'fixture-not-a-key','OPENAI_ORG_ID':ORG,'OPENAI_PROJECT_ID':PROJECT} if production else env
 credentials=exact_prepaid_funding(config,manifest,now,check_env)
 funding=config['funding']
 cap=amounts.amount(funding['pilot_cap_usd']);v.need(cap<=amounts.amount(config['month_cap_usd']),'Pilot exceeds month cap')
 prices={model:{'input_nusd_per_million':amounts.amount(v.MODELS[model][0]),'output_nusd_per_million':amounts.amount(v.MODELS[model][1])} for model in models.values()}
 v.need(prices==manifest['prices'],'Pinned model prices differ')
 contexts=emitter.c.current_contexts(packets);body=emitter.c.context_prompts(packets,models,contexts,prompt_version=prompt_version)
 def cost(model,i,o):return (i*prices[model]['input_nusd_per_million']+o*prices[model]['output_nusd_per_million']+999999)//1000000
 reserve=cost(models['author'],len(v.encoded(body)),2000)+cost(models['reviewer'],48000,2000)
 v.need(type(manifest['maximum_reservation_nusd']) is int and reserve<=manifest['maximum_reservation_nusd']<=60000000,'Exact reservation exceeded')
 observation={'observed_at':funding['verified_at'],'expires_at':funding['expires_at'],'balance_nusd':amounts.amount(funding['remaining_usd']),'auto_recharge_disabled':funding['auto_recharge_disabled'],'organization':credentials['organization'],'project':credentials['project'],'cap_nusd':cap}
 # The unchanged emitter uses FixtureTransport.exchange. Its requests retain
 # request_body's fixed model, no tools/store/background and bounded output.
 # The actual fixed api_request transport remains uncalled in this adapter.
 if preflight:return {'ready_for_protected_lookup':True,'manifest_sha256':approved_manifest_sha256}
 if production:
  credentials=exact_prepaid_funding(config,manifest,now,env() if callable(env) else env)
  transport=ProtectedResponses(credentials)
 return emitter._run_sequence(state,packets,models,observation,prices,transport=transport,started_at=now.isoformat(),completed_at=completed_at,production=production,approved_manifest_sha256=approved_manifest_sha256,prompt_version=prompt_version)


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

def launcher_preflight(manifest_sha256=None):
 # Exact expected digest is supplied separately by the protected launcher
 # approval argument. Never embed it in the source bytes the manifest pins.
 from scripts.scarb_packet_consumption_candidate import HEX
 v.need(LIVE_GROUPED_ENABLED and isinstance(manifest_sha256,str) and HEX.fullmatch(manifest_sha256),'Grouped protected launcher is not activated; no credential lookup allowed')


class ProtectedResponses:
 def __init__(self,credentials):self.credentials=credentials
 def exchange(self,body):return v.api_request(body,self.credentials)

def invoke_fixture(*args,**kwargs):return _invoke(*args,**kwargs)

def invoke_protected(manifest_path,approved_manifest_sha256,*,state,env_loader,now,preflight=False):
 launcher_preflight(approved_manifest_sha256)
 from scripts.scarb_packet_consumption_candidate import protected_root
 return _invoke(manifest_path,approved_manifest_sha256,state=state,expected_state=protected_root(),env=env_loader,transport=None,now=now,completed_at=None,production=True,preflight=preflight)
