#!/usr/bin/env python3
"""Finite-horizon revocation counts; no new gas measurements.

Time is integer seconds. The exhaustive grid uses two distinct days sampled
uniformly without replacement from 1..89. Poisson results use independent
increments on a regular access grid, not an empirical revocation-rate estimate.
"""
from collections import Counter, defaultdict
from itertools import combinations
from math import ceil, comb, exp, fsum
from pathlib import Path
import argparse
import csv
import json
import gzip
import hashlib

DAY = 86400
STEP = 77760
TTL = 30 * DAY
N = 100
SIGNED = 8227440
UNCHECKED = 5556651
ZK_THREE = 7780318.6
MARGINAL = 288129.8
EUR_PER_GAS = .130658648 * 2164.73 / 1e9


def authorization_indices(update_seconds, n=N, step=STEP, ttl=TTL):
    updates = sorted(update_seconds)
    last = None
    selected = []
    for i in range(n):
        now = i * step
        stale = last is not None and any(last < u <= now for u in updates)
        if last is None or now >= last + ttl or stale:
            selected.append(i)
            last = now
    return selected


def gas(k):
    return ZK_THREE + MARGINAL * (k - 3)


def changed_storage_fields(update_seconds):
    indices=authorization_indices(update_seconds)
    changes=0
    for a,b in zip(indices,indices[1:]):
        previous,now=a*STEP,b*STEP
        changes+=int(min(previous+TTL,90*DAY)!=min(now+TTL,90*DAY))
        changes+=int(any(previous<u<=now for u in update_seconds))
    return changes


def fixed_count_distribution(max_m=12, n=N, step=STEP, ttl=TTL,
                             candidate_days=range(1, 90)):
    """Exact combinatorial DP over all subsets, simultaneously for m<=max_m.

    State = (last authorization index, selected revocations, full authorizations).
    Weight = number of subsets. Multiple events in an access interval coalesce.
    """
    candidates = [d * DAY for d in candidate_days]
    assert all(0 < d <= (n - 1) * step for d in candidates)
    states = {(0, 0, 1): 1}
    for i in range(1, n):
        available = sum((i-1)*step < d <= i*step for d in candidates)
        nxt = defaultdict(int)
        for (last, m, k), weight in states.items():
            for added in range(min(available, max_m-m)+1):
                full = added > 0 or (i-last)*step >= ttl
                nxt[(i if full else last, m+added, k+int(full))] += weight*comb(available, added)
        states = nxt
    result = {m: Counter() for m in range(max_m+1)}
    for (_, m, k), weight in states.items():
        result[m][k] += weight
    for m, counts in result.items():
        assert sum(counts.values()) == comb(len(candidates), m)
    return result


def poisson_distribution(rate_per_day, n=N, step=STEP, ttl=TTL):
    """Exact finite-horizon distribution under a homogeneous Poisson model.

    L=min(J,q), J geometric(p), p=1-exp(-lambda*h), q=ceil(T/h).
    Dynamic program propagates the age and count of the cache, allowing an
    independent renewal-equation calculation of the expectation below.
    """
    assert rate_per_day >= 0
    q = ceil(ttl/step)
    p = 1-exp(-rate_per_day*step/DAY)
    states = {(0, 1): 1.0}
    for _ in range(1, n):
        nxt = defaultdict(float)
        for (age, k), weight in states.items():
            if age+1 == q:
                nxt[(0, k+1)] += weight
            else:
                nxt[(0, k+1)] += weight*p
                nxt[(age+1, k)] += weight*(1-p)
        states = nxt
    counts = defaultdict(float)
    for (_, k), weight in states.items():
        counts[k] += weight
    assert abs(fsum(counts.values())-1) < 1e-12
    return dict(counts)


def renewal_expectation(rate_per_day, n=N, step=STEP, ttl=TTL):
    q = ceil(ttl/step)
    p = 1-exp(-rate_per_day*step/DAY)
    f = {l: p*(1-p)**(l-1) for l in range(1,q)}
    f[q] = (1-p)**(q-1)
    u = [1.0]
    for i in range(1,n):
        u.append(fsum(f[l]*u[i-l] for l in range(1,min(q,i)+1)))
    return fsum(u)


