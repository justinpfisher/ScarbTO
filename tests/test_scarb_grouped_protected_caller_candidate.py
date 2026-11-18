import unittest,tempfile,json,datetime,copy
from pathlib import Path
from unittest.mock import patch
from scripts import scarb_grouped_protected_caller_candidate as w
from tests.test_scarb_grouped_runner_candidate import RunnerTests
class ProtectedCallerTests(unittest.TestCase):
 def prepare(self,state):
  RunnerTests.setUpClass();t=RunnerTests();_,_,transport=t.inputs(state)
  w.emitter.save(state,'usage.json',{'months':{},'paid_pilot_usd':0})
  now=datetime.datetime(2030,1,1,3,1,tzinfo=datetime.timezone.utc)
  config={'enabled':True,'author_model':'gpt-6-luna','reviewer_model':'gpt-6.1-terra','month_cap_usd':1,'funding':{'kind':'existing_paid_api_credits','organization':w.ORG,'project':w.PROJECT,'verified_at':'2030-01-01T03:00:00Z','expires_at':'2030-01-01T04:00:00Z','remaining_usd':67,'auto_recharge_disabled':True,'billing_mode':'prepaid_cutoff_not_guaranteed','pilot_request_sha256':[w.v.digest(x) for x in t.packets],'pilot_cap_usd':.25}}
  env={'SCARB_AI_ENABLE':'1','OPENAI_API_KEY':'fixture-not-a-key','OPENAI_ORG_ID':w.ORG,'OPENAI_PROJECT_ID':w.PROJECT}
  cp=state/'fixture-config.json';rp=state/'fixture-requests.json';w.emitter.save(state,cp.name,config);w.emitter.save(state,rp.name,t.packets)
  models={'author':config['author_model'],'reviewer':config['reviewer_model']}
  prices={m:{'input_nusd_per_million':w.amounts.amount(w.v.MODELS[m][0]),'output_nusd_per_million':w.amounts.amount(w.v.MODELS[m][1])} for m in models.values()}
  manifest={'version':'scarb-grouped-wrapper-fixture-1','code_sha256':w.source_pins(),'config_path':str(cp),'config_sha256':w.sha(cp),'requests_path':str(rp),'requests_sha256':w.sha(rp),'packet_bindings':{p['id']:w.v.digest(p) for p in t.packets},'models':models,'maximum_reservation_nusd':60000000,'prices':prices,'state_root':str(state.resolve()),'pilot_cap_nusd':250000000}
  mp=state/'manifest-fixture.json';w.emitter.save(state,mp.name,manifest)
  return mp,env,transport,now
 def invoke(self,state,prepared):
  mp,env,t,now=prepared
  return w.invoke_fixture(mp,w.sha(mp),state=state,expected_state=state,env=env,transport=t,now=now,completed_at='2030-01-01T03:01:05Z')
 def test_exact_gates_to_emitter_no_network_and_no_retry(self):
  with tempfile.TemporaryDirectory() as d,patch.object(w.v,'api_request',side_effect=AssertionError('No network')) as api:
   state=Path(d);prepared=self.prepare(state);result=self.invoke(state,prepared)
   self.assertEqual(result['calls'],2);api.assert_not_called()
   with self.assertRaises(w.v.VoiceError):self.invoke(state,prepared)
   self.assertEqual(len(prepared[2].calls),2)
 def test_code_config_scope_root_checks_before_funding_and_debit(self):
  for field in ['code','config','scope','root','reserve','funding']:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
    state=Path(d);prepared=self.prepare(state);mp=prepared[0];m=json.loads(mp.read_text())
    if field=='code':m['code_sha256']['scarb_ai_voice']='0'*64
    elif field=='config':m['config_sha256']='0'*64
    elif field=='scope':m['packet_bindings']={}
    elif field=='root':m['state_root']=str(state/'wrong')
    elif field=='reserve':m['maximum_reservation_nusd']=1
    else:prepared[1]['OPENAI_PROJECT_ID']='wrong'
    w.emitter.save(state,mp.name,m);before=(state/'usage.json').read_bytes()
    with self.assertRaises(w.v.VoiceError):self.invoke(state,prepared)
    self.assertEqual(prepared[2].calls,[]);self.assertEqual((state/'usage.json').read_bytes(),before)
    self.assertFalse((state/'grouped-runs').exists())
 def test_injected_failure_is_not_retried(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);prepared=list(self.prepare(state));prepared[2]=w.f.FixtureTransport([w.v.TransportFailure('transport-timeout',None)])
   with self.assertRaises(w.v.TransportFailure):self.invoke(state,prepared)
   self.assertEqual(len(prepared[2].calls),1)
   with self.assertRaises(w.v.VoiceError):self.invoke(state,prepared)
   self.assertEqual(len(prepared[2].calls),1)


 def test_existing_responses_boundary_isolated_injection(self):
  from unittest.mock import MagicMock
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);mp,env,t,now=self.prepare(state)
   config=json.loads((state/'fixture-config.json').read_text());credentials=w.exact_prepaid_funding(config,json.loads(mp.read_text()),now,env)
   packets=json.loads((state/'fixture-requests.json').read_text());models={'author':config['author_model'],'reviewer':config['reviewer_model']}
   request=w.emitter.c.context_prompts(packets,models,w.emitter.c.current_contexts(packets))
   boundary=MagicMock();stream=MagicMock();stream.__enter__.return_value=stream;stream.read.return_value=w.v.encoded(t.responses[0]);boundary.open.return_value=stream
   with patch.object(w.v.urllib.request,'build_opener',return_value=boundary) as build:
    result=w.v.api_request(request,credentials)
   self.assertEqual(result,t.responses[0]);build.assert_called_once_with(w.v.NoRedirect)
   args,kwargs=boundary.open.call_args;self.assertEqual(args[0].full_url,w.v.ENDPOINT);self.assertEqual(kwargs['timeout'],60)
   stream.read.assert_called_once_with(1024*1024+1)


 def test_exact_prepaid_launcher_to_actual_transport_emitter_offline(self):
  from unittest.mock import MagicMock
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);mp,env,t,now=self.prepare(state)
   config=json.loads((state/'fixture-config.json').read_text());credentials=w.exact_prepaid_funding(config,json.loads(mp.read_text()),now,env)
   opener=MagicMock();streams=[]
   for raw in t.responses:
    stream=MagicMock();stream.__enter__.return_value=stream;stream.read.return_value=w.v.encoded(raw);streams.append(stream)
   opener.open.side_effect=streams
   injected=w.FixedResponsesInjected(credentials,opener)
   result=self.invoke(state,(mp,env,injected,now));self.assertEqual(result['calls'],2)
   self.assertEqual(opener.open.call_count,2)
   for args,kwargs in opener.open.call_args_list:
    self.assertEqual(args[0].full_url,w.v.ENDPOINT);self.assertEqual(kwargs['timeout'],60)
   for stream in streams:stream.read.assert_called_once_with(1024*1024+1)
   self.assertEqual(w.emitter.recover_fixture(state,RunnerTests.packets)['status'],'completed')
   with self.assertRaises(w.v.VoiceError):self.invoke(state,(mp,env,injected,now))
   self.assertEqual(opener.open.call_count,2)
 def test_postpaid_inference_expired_funding_and_launcher_activation_refused(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);mp,env,t,now=self.prepare(state);m=json.loads(mp.read_text());config=json.loads((state/'fixture-config.json').read_text())
   for mode in ['postpaid','expired','scope','cap']:
    changed=copy.deepcopy(config)
    if mode=='postpaid':changed['funding']['postpaid_disabled']=True
    elif mode=='expired':changed['funding']['expires_at']='2029-12-31T00:00:00Z'
    elif mode=='scope':changed['funding']['pilot_request_sha256']=[]
    else:changed['funding']['pilot_cap_usd']=.26
    with self.assertRaises(w.v.VoiceError):w.exact_prepaid_funding(changed,m,now,env)
   with self.assertRaises(w.v.VoiceError):w.launcher_preflight()
   self.assertFalse(w.LIVE_GROUPED_ENABLED)

