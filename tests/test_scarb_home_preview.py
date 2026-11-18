import copy,json,subprocess,unittest
from pathlib import Path
from scripts.scarb_home_preview import homepage_preview,NOTICE
from scripts import scarb_ai_voice as voice

class HomepagePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Invoke the real verified-byte collector rather than reconstructing its facts.
        js="""import {retainedIonviewRequest} from './scripts/collect_scarb_ai_requests.mjs';import {readFileSync} from 'node:fs';
        const paths=['research/phase1b-csi/fixtures/official-source-contract/scarbto-neighbourhood158-source-contract-2026-10-27.json','docs/area-selection.mjs','docs/community-data/releases/887085d7e735b7e9f8484013abe2fa0193ae812f421cc9bca3b16f17003e4655.json','docs/community-data/boundaries/9412f1c2737d7b0165867c7e6a38dd5e7549b834d0184cb9923c4241a85dd3f7.json','docs/data/scarborough-neighbourhoods.geojson'];console.log(JSON.stringify(retainedIonviewRequest(Object.fromEntries(paths.map(p=>[p,readFileSync(p)])))));"""
        cls.packet=json.loads(subprocess.check_output(['node','--input-type=module','-e',js],text=True))
        cls.record=json.loads(Path('config/scarb-static-shells.json').read_text(encoding='utf-8'))['docs/index.html']
        cls.writer={'slots':{'NAME':{'rank':0,'before':'Here is a map detail worth following: '},'WARD_A':{'rank':1,'before':' overlaps wards '},'WARD_B':{'rank':2,'before':' and '},'LIMIT':{'rank':3,'before':'. '}},'tail':'','evidence_ids':['retained-geography.125']}
    def test_actual_home_preview_is_inert_source_faithful_and_not_accepted(self):
        result=homepage_preview(self.packet,self.writer,self.record)
        self.assertFalse(result['accepted']);self.assertEqual(result['origin'],'test-fixture')
        for value in self.packet['locks'].values():self.assertIn(value,result['text'])
        self.assertIn(NOTICE,result['html']);self.assertIn('default-src',result['html'])
        self.assertIn('data-scarb-preview="test-fixture"',result['html'])
        self.assertIn('data-scarb-voice="home-intro">'+result['text'],result['html'])
        # The real release-side marked-copy gate must reject this unaccepted preview.
        js="import {inspectMarkup} from './scripts/check_scarb_voice.mjs';let s='';for await(const x of process.stdin)s+=x;try{inspectMarkup('docs/index.html',s);process.exit(1)}catch(e){if(!/drift/.test(e.message))throw e;console.log('unaccepted preview rejected')}"
        self.assertIn('rejected',subprocess.check_output(['node','--input-type=module','-e',js],input=result['html'],text=True,encoding='utf-8'))
    def test_current_production_inputs_unchanged(self):
        paths=['docs/index.html','docs/scarb-copy-manifest.json','docs/scarb-copy-manifest.mjs']
        before={p:Path(p).read_bytes() for p in paths}
        homepage_preview(self.packet,self.writer,self.record)
        self.assertEqual(before,{p:Path(p).read_bytes() for p in paths})
        manifest=json.loads(before[paths[1]]);self.assertEqual(len(manifest),736)
        self.assertNotIn(self.packet['id'],manifest)
    def test_changed_fact_or_evidence_is_refused(self):
        for key in ['locks','evidence','draft']:
            p=copy.deepcopy(self.packet);p[key]={} if key=='locks' else [] if key=='evidence' else 'changed'
            with self.assertRaises(voice.VoiceError):homepage_preview(p,self.writer,self.record)
    def test_missing_protected_slots_are_refused(self):
        for key in self.writer['slots']:
            w=copy.deepcopy(self.writer);del w['slots'][key]
            with self.assertRaises(voice.VoiceError):homepage_preview(self.packet,w,self.record)
    def test_missing_or_duplicate_home_intro_is_refused(self):
        for duplicate in [False,True]:
            r=copy.deepcopy(self.record);slot=next(s for s in r['slots'] if s['id']=='static.home-intro')
            if duplicate:r['slots'].append(slot)
            else:r['slots'].remove(slot)
            with self.assertRaises(voice.VoiceError):homepage_preview(self.packet,self.writer,r)
