import copy,hashlib,unittest
from unittest.mock import patch
from scripts import scarb_group21_source_compatibility as h
from scripts import scarb_grouped_context_candidate as c
class Community15CompatibilityTests(unittest.TestCase):
 def setUp(self):
  self.current=c.seam.current_canonical_requests()
 def case(self,m,b):
  now=c.current_contexts([self.current[i] for i in b]);old=copy.deepcopy(now)
  sources={
   'docs/scarb-voice.mjs':h.COMMUNITY15_BEFORE,
   'docs/inspection-translations.mjs':h.FINDING22_TRANSITIONS['docs/inspection-translations.mjs'][0],
   'config/scarb-finding-source-drafts.json':h.COMMUNITY15_DIRECTORY_SOURCE_PAIRS['config/scarb-finding-source-drafts.json'][1],
  }
  for x in old.values():x['source_sha256']=sources.copy()
  return {'manifest_sha256':m,'packet_bindings':b},now,old
 def test_exact_nine_and_historical(self):
  for m,b in h.COMMUNITY15_PINS.items():
   pin,now,old=self.case(m,b);self.assertEqual(h.historical_context(pin,now,old),old);self.assertEqual(h.historical_context(pin,old,old),old)
 def test_unlisted_membership_and_context(self):
  m,b=next(iter(h.COMMUNITY15_PINS.items()));pin,now,old=self.case(m,b)
  for mutate in ('manifest','binding','context','digest','extra'):
   pp=copy.deepcopy(pin);nn=copy.deepcopy(now);oo=copy.deepcopy(old)
   if mutate=='manifest':pp['manifest_sha256']='0'*64
   if mutate=='binding':pp['packet_bindings'][next(iter(b))]='0'*64
   if mutate=='context':nn[next(iter(b))]['effective_translation']='changed meaning'
   if mutate=='digest':oo[next(iter(b))]['source_sha256']['docs/scarb-voice.mjs']='0'*64
   if mutate=='extra':nn['static.community-publishing-message-15']=nn[next(iter(b))]
   with self.assertRaises(ValueError):h.historical_context(pp,nn,oo)
 def test_byte_tamper_and_packet_change(self):
  m,b=next(iter(h.COMMUNITY15_PINS.items()));pin,now,old=self.case(m,b)
  original=h.Path.read_bytes
  def altered(path):
   raw=original(path);return raw+b' ' if path.as_posix().endswith('docs/scarb-voice.mjs') else raw
  with patch.object(h.Path,'read_bytes',altered):
   with self.assertRaises(ValueError):h.historical_context(pin,now,old)
  changed=copy.deepcopy(self.current);changed[next(iter(b))]['draft']+=' changed'
  with patch('scripts.scarb_grouped_projection_seam.current_canonical_requests',return_value=changed):
   with self.assertRaises(ValueError):h.historical_context(pin,now,old)


 def test_exact_git_lf_and_windows_crlf(self):
  manifest,bindings=next(iter(h.COMMUNITY15_PINS.items()))
  pin,current,sealed=self.case(manifest,bindings)
  actual={path:(h.ROOT/path).read_bytes() for path in h.COMMUNITY15_DIRECTORY_SOURCE_PAIRS}
  original=h.Path.read_bytes
  for ending in (b'\n',b'\r\n'):
   observed={path:raw.replace(b'\r\n',b'\n').replace(b'\n',ending) for path,raw in actual.items()}
   contexts={identity:{**entry,'source_sha256':{
    path:hashlib.sha256(raw).hexdigest() for path,raw in observed.items()
   }} for identity,entry in current.items()}
   def read(path):
    relative=path.relative_to(h.ROOT).as_posix() if path.is_relative_to(h.ROOT) else None
    return observed[relative] if relative in observed else original(path)
   with self.subTest(ending=ending),patch.object(h.Path,'read_bytes',read):
    self.assertEqual(h.historical_context(pin,contexts,sealed),sealed)

 def test_directory_only_rejects_other_current_source_edits(self):
  manifest,bindings=next(iter(h.COMMUNITY15_PINS.items()))
  pin,current,sealed=self.case(manifest,bindings)
  original=h.Path.read_bytes
  voice='docs/scarb-voice.mjs'
  edits=[
   (voice,lambda raw:raw.replace(h.DIRECTORY_NEW_LINE,h.DIRECTORY_NEW_LINE+b' ',1)),
   (voice,lambda raw:raw.replace(h.COMMUNITY15_NEW,h.COMMUNITY15_OLD,1)),
   *((voice,lambda raw,old=old,new=new:raw.replace(new,old,1)) for old,new in h.COMMUNITY333637_EDITS),
   ('docs/inspection-translations.mjs',lambda raw:raw+b' '),
   ('config/scarb-finding-source-drafts.json',lambda raw:raw+b' '),
  ]
  for relative,edit in edits:
   target=h.ROOT/relative
   changed=edit(original(target))
   self.assertNotEqual(changed,original(target))
   def read(path):
    return changed if path==target else original(path)
   claimed=copy.deepcopy(current)
   for entry in claimed.values():entry['source_sha256'][relative]=hashlib.sha256(changed).hexdigest()
   with self.subTest(path=relative),patch.object(h.Path,'read_bytes',read),self.assertRaises(ValueError):
    h.historical_context(pin,claimed,sealed)
