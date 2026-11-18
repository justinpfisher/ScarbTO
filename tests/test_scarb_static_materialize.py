import copy,json,unittest
from pathlib import Path
from scripts.scarb_static_materialize import discover,materialize
class StaticMaterializationTests(unittest.TestCase):
    def test_all_six_current_shells_roundtrip_exact_bytes_no_archive(self):
        records=json.loads(Path('config/scarb-static-shells.json').read_text(encoding='utf-8'))
        self.assertEqual(len(records),6)
        self.assertFalse(any('/briefs/' in p for p in records))
        for path,record in records.items():
            lookup={s['id']:s['draft'] for s in record['slots']}
            self.assertEqual(materialize(record,lookup.__getitem__),record['source'],path)
            self.assertEqual(record['source'],Path(path).read_bytes().decode().replace('\r\n','\n'))
    def test_unmarked_text_single_quote_uppercase_metadata_and_accessibility(self):
        source='''<META NAME="description" CONTENT='A public note'><button TITLE='Read it' aria-label="Open">A &amp; B</button><script>privateCode()</script>'''
        slots=discover(source)
        self.assertEqual([s['draft'] for s in slots],['A public note','Read it','Open','A & B'])
        record={'source':source,'slots':[{**s,'id':str(i)} for i,s in enumerate(slots)]}
        result=materialize(record,lambda key:'New "copy" <safe> & clear')
        self.assertIn('New &quot;copy&quot; &lt;safe&gt; &amp; clear',result)
        self.assertIn('<script>privateCode()</script>',result)
    def test_new_unregistered_text_or_missing_accepted_entry_holds(self):
        source='<p>Original</p>';record={'source':source,'slots':[{**discover(source)[0],'id':'one'}]}
        changed=copy.deepcopy(record);changed['source']=source+'<p>Unreviewed</p>'
        with self.assertRaises(ValueError):materialize(changed,lambda key:'Accepted')
        with self.assertRaises(KeyError):materialize(record,{}.__getitem__)
        with self.assertRaises(ValueError):materialize(record,lambda key:'')
    def test_template_fields_cannot_be_added_or_removed(self):
        source='<p>Explore {{NAME}}</p>';record={'source':source,'slots':[{**discover(source)[0],'id':'name'}]}
        with self.assertRaises(ValueError):materialize(record,lambda key:'Invented name')
        self.assertEqual(materialize(record,lambda key:'Meet {{NAME}}'),'<p>Meet {{NAME}}</p>')
    def test_no_srcdoc_or_unquoted_public_attribute(self):
        for source in ['<iframe srcdoc="content"></iframe>','<input title=unquoted>']:
            with self.assertRaises(ValueError):discover(source)
