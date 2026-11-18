"""Isolated launcher entry. Production remains disabled before credential access."""
import argparse,sys,json,datetime,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import scarb_grouped_protected_caller_candidate as caller
p=argparse.ArgumentParser();p.add_argument('--preflight-only',action='store_true');p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--state',required=True);p.add_argument('--fixture-responses');p.add_argument('--fixture-responses-sha256');p.add_argument('--fixture-now');p.add_argument('--fixture-completed-at');args=p.parse_args()
if not args.fixture_responses:
 result=caller.invoke_protected(args.manifest,args.manifest_sha256,state=args.state,env_loader=lambda:dict(os.environ),now=caller.v.dt.datetime.now(caller.v.dt.timezone.utc),preflight=args.preflight_only)
 print(json.dumps({'outcome':'preflight-ready' if args.preflight_only else 'review-recorded-not-published','production_qualified':False}))
 raise SystemExit(0)
caller.v.need(caller.sha(args.fixture_responses)==args.fixture_responses_sha256,'Injected response bytes changed')
transport=caller.f.FixtureTransport(json.loads(Path(args.fixture_responses).read_text(encoding='utf8')))
env={'OPENAI_API_KEY':'fixture-not-a-key','SCARB_AI_ENABLE':'1','OPENAI_ORG_ID':caller.ORG,'OPENAI_PROJECT_ID':caller.PROJECT}
result=caller.invoke_fixture(args.manifest,args.manifest_sha256,state=args.state,expected_state=args.state,env=env,transport=transport,now=caller.v.instant(args.fixture_now),completed_at=args.fixture_completed_at)
print(json.dumps({'outcome':'synthetic-completed','calls':result['calls'],'production_qualified':False}))
