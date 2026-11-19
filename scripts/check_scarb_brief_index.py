"""Existing publication check for a newly generated index, never a retained one."""
import json,re,sys
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


def historical_inputs():
    import subprocess
    def git(*args):
        result=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=False)
        if result.returncode:raise ValueError('Committed index provenance unavailable')
        return result.stdout
    revision=git('log','-1','--format=%H','HEAD','--','docs/briefs/index.html').decode().strip()
    if not re.fullmatch('[a-f0-9]{40}',revision):raise ValueError('Invalid index provenance revision')
    catalogue=json.loads(git('show',revision+':docs/scarb-copy-inputs.json'))
    expected=json.loads(git('show',revision+':docs/scarb-copy-manifest.json'))
    return catalogue,expected


if __name__=='__main__':
    markup=(ROOT/'docs/briefs/index.html').read_text(encoding='utf-8')
    manifest=json.loads((ROOT/'docs/briefs/editions.json').read_text(encoding='utf-8'))
    if '--retained' in sys.argv:
        catalogue,expected=historical_inputs()
        verify_retained_generated_index(markup,manifest,catalogue,expected)
        print('Retained index matches its prior accepted catalogue and exact committed archive.')
    else:
        verify_generated_index(markup,manifest)
        print('Generated index matches accepted producer and issued archive evidence.')