def csv_write(path, rows):
    with path.open('w', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1]/'results/revocation_model')
    args=parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    evidence=Path(__file__).resolve().parents[1]/'results/revocation_validation'
    historical=json.loads((evidence/'validation_report.json').read_text())
    traces=json.loads((evidence/'traces.json').read_text())
    raw=json.loads(gzip.decompress((evidence/'receipts_and_proofs.json.gz').read_bytes()))
    review_evidence=evidence.with_name('revocation_review')
    review_report=json.loads((review_evidence/'validation_report.json').read_text())
    assert review_report['status']=='PASS'
    review_traces=json.loads((review_evidence/'traces.json').read_text())
    review_raw=json.loads(gzip.decompress((review_evidence/'receipts_and_proofs.json.gz').read_bytes()))
    traces+=review_traces
    raw['transactions']+=review_raw['transactions']
    transactions={(r['label'],r['receipt']['hash']):r for r in raw['transactions']}
    calldata=[]
    for row in traces:
        if row['variant']=='zk' and row['event']=='reauthorize':
            data=bytes.fromhex(transactions[row['label'],row['tx_hash']]['transaction']['data'][2:])
            calldata.append(sum(4 if b==0 else 16 for b in data))
    first=[r['first'] for r in historical['stateSamples'] if r['variant']=='zk']
    first += [r['gas'] for r in review_traces if r['variant']=='zk' and r['event']=='first']
    signed_actual=next(r['gas'] for r in historical['summaries'] if r['variant']=='signed')
    pairs=[]
    for d1,d2 in combinations(range(1,90),2):
        k=len(authorization_indices([d1*DAY,d2*DAY]))
        fields=changed_storage_fields([d1*DAY,d2*DAY])
        bounds=[46463+f(first)+(100-k)*67610+(k-1)*(342621+f(calldata))+2800*fields-signed_actual for f in (min,max)]
        assert (bounds[1]<0) if k<=4 else (bounds[0]>0)
        pairs.append(dict(d1=d1,d2=d2,k=k,projected_delta_gas=round(gas(k)-SIGNED,1),
                          changed_storage_fields=fields,state_aware_delta_low=bounds[0],state_aware_delta_high=bounds[1]))
    counts=Counter(r['k'] for r in pairs)
    fixed=fixed_count_distribution()
    assert counts == fixed[2]
    fixed_rows=[]
    for m, dist in fixed.items():
        total=sum(dist.values()); mean=sum(k*v for k,v in dist.items())/total
        fixed_rows.append(dict(m=m,pairs_or_subsets=total,mean_k=mean,min_k=min(dist),max_k=max(dist),
                               probability_zk_more_gas=sum(v for k,v in dist.items() if gas(k)>SIGNED)/total,
                               expected_projected_delta_gas=gas(mean)-SIGNED))
    poisson=[]
    for m in range(13):
        dist=poisson_distribution(m/90)
        mean=fsum(k*p for k,p in dist.items())
        assert abs(mean-renewal_expectation(m/90))<1e-10
        poisson.append(dict(expected_revocations_90d=m,lambda_per_day=m/90,mean_k=mean,
                            probability_zk_more_gas=fsum(p for k,p in dist.items() if gas(k)>SIGNED),
                            expected_projected_delta_gas=gas(mean)-SIGNED))
    lo,hi=0.,12.
    for _ in range(60):
        mid=(lo+hi)/2
        if gas(renewal_expectation(mid/90))>SIGNED: hi=mid
        else: lo=mid
    economy=[]
    for name,days in [('30/60',[30,60]),('15/45',[15,45]),('31/63',[31,63]),('weekly',list(range(7,85,7)))]:
        k=len(authorization_indices([x*DAY for x in days])); signed_pool=SIGNED-UNCHECKED; zk_pool=gas(k)-UNCHECKED
        alpha=signed_pool/zk_pool
        for a in [1,.5]:
            budget=(signed_pool-a*zk_pool)*EUR_PER_GAS
            economy.append(dict(schedule=name,k=k,alpha=a,alpha_star=alpha,
                                 projected_delta_gas=round(gas(k)-SIGNED,1),
                                 minimum_gas_only_transfer_eur=max(0,(gas(k)-SIGNED)*EUR_PER_GAS),
                                 per_proof_expense_ceiling_eur=budget/k if budget>=0 else '',
                                 unreimbursed_shortfall_eur=max(0,-budget)))
    groups=[]
    for B in [1,2,4]:
        mean=renewal_expectation(12/90/B)
        groups.append(dict(groups=B,issuer_slots_per_group=4//B,expected_total_revocations_90d=12,
                           expected_relevant_revocations_90d=12/B,mean_k=mean,
                           expected_projected_delta_gas=gas(mean)-SIGNED))
    for name,rows in [('two_revocations.csv',pairs),('fixed_m.csv',fixed_rows),('poisson.csv',poisson),
                       ('schedule_economics.csv',economy),('group_model.csv',groups)]: csv_write(args.out/name,rows)
    summary=dict(status='PASS',pair_count=len(pairs),count_distribution=dict(sorted(counts.items())),
                 aligned_three_authorization_pairs=[[r['d1'],r['d2']] for r in pairs if r['k']==3],
                 probability_zk_more_gas=counts[5]/len(pairs),
                 expected_k_two=fsum(r['k'] for r in pairs)/len(pairs),
                 expected_projected_delta_gas_two=fsum(r['projected_delta_gas'] for r in pairs)/len(pairs),
                 mean_state_aware_delta_observed_calldata_envelope=[fsum(r[key] for r in pairs)/len(pairs) for key in ['state_aware_delta_low','state_aware_delta_high']],
                 state_aware_calibration=dict(calldata_gas_range=[min(calldata),max(calldata)],first_authorization_range=[min(first),max(first)],signed_receipt_baseline=signed_actual,
                    warning='Finite observed-range sensitivity projection, not receipts for all 3916 schedules and not a confidence interval.'),
                 poisson_mean_revocations_90d_at_expected_gas_parity=(lo+hi)/2,
                 first_integer_m_with_positive_expected_delta=next(r['m'] for r in fixed_rows if r['expected_projected_delta_gas']>0),
                 source_sha256={name:hashlib.sha256((evidence/name).read_bytes()).hexdigest() for name in ['validation_report.json','traces.json','receipts_and_proofs.json.gz']},
                 review_source_sha256={name:hashlib.sha256((review_evidence/name).read_bytes()).hexdigest() for name in ['validation_report.json','traces.json','receipts_and_proofs.json.gz']},
                 assumptions='Synthetic uniform distinct integer days and homogeneous Poisson alternatives; no empirical prevalence claim. Gas is projected either with historical fixed means or the explicitly labelled observed state/calldata envelope, not newly executed for every schedule. Finite horizon is 100 accesses through day 89.1; Poisson m denotes lambda times 90 days.')
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