class DisabledProductionBranchTests(ProtectedCallerTests):
 def test_default_refuses_before_credentials_and_dispatch(self):
  from unittest.mock import Mock
  loader=Mock(side_effect=AssertionError('credential access'))
  with patch.object(w.v,'api_request',side_effect=AssertionError('network')) as api:
   with self.assertRaises(w.v.VoiceError):w.invoke_protected('nonexistent','0'*64,state='nonexistent',env_loader=loader,now=w.v.dt.datetime.now(w.v.dt.timezone.utc))
   loader.assert_not_called();api.assert_not_called()
  self.assertFalse(w.LIVE_GROUPED_ENABLED);self.assertFalse(hasattr(w,'LIVE_DISPATCH_MANIFEST_SHA256'))
 def test_nonfixture_branch_in_memory_gate_fake_credentials_transport_only(self):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);mp,env,t,_=self.prepare(state);now=w.v.dt.datetime.now(w.v.dt.timezone.utc)
   config=json.loads((state/'fixture-config.json').read_text());config['funding']['verified_at']=(now-w.v.dt.timedelta(minutes=1)).isoformat();config['funding']['expires_at']=(now+w.v.dt.timedelta(minutes=30)).isoformat()
   w.emitter.save(state,'fixture-config.json',config)
   m=json.loads(mp.read_text());m['version']='scarb-grouped-wrapper-production-1';m['config_sha256']=w.sha(state/'fixture-config.json');w.emitter.save(state,mp.name,m);digest=w.sha(mp)
   # Scoped test patches only. No private on-disk enablement or real key lookup.
   with patch.object(w,'LIVE_GROUPED_ENABLED',True),patch('scripts.scarb_packet_consumption_candidate.protected_root',lambda:state),patch.object(w.v,'api_request',side_effect=t.responses) as api:
    calls=[]
    def loader():calls.append('lookup');return env
    preflight=w.invoke_protected(mp,digest,state=state,env_loader=loader,now=now,preflight=True)
    self.assertTrue(preflight['ready_for_protected_lookup']);self.assertEqual(calls,[]);api.assert_not_called()
    result=w.invoke_protected(mp,digest,state=state,env_loader=loader,now=now)
    self.assertEqual(result['calls'],2);self.assertEqual(calls,['lookup']);self.assertEqual(api.call_count,2)
    root=Path(result['root']);self.assertTrue((root/'candidate-pin.json').is_file());self.assertFalse((root/'fixture-pin.json').exists())
    self.assertFalse(w.emitter.verifier.TRUSTED_GROUPED_RUNS)
    with self.assertRaises(w.v.VoiceError):w.invoke_protected(mp,digest,state=state,env_loader=loader,now=now)
    self.assertEqual(api.call_count,2)
   self.assertFalse(w.LIVE_GROUPED_ENABLED);self.assertFalse(hasattr(w,'LIVE_DISPATCH_MANIFEST_SHA256'))

