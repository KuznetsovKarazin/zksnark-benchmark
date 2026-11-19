#!/usr/bin/env python3
"""Continuous-time trace-driven counterfactual, conditional on complete accesses.

Whole wallet paths preserve bursts and calendar alignment. No actual EAS/DeFi
identity relationship is asserted. A failing/unknown data gate stops this CLI.
"""
import argparse
import bisect
import json
from pathlib import Path
import numpy as np


def pattern(accesses,updates,ttl=30*86400):
    last=None;out=[]
    for at in accesses:
        fresh=last is None or at-last>=ttl
        if last is not None:
            i=bisect.bisect_right(updates,last)
            fresh=fresh or (i<len(updates) and updates[i]<=at)
        out.append(fresh)
        if fresh:last=at
    return np.asarray(out,dtype=bool)


def evaluate(paths,schedules,seed=0,holders=1000,policy='selective',period_days=7,days=90):
    if not paths or not schedules:raise ValueError('Empty empirical input')
    b=len(schedules);rng=np.random.default_rng(seed)
    truth=rng.integers(b,size=holders)
    sampled=rng.integers(len(paths),size=holders)  # Resample entire wallet histories.
    common=sorted(set(t for s in schedules for t in s))
    batches=list(range(period_days*86400,days*86400,period_days*86400))
    accuracy=[];full=[];events=[];censored=[];entropy=[]
    for wallet,issuer in zip(sampled,truth):
        accesses=paths[wallet]
        candidates=np.stack([pattern(accesses,common if policy=='common' else batches if policy=='batch' else s) for s in schedules])
        observed=candidates[issuer]  # Generator supplies labels; observer gets no issuer.
        alive=np.ones(b,dtype=bool);identified=None
        for t,y,predicted in zip(accesses,observed,candidates.T):
            alive &= predicted==y
            if not alive.any():raise AssertionError('Internal model mismatch')
            if identified is None and alive.sum()==1:identified=t/86400
        accuracy.append(1/alive.sum());entropy.append(float(np.log2(alive.sum())));full.append(int(observed.sum()))
        censored.append(identified is None);events.append(identified)
    return dict(seed=seed,policy=policy,holders=holders,issuers=b,accuracy=float(np.mean(accuracy)),
                entropy_bits=float(np.mean(entropy)),full_per_holder=float(np.mean(full)),
                identified_fraction=1-float(np.mean(censored)),
                conditional_identification_median_days=float(np.median([x for x in events if x is not None])) if any(x is not None for x in events) else None,
                identification_curve=[sum(x is not None and x<=t for x in events)/holders for t in range(days+1)],
                interpretation='Counterfactual random issuer assignment; complete observed access times; no observation noise',
                uncertainty='Independent assignment/resampling seed conditional on these observed schedules and window')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--accesses',required=True);p.add_argument('--revocations',required=True)
    p.add_argument('--gate',required=True);p.add_argument('--out',required=True);p.add_argument('--holders',type=int,default=1000);p.add_argument('--seeds',type=int,default=20)
    args=p.parse_args();gate=json.loads(Path(args.gate).read_text())
    if gate.get('chain_validated_gate')!='PASS':raise SystemExit('Data gate is not chain-validated PASS; no headline empirical result generated')
    a=json.loads(Path(args.accesses).read_text());r=json.loads(Path(args.revocations).read_text())
    if (a['start'],a['end_exclusive'])!=(r['start'],r['end_exclusive']):raise SystemExit('Mismatched windows')
    result=[evaluate(a['access_paths'],r['issuer_schedules'],seed,args.holders,policy) for policy in ('selective','common','batch') for seed in range(args.seeds)]
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n')
