#!/usr/bin/env python3
"""REVIEW-01 independent worked cross-check: read source gas fields, no reliance on economic_sweep.py output."""
from pathlib import Path
from decimal import Decimal as D
import csv, json
root=Path(__file__).resolve().parent
rows=list(csv.DictReader((root/'inputs'/'frequency_workload_costs.csv').open(newline='',encoding='utf-8')))
def gas(variant):
    matches=[r for r in rows if int(r['accesses'])==100 and r['policy']=='security' and r['variant']==variant and int(r['apps'])==1 and int(r['validity_days'])==90]
    assert len(matches)==1,(variant,len(matches))
    return D(matches[0]['user_transaction_gas_per_user'])
g0,gs,gz=map(gas,['unchecked','signed_cache','zk_cache'])
q=D('0.130658648');E=D('2164.73');alpha=D('.5');factor=q*E/D(10)**9
As=(gs-g0)*factor;Az=(gz-g0)*factor;R=(1-alpha)*Az;net_user_difference=alpha*Az-As
assert (g0,gs,gz)==(D('5556651'),D('8227440'),D('10661616.6'))
assert abs(net_user_difference-D('-.0334618078408697592480'))<D('.000000000000001')
assert abs(R-D('.7219460093446091373120'))<D('.000000000000001')
assert abs((alpha*Az+R)-Az)<D('.000000000000001')
print(json.dumps({'scope':'n100 K1 security, 90d, alpha=50%, p50','gas_unchecked':str(g0),'gas_signed':str(gs),'gas_ZK':str(gz),'A_signed_eur_user':str(As),'A_ZK_eur_user':str(Az),'user_ZK_minus_signed_network_eur':str(net_user_difference),'service_reimbursement_eur_user':str(R),'alpha_reimbursement_conservation':True,'source':'inputs/frequency_workload_costs.csv'},indent=2))