class ExternalPinMaterializationTests(unittest.TestCase):
 def test_materialized_enabled_source_has_external_non_circular_pin(self):
  import subprocess,io,zipfile,shutil,os
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);repo=base/'source';repo.mkdir()
   archive=subprocess.check_output(['git','archive','--format=zip','HEAD'],cwd=w.ROOT)
   with zipfile.ZipFile(io.BytesIO(archive)) as z:z.extractall(repo)
   for name in subprocess.check_output(['git','diff','--name-only'],cwd=w.ROOT,text=True).splitlines():
    target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(w.ROOT/name,target)
   candidate=repo/'scripts/scarb_grouped_protected_caller_candidate.py'
   source=candidate.read_text(encoding='utf8');self.assertIn('LIVE_GROUPED_ENABLED=False',source)
   candidate.write_text(source.replace('LIVE_GROUPED_ENABLED=False','LIVE_GROUPED_ENABLED=True'),encoding='utf8')
   local=base/'local';state=local/'ScarbTO/voice-private';state.mkdir(parents=True)
   mp,env,t,_=ProtectedCallerTests().prepare(state)
   now=w.v.dt.datetime.now(w.v.dt.timezone.utc);config=json.loads((state/'fixture-config.json').read_text())
   config['funding']['verified_at']=(now-w.v.dt.timedelta(minutes=1)).isoformat();config['funding']['expires_at']=(now+w.v.dt.timedelta(minutes=20)).isoformat();w.emitter.save(state,'fixture-config.json',config)
   pins=json.loads(subprocess.check_output([str(Path(os.sys.executable)),'-I','-S','-c',"import sys,json;sys.path.insert(0,"+repr(str(repo))+");from scripts.scarb_grouped_protected_caller_candidate import source_pins;print(json.dumps(source_pins()))"],text=True))
   manifest=json.loads(mp.read_text());manifest.update(version='scarb-grouped-wrapper-production-1',code_sha256=pins,config_sha256=w.sha(state/'fixture-config.json'));w.emitter.save(state,mp.name,manifest)
   external_pin=w.sha(mp) # retained separately, never written into pinned source
   cmd=[os.sys.executable,'-I','-S',str(repo/'scripts/launch_scarb_grouped_candidate.py'),'--preflight-only','--manifest',str(mp),'--manifest-sha256',external_pin,'--state',str(state)]
   child_env={**os.environ,'LOCALAPPDATA':str(local)}
   # No credentials exist in the child; preflight must not ask for any.
   for name in ['OPENAI_API_KEY','OPENAI_ORG_ID','OPENAI_PROJECT_ID']:child_env.pop(name,None)
   before=(state/'usage.json').read_bytes();result=subprocess.run(cmd,env=child_env,capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr);self.assertIn('preflight-ready',result.stdout)
   self.assertEqual(w.sha(mp),external_pin);self.assertEqual(w.sha(candidate),pins['scarb_grouped_protected_caller_candidate'])
   manifest['maximum_reservation_nusd']=1;w.emitter.save(state,mp.name,manifest)
   tampered=subprocess.run(cmd,env=child_env,capture_output=True,text=True)
   self.assertNotEqual(tampered.returncode,0);self.assertIn('Exact manifest changed',tampered.stderr)
   self.assertEqual((state/'usage.json').read_bytes(),before);self.assertFalse((state/'grouped-runs').exists())
   self.assertFalse(w.LIVE_GROUPED_ENABLED);self.assertFalse(hasattr(w,'LIVE_DISPATCH_MANIFEST_SHA256'))
