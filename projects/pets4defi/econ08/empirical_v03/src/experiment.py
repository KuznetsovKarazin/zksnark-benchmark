#!/usr/bin/env python3
"""Reproducible stress experiments; synthetic results are explicitly labeled."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import time
import numpy as np
from observers import hmm, trigger_probabilities, spectral, anchored_predictions


def simulate(publications, assignments, activity, rng, *, ttl=30, policy="selective",
             rho=0.0, period=7, label_error=0.0, missing=0.0):
    n, days = len(assignments), publications.shape[1]
    trigger = trigger_probabilities(publications, policy, rho, period)
    age = np.full(n, ttl)
    pending = np.zeros(n, dtype=bool)
    observed = np.full((n, days), -1, dtype=int)
    full_count = np.zeros(n, dtype=int)
    access_count = np.zeros(n, dtype=int)
    for day in range(days):
        if day:
            age = np.minimum(age + 1, ttl)
        pending |= rng.random(n) < trigger[assignments, day]
        accessed = rng.random(n) < activity
        full = accessed & ((age >= ttl) | pending)
        full_count += full
        access_count += accessed
        age[full] = 0
        pending[full] = False
        visible = accessed & (rng.random(n) >= missing)
        labels = full ^ (rng.random(n) < label_error)
        observed[visible, day] = labels[visible]
    return observed, full_count, access_count


def metrics(posterior, assignments, threshold=0.95):
    n, days, b = posterior.shape
    truth = posterior[np.arange(n)[:, None], np.arange(days)[None, :], assignments[:, None]]
    crossed = truth >= threshold
    event = crossed.any(axis=1)
    times = np.where(event, crossed.argmax(axis=1), days)
    final = posterior[:, -1]
    ties = np.isclose(final, final.max(axis=1, keepdims=True), rtol=0, atol=1e-12)
    accuracy = (ties[np.arange(n), assignments] / ties.sum(axis=1)).mean()
    entropy = -(final * np.log2(np.maximum(final, 1e-300))).sum(axis=1).mean()
    confidence = posterior.max(axis=2) >= threshold
    first = confidence.argmax(axis=1)
    any_confidence = confidence.any(axis=1)
    first_guess = posterior[np.arange(n), first].argmax(axis=1)
    wrong = any_confidence & (first_guess != assignments)
    curve = np.array([(times <= day).mean() for day in range(days)])
    median = int(np.flatnonzero(curve >= .5)[0]) if np.any(curve >= .5) else None
    return dict(accuracy=float(accuracy),posterior_entropy_bits=float(entropy),
                identified_fraction=float(event.mean()),never_identified_fraction=float((~event).mean()),
                first_confident_wrong_fraction=float(wrong.mean()),
                identification_median_days=median,
                identified_only_median_days=float(np.median(times[event])) if event.any() else None), curve


def schedules(b, days, rng, heterogeneity=True):
    rates=np.exp(np.linspace(-1,1,b)) if heterogeneity else np.ones(b)
    rates=rates/rates.mean()/7
    return rng.poisson(rates[:,None],size=(b,days))


def run_case(case, seed, n=128, days=90):
    b=case['issuers'];rng=np.random.default_rng(seed)
    pub=schedules(b,days,rng,case.get('heterogeneity',True))
    prior=np.arange(1,b+1,dtype=float) if case.get('skewed_prior') else np.ones(b)
    prior/=prior.sum()
    truth=rng.choice(b,n,p=prior)
    activity=np.full(n,.45)
    kwargs={k:case[k] for k in ('policy','rho','period','label_error','missing') if k in case}
    obs,full,accesses=simulate(pub,truth,activity,rng,**kwargs)
    started=time.perf_counter()
    posterior=hmm(obs,pub,activity,prior=prior,**kwargs)
    result,curve=metrics(posterior,truth)
    # This is a prior-only benchmark under the declared prior, not always 1/B.
    baseline=float(prior.max())
    result.update(seed=seed,holders=n,days=days,**case,prior_only_bayes_accuracy=baseline,
                  full_per_holder=float(full.mean()),accesses_per_holder=float(accesses.mean()),
                  inference_seconds=time.perf_counter()-started,
                  model='synthetic_daily_Bernoulli_exact_HMM',uncertainty_unit='independent_simulation_seed')
    return result,curve,obs,truth


def matrix():
    rows=[]
    for b in (4,8,16,32,64):
        for e in (0,.05,.1,.2):
            for m in (0,.1,.3):
                rows.append(dict(issuers=b,policy='selective',label_error=e,missing=m,heterogeneity=True))
    for policy in ('common','cover','batch'):
        for e in (0,.1,.2):
            for m in (0,.3):
                rows.append(dict(issuers=4,policy=policy,rho=.5 if policy=='cover' else 0,period=7,label_error=e,missing=m,heterogeneity=True))
    rows.extend([dict(issuers=4,policy='selective',label_error=.1,missing=.1,heterogeneity=False),
                 dict(issuers=4,policy='selective',label_error=.1,missing=.1,heterogeneity=True,skewed_prior=True)])
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--seeds',type=int,default=20)
    p.add_argument('--holders',type=int,default=128);p.add_argument('--quick',action='store_true');p.add_argument('--scale',action='store_true')
    args=p.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    cases=matrix() if not args.quick else [dict(issuers=4,policy=x,label_error=.1,missing=.1,rho=.5) for x in ('selective','common','cover','batch')]
    plan=dict(cases=cases,seeds=list(range(args.seeds)),holders=args.holders,days=90,
              scale_cases=[dict(holders=10000,issuers=b,seed=20261117) for b in (4,64)] if args.scale else [],
              scope='Synthetic stress study; 10000-holder cases test sparse clustering only, not the complete HMM matrix.')
    (out/'run_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    all_rows=[];curves=[]
    with (out/'runs.jsonl').open('w') as log:
        for ci,case in enumerate(cases):
            for seed in range(args.seeds):
                result,curve,obs,truth=run_case(case,seed,n=args.holders)
                result['case']=ci;all_rows.append(result);log.write(json.dumps(result)+'\n');log.flush()
                curves.append(dict(case=ci,seed=seed,cumulative_identified_fraction=curve.tolist()))
            print(json.dumps(dict(completed_cases=ci+1,total_cases=len(cases),runs=len(all_rows))),flush=True)
    summary=[]
    # Student-t intervals across seed means, not across correlated holder-days.
    from scipy.stats import t
    for ci,case in enumerate(cases):
        sample=[r for r in all_rows if r['case']==ci]
        entry=dict(case=ci,**case,seeds=len(sample),holders_per_seed=args.holders)
        for key in ('accuracy','posterior_entropy_bits','identified_fraction','first_confident_wrong_fraction','full_per_holder','inference_seconds'):
            values=np.array([r[key] for r in sample]);mean=values.mean()
            half=float(t.ppf(.975,len(values)-1)*values.std(ddof=1)/math.sqrt(len(values))) if len(values)>1 else None
            entry[key]=float(mean);entry[key+'_ci95_halfwidth']=half
        summary.append(entry)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'identification_curves.json').write_text(json.dumps(curves)+'\n')
    if args.scale:
        from sklearn.metrics import adjusted_rand_score,adjusted_mutual_info_score
        scale=[]
        for b in (4,64):
            case=dict(issuers=b,policy='selective',label_error=.1,missing=.1)
            rng=np.random.default_rng(20261117);pub=schedules(b,90,rng);truth=rng.integers(b,size=10000)
            obs,full,accesses=simulate(pub,truth,np.full(10000,.45),rng,label_error=.1,missing=.1)
            started=time.perf_counter();clusters=spectral(obs,b,seed=20261117)
            anchors={int(i):int(truth[i]) for i in rng.choice(len(truth),size=1000,replace=False)}
            guesses=anchored_predictions(clusters,anchors);test=np.array([i not in anchors for i in range(len(truth))]);covered=test&(guesses>=0)
            independent=rng.permutation(truth)
            scale.append(dict(holders=10000,issuers=b,seed=20261117,seconds=time.perf_counter()-started,
                              ari=float(adjusted_rand_score(truth,clusters)),ami=float(adjusted_mutual_info_score(truth,clusters)),
                              truth_permutation_null_ari=float(adjusted_rand_score(independent,clusters)),
                              anchor_count=len(anchors),nonanchor_coverage=float(covered.sum()/test.sum()),
                              nonanchor_accuracy=float((guesses[test]==truth[test]).mean()),
                              caveat='One seed per size: scalability demonstration, not a confidence interval or privacy guarantee'))
            print(json.dumps(scale[-1]),flush=True)
        (out/'scale.json').write_text(json.dumps(scale,indent=2)+'\n')
    print(json.dumps(dict(status='COMPLETE',runs=len(all_rows),cases=len(cases))),flush=True)


if __name__=='__main__':main()
