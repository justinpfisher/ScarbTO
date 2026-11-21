"""Existing publication check for a newly generated index, never a retained one."""
import hashlib,json,re,sys
from datetime import date,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.build_weekly_brief import _render_index

def verify_generated_index(markup,manifest,render=_render_index):
    matches=re.findall(r'<main data-scarb-period-start="(\d{4}-\d{2}-\d{2})" data-scarb-period-end="(\d{4}-\d{2}-\d{2})" data-scarb-has-current="(true|false)">',markup)
    if len(matches)!=1:raise ValueError('New index needs its exact generation period')
    start,end,flag=matches[0];start,end=date.fromisoformat(start),date.fromisoformat(end);has_current=flag=='true'
    if start.weekday()!=0 or end-start!=timedelta(days=6):raise ValueError('Invalid generated index period')
    if any(e['period_start']==start.isoformat() for e in manifest['editions'])!=has_current:raise ValueError('Index availability disagrees with issued editions')
    expected=render(manifest,start,end,has_current).decode('utf-8')
    if markup.replace('\r\n','\n')!=expected:raise ValueError('Generated index differs from accepted copy and factual archive manifest')
    return True

def verify_retained_generated_index(markup, manifest, catalogue, expected):
    # Reconstruct only with the accepted catalogue that accompanied these
    # committed historical bytes, not the newly installed/current catalogue.
    # The caller must already have proved exact committed archive equality.
    from scripts import scarb_accepted_copy as accepted
    previous,loaded=accepted._CURRENT,accepted._LOADED
    try:
        accepted._CURRENT=accepted.accepted_resolver(catalogue,expected)
        accepted._LOADED=True
        return verify_generated_index(markup,manifest)
    finally:
        accepted._CURRENT,accepted._LOADED=previous,loaded


# The last pre-gateway index is not new copy. These exact index and
# registry digests were reproduced from the renderer at its publishing commit.
# No other historical version, mutation or missing catalogue is accepted here.
_PRE_GATEWAY_INDEX = '08af44cd8ba935a9752bf665d2100ad898668e61'
_PRE_GATEWAY_SHA256 = '6c8b26fca32becd84967f9c330488e39881ff7e18b60aca8bc63909c39d03bd6'

def verify_pre_gateway_index(revision, index_bytes, registry_bytes, committed_registry_bytes):
    if (revision != _PRE_GATEWAY_INDEX or
        hashlib.sha256(index_bytes).hexdigest() != _PRE_GATEWAY_SHA256 or
        registry_bytes != committed_registry_bytes):
        raise ValueError('Retained pre-gateway index or its exact archive registry changed')
    return True

def historical_inputs():
    import subprocess
    def git(*args):
        result=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=False)
        if result.returncode:raise ValueError('Committed index provenance unavailable')
        return result.stdout
    # In the existing PR reconciliation, the retained archive comes from
    # the reviewed main side of the merge; the draft HEAD can be stale.
    pending=subprocess.run(['git','rev-parse','--verify','MERGE_HEAD'],cwd=ROOT,capture_output=True)
    baseline=pending.stdout.decode().strip() if pending.returncode==0 else 'HEAD'
    revision=git('log','-1','--format=%H',baseline,'--','docs/briefs/index.html').decode().strip()
    if not re.fullmatch('[a-f0-9]{40}',revision):raise ValueError('Invalid index provenance revision')
    if revision==_PRE_GATEWAY_INDEX:
        return revision,git('show',revision+':docs/briefs/editions.json')
    catalogue=json.loads(git('show',revision+':docs/scarb-copy-inputs.json'))
    expected=json.loads(git('show',revision+':docs/scarb-copy-manifest.json'))
    return catalogue,expected


if __name__=='__main__':
    markup=(ROOT/'docs/briefs/index.html').read_text(encoding='utf-8')
    manifest=json.loads((ROOT/'docs/briefs/editions.json').read_text(encoding='utf-8'))
    if '--retained' in sys.argv:
        catalogue,expected=historical_inputs()
        if catalogue==_PRE_GATEWAY_INDEX:
            verify_pre_gateway_index(catalogue,
                (ROOT/'docs/briefs/index.html').read_bytes(),
                (ROOT/'docs/briefs/editions.json').read_bytes(),expected)
            for record in manifest['editions']:
                route=record['path']
                if not re.fullmatch(r'briefs/\d{4}-\d{2}-\d{2}/',route):
                    raise ValueError('Invalid retained edition path')
                page=(ROOT/'docs'/route/'index.html').read_bytes()
                if hashlib.sha256(page).hexdigest()!=record['html_sha256']:
                    raise ValueError('Retained edition differs from the issued archive')
        else:
            verify_retained_generated_index(markup,manifest,catalogue,expected)
        print('Retained index matches its prior accepted catalogue and exact committed archive.')
    else:
        verify_generated_index(markup,manifest)
        print('Generated index matches accepted producer and issued archive evidence.')
