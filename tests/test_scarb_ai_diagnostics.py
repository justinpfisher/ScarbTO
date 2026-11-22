import copy,json,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch,MagicMock
from scripts import scarb_ai_voice as v
from tests.test_scarb_ai_voice import CONFIG,ENV,NOW,PACKET,REVIEW,FakeTransport,response,writer
class DiagnosticTests(unittest.TestCase):
 def run_failure(self,transport):
  with tempfile.TemporaryDirectory() as d,patch('scripts.scarb_packet_consumption_candidate.protected_root',lambda:Path(d)):
   state=Path(d)
   with self.assertRaises((v.VoiceError,OSError,ValueError)):
    v.generate(copy.deepcopy(PACKET),copy.deepcopy(CONFIG),state,transport=transport,env=ENV,now=NOW)
   held=json.loads(next((state/'held').glob('*.json')).read_text())
   usage=(state/'usage.json').read_bytes()
   retry=FakeTransport([])
   with self.assertRaisesRegex(v.VoiceError,'prior attempt'):
    v.generate(copy.deepcopy(PACKET),copy.deepcopy(CONFIG),state,transport=retry,env=ENV,now=NOW)
   self.assertEqual(retry.calls,[]);self.assertEqual((state/'usage.json').read_bytes(),usage)
   return held
 def test_author_validation_failure_is_one_call_and_no_payload_logged(self):
  fake=FakeTransport([response({'body':'FAKE_SECRET 123','evidence_ids':[]})])
  held=self.run_failure(fake);self.assertEqual(len(fake.calls),1)
  self.assertEqual(held['stage'],'author-validation');self.assertEqual(held['transport_attempts'],1)
  self.assertTrue(held['response_received']);self.assertNotIn('FAKE_SECRET',json.dumps(held))
 def test_actual_api_transport_sanitizes_http_timeout_and_network(self):
  cases=[
   (urllib.error.HTTPError('https://example.invalid/FAKE_SECRET',400,'FAKE_SECRET',{'Authorization':'FAKE_SECRET'},None),'http-error',400),
   (TimeoutError('FAKE_SECRET'),'transport-timeout',None),
   (urllib.error.URLError(TimeoutError('FAKE_SECRET')),'transport-timeout',None),
   (urllib.error.URLError('FAKE_SECRET'),'transport-error',None),
   (OSError('FAKE_SECRET'),'transport-error',None),
  ]
  for error,outcome,status in cases:
   with self.subTest(outcome=outcome),patch.object(v.urllib.request,'build_opener') as build:
    build.return_value.open.side_effect=error
    held=self.run_failure(v.api_request)
    self.assertEqual(build.return_value.open.call_count,1)
    self.assertEqual(held['outcome'],outcome)
    self.assertEqual(held.get('http_status'),status)
    self.assertEqual(held['stage'],'author-request');self.assertFalse(held['response_received'])
    self.assertNotIn('FAKE_SECRET',json.dumps(held))
 def test_actual_api_failure_has_no_raw_exception_context(self):
  with patch.object(v.urllib.request,'build_opener') as build:
   build.return_value.open.side_effect=urllib.error.HTTPError('FAKE_SECRET',503,'FAKE_SECRET',{},None)
   try:v.api_request({}, {'key':'FAKE_SECRET','organization':'fixture','project':'fixture'})
   except v.TransportFailure as error:
    self.assertIsNone(error.__cause__);self.assertIsNone(error.__context__)
    self.assertNotIn('FAKE_SECRET',str(error));self.assertEqual(error.http_status,503)
   else:self.fail('expected sanitized error')
 def test_actual_api_invalid_json_has_finite_outcome(self):
  with patch.object(v.urllib.request,'build_opener') as build:
   build.return_value.open.return_value.__enter__.return_value.read.return_value=b'FAKE_SECRET'
   held=self.run_failure(v.api_request)
   self.assertEqual(build.return_value.open.call_count,1)
   self.assertEqual(held['outcome'],'response-json-invalid');self.assertNotIn('FAKE_SECRET',json.dumps(held))
 def test_reviewer_rejection_is_two_attempts_and_stays_held(self):
  fake=FakeTransport([response(writer()),response({**REVIEW,'approve':False})]);held=self.run_failure(fake)
  self.assertEqual(held['transport_attempts'],2);self.assertEqual(held['stage'],'review-validation');self.assertEqual(held['outcome'],'independent-review-rejected')
 def test_incomplete_and_timeout_are_not_raw_text(self):
  self.assertEqual(v.diagnostic_outcome(TimeoutError('FAKE_SECRET')),{'outcome':'transport-timeout'})
  self.assertEqual(v.diagnostic_outcome(v.VoiceError('API response incomplete or refused')),{'outcome':'response-incomplete-or-refused'})
  self.assertEqual(v.diagnostic_outcome(ValueError('FAKE_SECRET')),{'outcome':'validation-or-local-error'})
 def test_success_still_clears_only_its_held_marker(self):
  with tempfile.TemporaryDirectory() as d,patch('scripts.scarb_packet_consumption_candidate.protected_root',lambda:Path(d)):
   state=Path(d);fake=FakeTransport();v.generate(copy.deepcopy(PACKET),copy.deepcopy(CONFIG),state,transport=fake,env=ENV,now=NOW)
   self.assertEqual(len(fake.calls),2);self.assertEqual(list((state/'held').glob('*.json')),[])

class FactDiagnosticTests(unittest.TestCase):
 def test_finite_codes_preserve_rejection_rules(self):
  packet={**copy.deepcopy(PACKET),"draft":"{{LOCK:SAFE}}", "locks":{"SAFE":"original"}, "limits":{"words":10,"characters":100}}
  ids=[x['id'] for x in packet['evidence']]
  cases=[('', 'writer-text-invalid'),('{{LOCK:UNKNOWN}}','lock-unknown'),('{{LOCK:SAFE}} {{LOCK:SAFE}}','lock-repeated'),('missing','lock-missing'),('{{LOCK:SAFE}} {{broken}}','unprotected-placeholder'),('{{LOCK:SAFE}} 123','unprotected-number'),('{{LOCK:SAFE}} https://FAKE_SECRET.invalid','unprotected-url'),('{{LOCK:SAFE}} <FAKE_SECRET>','unprotected-markup')]
  for body,code in cases:
   with self.subTest(code=code),self.assertRaises(v.VoiceError) as caught:v.text_check(packet,{'body':body,'evidence_ids':ids})
   self.assertEqual(v.diagnostic_outcome(caught.exception),{'outcome':code})
   self.assertNotIn('FAKE_SECRET',str(caught.exception))
  for limits,code in [({'words':1,'characters':100},'copy-word-limit'),({'words':10,'characters':1},'copy-character-limit')]:
   with self.assertRaises(v.VoiceError) as caught:v.text_check({**packet,'limits':limits},{'body':'{{LOCK:SAFE}} prose','evidence_ids':ids})
   self.assertEqual(v.diagnostic_outcome(caught.exception),{'outcome':code})
  with self.assertRaises(v.VoiceError) as caught:v.text_check(packet,{'body':'{{LOCK:SAFE}}','evidence_ids':[]})
  self.assertEqual(v.diagnostic_outcome(caught.exception),{'outcome':'evidence-identities-changed'})
  self.assertEqual(v.text_check(packet,{'body':'{{LOCK:SAFE}}','evidence_ids':ids}),'original')
