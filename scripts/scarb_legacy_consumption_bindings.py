"""Exact legacy hold interpretations; originals remain immutable and held.
Bindings rederived from preserved pilot requests and v1 cache-key function.
No key-only fallback: path, complete original bytes hash and key must all match.
"""
from types import MappingProxyType
LEGACY=MappingProxyType({
 'held/9ddf48fcfe615dea5775e6a730e6e6e917b7a96a495a3029a4b1d4f1a45acd92.json':('88bc16fdcddac6eae96c06afd55117e34904426d5438e0b0bae03c75a26dae46','d1ee00949d7848b8046873c82dcd4490ef73f0b64b8bb2b8a204b435131c8fc0'),
 'held/79ed6ef525e064a40e17cd530d4ea8a6d99e138517d2fedce7a0a758e7e3d78d.json':('f681787f09f927162db4c2015cb072a81c5bef15925910d1dc1c36d23202c599','e8f8d7fda9aa2749b15acaf4450a988b9b29882b04fabd194168bce6f5b6fd18')})
def interpret(relative_path,raw_sha256,key):
 from scripts import scarb_ai_voice as v
 binding=LEGACY.get(relative_path)
 v.need(binding is not None and binding[0]==raw_sha256 and relative_path=='held/'+key+'.json','Unknown or changed unbound prior attempt')
 return binding[1]
