"""Version-2 proof over existing usage.json, not a new budget ledger.
Mutation driver is synthetic-state-only. Crash gaps are explicit, not atomic.
"""
import copy,json,hashlib
from decimal import Decimal,InvalidOperation,ROUND_CEILING
from pathlib import Path
from scripts import scarb_ai_voice as v
from scripts import scarb_packet_consumption_candidate as consumption
NUSD=Decimal(1000000000)

def amount(value):
 v.need(type(value) in (int,float,Decimal) and not isinstance(value,bool),'Invalid USD number')
 try:d=Decimal(str(value))
 except InvalidOperation:raise v.VoiceError('Invalid USD decimal')
 v.need(d.is_finite() and d>=0 and d*NUSD==(d*NUSD).to_integral_value(),'Invalid USD precision/value')
 return int(d*NUSD)

def ledger_values(ledger,month):
 v.need(isinstance(ledger,dict) and set(ledger)<={'months','paid_pilot_usd'} and isinstance(ledger.get('months'),dict),'Unknown shared ledger shape')
 for name,value in ledger['months'].items():
  import re
  v.need(isinstance(name,str) and re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',name),'Invalid accounting month');amount(value)
 if 'paid_pilot_usd' in ledger:amount(ledger['paid_pilot_usd'])
 return amount(ledger['months'].get(month,0)),amount(ledger.get('paid_pilot_usd',0))

def debit(before,month,reservation_nusd,month_cap_nusd,pilot_cap_nusd):
 spent,pilot=ledger_values(before,month)
 v.need(type(reservation_nusd) is int and reservation_nusd>0,'Invalid exact reservation')
 # Existing ledger stores six-decimal USD. Round reservation UP once, never
 # debit less than the nanodollar reservation or refund uncertain outcomes.
 charged=((reservation_nusd+999)//1000)*1000
 v.need(all(type(n) is int and n>=0 for n in [month_cap_nusd,pilot_cap_nusd]),'Invalid caps')
 v.need(spent+charged<=month_cap_nusd and pilot+charged<=pilot_cap_nusd,'Shared budget exceeded')
 after=copy.deepcopy(before);after['months'][month]=float(Decimal(spent+charged)/NUSD);after['paid_pilot_usd']=float(Decimal(pilot+charged)/NUSD)
 v.need(ledger_values(after,month)==(spent+charged,pilot+charged),'Non-representable shared ledger debit')
 return after,charged

def proof(before,after,month,reservation_nusd,actual_cost_nusd,month_cap_nusd,pilot_cap_nusd,bindings,membership_before,membership_after):
 consumption.bindings_check(bindings)
 expected,charged=debit(before,month,reservation_nusd,month_cap_nusd,pilot_cap_nusd)
 v.need(after==expected,'Shared ledger transition/refund mismatch')
 v.need(type(actual_cost_nusd) is int and 0<=actual_cost_nusd<=reservation_nusd,'Actual cost exceeds reserve')
 v.need(isinstance(membership_before,dict) and all(isinstance(k,str) and consumption.HEX.fullmatch(k) and isinstance(x,str) and consumption.HEX.fullmatch(x) for k,x in membership_before.items()),'Invalid prior membership')
 v.need(not set(bindings.values()).intersection(membership_before),'Prior packet consumed')
 scope=v.digest(bindings)
 v.need(membership_after=={**membership_before,**{h:scope for h in bindings.values()}},'Membership transition mismatch')
 return {'version':'scarb-shared-cost-proof-2','month':month,'reservation_nusd':reservation_nusd,'debited_nusd':charged,'actual_usage_cost_nusd':actual_cost_nusd,'month_cap_nusd':month_cap_nusd,'pilot_cap_nusd':pilot_cap_nusd,'usage_before_sha256':v.digest(before),'usage_after_sha256':v.digest(after),'membership_before_sha256':v.digest(membership_before),'membership_after_sha256':v.digest(membership_after),'packet_bindings':bindings,'no_refund':True}

def validate_proof(value,before,after,membership_before,membership_after):
 expected=proof(before,after,value['month'],value['reservation_nusd'],value['actual_usage_cost_nusd'],value['month_cap_nusd'],value['pilot_cap_nusd'],value['packet_bindings'],membership_before,membership_after)
 v.need(value==expected,'Shared cost proof differs');return True

def fixture_debit(root,expected_root,bindings,reservation_nusd,month,month_cap_nusd,pilot_cap_nusd,*,crash_at=None):
 """Execute actual debit/claim order on marked disposable state, no transport."""
 root=Path(root);v.need((root/'SYNTHETIC_GROUPED_ACCOUNTING_ONLY').is_file(),'Disposable synthetic accounting marker required')
 with v.exclusive(root):
  consumption.assert_unconsumed(root,bindings,expected_root=expected_root)
  path=root/'usage.json';v.need(path.is_file(),'Existing shared ledger required')
  before=json.loads(path.read_text(encoding='utf8'));after,charged=debit(before,month,reservation_nusd,month_cap_nusd,pilot_cap_nusd)
  pending=root/'grouped-accounting-pending.json'
  marker={'version':'scarb-shared-debit-pending-2','root':str(root.resolve()),'bindings':bindings,'usage_before_sha256':v.digest(before),'usage_after_sha256':v.digest(after),'debited_nusd':charged}
  v.atomic_json(pending,marker)
  if crash_at=='before_debit':raise RuntimeError('synthetic interruption before debit')
  v.atomic_json(path,after)
  if crash_at=='after_debit':raise RuntimeError('synthetic interruption after debit')
  # Pending blocks other entries. This call is within the same held lock and
  # verifies exact pending bytes; it may finish consumption but never retry calls.
  consumption.consume_grouped_locked(root,bindings,expected_root=expected_root,pending_proof=marker)
  if crash_at=='after_membership':raise RuntimeError('synthetic interruption after membership')
  v.need(json.loads(path.read_text())==after and json.loads(pending.read_text())==marker,'Debit changed during reservation')
  pending.unlink()
  return {'before':before,'after':after,'debited_nusd':charged}
