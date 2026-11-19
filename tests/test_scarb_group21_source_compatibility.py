import copy,unittest,hashlib
from unittest.mock import patch
from scripts import scarb_group21_source_compatibility as h
from scripts import scarb_grouped_context_candidate as c
class BoundedSourceCompatibilityTests(unittest.TestCase):
 def setUp(self):
  self.current=c.seam.current_canonical_requests();self.context=c.current_contexts([self.current[i] for i in h.BINDINGS]);self.old=copy.deepcopy(self.context)
  for item in self.old.values():
   for path,(before,after) in h.TRANSITIONS.items():item['source_sha256'][path]=before
  self.pin={'manifest_sha256':h.MANIFEST,'packet_bindings':h.BINDINGS}
 def test_exact_transition_and_unmodified_packets(self):
  # Historical positive proof remains bound to the exact previously qualified bytes.
  # Reconstruct the bounded previous source version from tracked wording only.
  # Works in a shallow checkout; the exact historic byte hashes still bind it.
  replacements={
   'Utensils being used were not in good repair.':'Utensils were not in good repair.',
   'Utensils being used were not designed so they could be readily cleaned.':'Utensils were not designed so they could be readily cleaned.',
   'Food equipment being used was not made of material that could be readily cleaned.':'Food equipment was not made of material that could be readily cleaned.',
   'Shelves being used were not designed so they could be readily cleaned.':'Shelves were not designed so they could be readily cleaned.',
   'Food equipment being used was not designed so it could be readily cleaned.':'Food equipment was not designed so it could be readily cleaned.',
   'Utensils being used were not made of material that could be readily cleaned.':'Utensils were not made of material that could be readily cleaned.',
   'Food equipment being used was not of sound, tight construction.':'Food equipment was not of sound, tight construction.',
   'Utensils being used were not of sound, tight construction.':'Utensils were not of sound, tight construction.',
   'Utensils were sanitized using an agent for which the testing reagent was not readily available.':'The testing chemical needed to check the utensil sanitizer was not readily available.'}
  files={}
  for path,(_,expected) in h.TRANSITIONS.items():
   raw=(c.ROOT/path).read_bytes()
   for old,new in h.FINDING22_EDITS:raw=raw.replace(new,old)
   if path=='docs/scarb-voice.mjs':
    for old,new in h.COMMUNITY333637_EDITS:raw=raw.replace(new,old)
   raw=raw.replace(b"Supply a non-empty list of boundary polygons within the publishing tool's polygon limit.",b'Boundary polygons are missing.')
   for current,prior in replacements.items():
    self.assertEqual(raw.count(current.encode()),1)
    raw=raw.replace(current.encode(),prior.encode())
   raw=raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
   self.assertEqual(hashlib.sha256(raw).hexdigest(),expected)
   files[path]=raw
  context=copy.deepcopy(self.context)
  for item in context.values():
   for path,(_,after) in h.TRANSITIONS.items():item['source_sha256'][path]=after
  context['static.finding-explanation-fcf37504d73b4996']['effective_translation']='Food equipment was not of sound, tight construction.'
  old=copy.deepcopy(context)
  for item in old.values():
   for path,(before,_) in h.TRANSITIONS.items():item['source_sha256'][path]=before
  original=h.Path.read_bytes
  def historical_bytes(path):
   for rel,raw in files.items():
    if path.as_posix().endswith(rel):return raw
   return original(path)
  with patch.object(h.Path,'read_bytes',historical_bytes):
   self.assertEqual(h.historical_context(self.pin,context,old),old)
  self.assertNotEqual({i:c.v.digest(self.current[i]) for i in h.BINDINGS},h.BINDINGS)
  with self.assertRaises(c.v.VoiceError):h.historical_context(self.pin,self.context,old)
  self.assertEqual(h.historical_context({},self.context,self.context),self.context)
 def test_unrelated_change_wrong_pin_membership_and_hash_fail(self):
  for kind in ['meaning','official','hash','manifest','binding','membership']:
   current=copy.deepcopy(self.context);pin=copy.deepcopy(self.pin);i=next(iter(current))
   if kind=='meaning':current[i]['meaning']='changed'
   elif kind=='official':current[i]['official_wording']='changed'
   elif kind=='hash':current[i]['source_sha256']['docs/scarb-voice.mjs']='a'*64
   elif kind=='manifest':pin['manifest_sha256']='a'*64
   elif kind=='binding':pin['packet_bindings'][i]='a'*64
   else:current.pop(i)
   with self.subTest(kind=kind),self.assertRaises(c.v.VoiceError):h.historical_context(pin,current,self.old)
 def test_actual_source_bytes_not_just_claimed_hash(self):
  original=h.Path.read_bytes
  def altered(path):return original(path)+b'\n'
  with patch.object(h.Path,'read_bytes',altered),self.assertRaises(c.v.VoiceError):h.historical_context(self.pin,self.context,self.old)
 def test_regulated_action_and_condition_retained(self):
  p=self.current['static.finding-explanation-2c28027af8513b95']
  self.assertEqual(p['draft'],'Multi-service articles that were not readily cleanable were being used.')
  self.assertEqual(p['evidence'][1]['fact'],'use multi-service articles not of readily cleanable form - sec. 8(1)(c)')
  self.assertEqual(p['locks'],{})
  self.assertNotIn('designed',p['draft'])
