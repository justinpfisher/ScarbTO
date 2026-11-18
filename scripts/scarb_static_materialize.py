"""Offline static shell materialization from immutable authoring templates.
No model, receipt acceptance, network, archive writes or output installation.
"""
from html import escape, unescape
from html.parser import HTMLParser
import re

ATTRS={'aria-label','aria-description','alt','title','placeholder'}
class Slots(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False); self.source=source; self.slots=[]; self.hidden=[]
        self.lines=[0]
        self.lines += [m.end() for m in re.finditer('\n', source)]
    def absolute_position(self):
        line,col=self.getpos(); return self.lines[line-1]+col
    def add(self,start,end,attribute=False):
        raw=self.source[start:end]
        if not raw.strip() or not re.search(r'[A-Za-z]',unescape(raw)): return
        self.slots.append({'start':start,'end':end,'draft':unescape(raw),'attribute':attribute})
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.hidden.append(tag); return
        if self.hidden:return
        raw=self.get_starttag_text(); base=self.absolute_position(); values=dict(attrs)
        for m in re.finditer(r'''\s+([^\s=/>]+)\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))''',raw):
            name=m[1].lower()
            if name=='srcdoc':raise ValueError('Embedded authored HTML needs its own producer')
            selected=name in ATTRS or (tag=='input' and name=='value') or (tag=='meta' and name=='content' and (values.get('name') or values.get('property')) in ('description','og:title','og:description','twitter:title','twitter:description'))
            if selected:
                group=3 if m[3] is not None else 4 if m[4] is not None else 5
                if group==5:raise ValueError('Public attribute must be quoted before materialization')
                self.add(base+m.start(group),base+m.end(group),True)
    def handle_endtag(self,tag):
        if self.hidden and tag==self.hidden[-1]:self.hidden.pop()
    def handle_data(self,data):
        if not self.hidden:self.add(self.absolute_position(),self.absolute_position()+len(data))
    def handle_entityref(self,name):pass
    def handle_charref(self,name):pass

def discover(source):
    # HTMLParser splits entity references in data; merge contiguous data/entity
    # spans by replacing entities with same-length neutral text for tokenization.
    masked=re.sub(r'&(?:#[xX][0-9a-fA-F]+|#\d+|[A-Za-z][A-Za-z0-9]+);',lambda m:'x'*len(m[0]),source)
    parser=Slots(masked);parser.feed(masked);parser.close()
    result=parser.slots
    for slot in result:slot['draft']=unescape(source[slot['start']:slot['end']])
    return result

def materialize(record, lookup):
    source=record['source'];slots=discover(source)
    expected=[{k:v for k,v in s.items() if k not in ('id','fields')} for s in record['slots']]
    if slots!=expected:raise ValueError('Static authoring template changed without classification')
    result=source
    for slot in reversed(record['slots']):
        text=lookup(slot['id'])
        for name,value in slot.get('fields',{}).items():text=text.replace('{{'+name+'}}',value)
        if not isinstance(text,str) or not text.strip():raise ValueError('Missing accepted static copy')
        if sorted(re.findall(r'\{\{[^{}]+\}\}',text))!=sorted(re.findall(r'\{\{[^{}]+\}\}',slot['draft'])):raise ValueError('Static placeholders changed')
        result=result[:slot['start']]+(source[slot['start']:slot['end']] if text==slot['draft'] else escape(text,quote=slot['attribute']))+result[slot['end']:]
    return result
