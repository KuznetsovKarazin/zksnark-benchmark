#!/usr/bin/env python3
"""One factor at a time around 16 issuers and 1,000 holders, 20 seeds."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy.stats import t
from experiment import run_case


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    base=dict(issuers=16,policy='selective',label_error=.1,missing=.1,heterogeneity=True)
    cases=[base]
    for key,values in [('issuers',(4,8,32,64)),('label_error',(0,.05,.2)),('missing',(0,.3)),('heterogeneity',(False,)),('skewed_prior',(True,))]:
        cases.extend([dict(base,**{key:value}) for value in values])
    cases.extend([dict(base,policy=policy,rho=.5,period=7) for policy in ('common','cover','batch')])
    plan=dict(cases=cases,seeds=list(range(20)),holders=1000,days=90,scope='Synthetic daily model; one factor at a time')
    (out/'run_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    rows=[]
    for ci,case in enumerate(cases):
        file=out/f'case_{ci:02d}.json'
        if file.exists():
            sample=json.loads(file.read_text())
            assert len(sample)==20 and all(r['case']==ci and r['holders']==1000 for r in sample)
        else:
            sample=[]
            for seed in range(20):
                result,_,_,_=run_case(case,seed,n=1000);sample.append(dict(result,case=ci))
            file.write_text(json.dumps(sample,indent=2)+'\n')
        rows.extend(sample);print(json.dumps(dict(case=ci,completed_runs=len(rows),total_cases=len(cases))),flush=True)
    summary=[]
    for ci,case in enumerate(cases):
        sample=[r for r in rows if r['case']==ci];entry=dict(case=ci,**case,seeds=20,holders_per_seed=1000)
        for key in ('accuracy','posterior_entropy_bits','identified_fraction','first_confident_wrong_fraction','full_per_holder'):
            v=np.array([r[key] for r in sample]);entry[key]=float(v.mean());entry[key+'_ci95_halfwidth']=float(t.ppf(.975,19)*v.std(ddof=1)/math.sqrt(20))
        summary.append(entry)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',runs=len(rows),cases=len(cases),holders=1000)),flush=True)
