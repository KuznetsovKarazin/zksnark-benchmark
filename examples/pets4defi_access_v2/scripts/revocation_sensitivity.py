#!/usr/bin/env python3
"""Bounded model-only sensitivity; no new EVM receipts or empirical frequencies.

Two distinct integer update days are uniform on 1..89 unless a conditional
gap law is named. For fixed 90 days, regular n and spacing are coupled.
Expired credentials are rejected, never silently renewed. Gas uses historical
fixed means, compared between the two CACHE variants (no direct-path selection).
"""
from collections import Counter
from itertools import combinations
from pathlib import Path
from math import fsum
import argparse
import csv
import gzip
import hashlib
import io
import json

from revocation_model import DAY, EVENT_COSTS, csv_write, validated_unit_costs


def cache_trace(accesses, updates, ttl, expiry):
    if ttl <= 0 or expiry <= 0 or any(t < 0 for t in accesses):
        raise ValueError('Times must be nonnegative and lifetimes positive.')
    if any(b <= a for a, b in zip(accesses, accesses[1:])):
        raise ValueError('Accesses must be strictly ordered.')
    updates = sorted(updates)
    last = None; deadline = None; epoch = 0; cursor = 0
    full = []; rejected = []; deadline_changes = 0; epoch_changes = 0
    stored_epoch = None
    for i, now in enumerate(accesses):
        while cursor < len(updates) and updates[cursor] <= now:
            epoch += 1; cursor += 1
        if now >= expiry:
            rejected.append(i)
            continue
        if last is None or now >= deadline or epoch != stored_epoch:
            new_deadline = min(now + ttl, expiry)
            if last is not None:
                deadline_changes += int(new_deadline != deadline)
                epoch_changes += int(epoch != stored_epoch)
            full.append(i); last = now; deadline = new_deadline; stored_epoch = epoch
    return dict(full=full, rejected=rejected, deadline_changes=deadline_changes,
                epoch_changes=epoch_changes, accepted=len(accesses)-len(rejected))


def cache_gas(cost, n, k):
    if not 1 <= k <= n:
        raise ValueError('A positive accepted trace must have 1 <= k <= n.')
    return float(cost['approve'] + cost['cache_register_first'] +
                 (k-1)*cost['cache_reauthorize'] + (n-k)*cost['cache_hit'])


def pair_grid(max_gap=None):
    return [(a, b) for a, b in combinations(range(1, 90), 2)
            if max_gap is None or b-a <= max_gap]


def scenarios():
    base = dict(n=100, ttl_days=30, expiry_days=90, max_gap=None, access_pattern='regular')
    yield 'reference', base
    for ttl in (7, 14, 60):
        yield f'ttl_{ttl}', {**base, 'ttl_days':ttl}
    for n in (10, 50, 200):
        yield f'n_{n}', {**base, 'n':n}
    for expiry in (60, 120):
        yield f'expiry_{expiry}', {**base, 'expiry_days':expiry}
    for gap in (1, 7):
        yield f'cluster_gap_{gap}', {**base, 'max_gap':gap}
    # 20 bursts of five accesses, same count, first/last access and horizon.
    yield 'access_bursts', {**base, 'access_pattern':'five_per_burst'}


def access_grid(config):
    if config['access_pattern'] == 'regular':
        return [i*90*DAY//config['n'] for i in range(config['n'])]
    # Four 0.1-day gaps within each burst; starts evenly spaced to preserve
    # the original 0 and 89.1-day endpoints, rounded to integer seconds.
    return [round(b*(887*DAY/10)/19)+j*(DAY//10) for b in range(20) for j in range(5)]


def analyze(name, config, costs):
    accesses = access_grid(config)
    ttl = config['ttl_days']*DAY; expiry = config['expiry_days']*DAY
    signed = cache_trace(accesses, [], ttl, expiry)
    n = signed['accepted']; ks = len(signed['full']); signed_gas = cache_gas(costs['signed_cache'], n, ks)
    dist = Counter(); deadline_sum = 0; epoch_sum = 0; deltas = []; details = []
    pairs = pair_grid(config['max_gap'])
    for d1, d2 in pairs:
        z = cache_trace(accesses, [d1*DAY, d2*DAY], ttl, expiry)
        assert z['accepted'] == n and z['rejected'] == signed['rejected']
        k = len(z['full']); dist[k] += 1
        deadline_sum += z['deadline_changes']; epoch_sum += z['epoch_changes']
        delta = cache_gas(costs['zk_cache'], n, k)-signed_gas
        deltas.append(delta)
        details.append(dict(scenario=name,d1=d1,d2=d2,k_signed=ks,k_zk=k,
                            accepted_accesses=n,expired_accesses=len(z['rejected']),
                            deadline_changes=z['deadline_changes'],epoch_changes=z['epoch_changes'],
                            projected_delta_gas=round(delta,1) if n==config['n'] else ''))
    return dict(scenario=name,**config,access_spacing_days=90/config['n'] if config['access_pattern']=='regular' else '',
                first_access_day=accesses[0]/DAY,last_access_day=accesses[-1]/DAY,pair_count=len(pairs),
                accepted_accesses=n,expired_accesses=len(signed['rejected']),k_signed=ks,
                min_k_zk=min(dist),max_k_zk=max(dist),mean_k_zk=fsum(k*v for k,v in dist.items())/len(pairs),
                mean_deadline_changes=deadline_sum/len(pairs),mean_epoch_changes=epoch_sum/len(pairs),
                probability_zk_more_gas=sum(x>0 for x in deltas)/len(pairs) if n==config['n'] else '',
                expected_projected_delta_gas=fsum(deltas)/len(pairs) if n==config['n'] else '',
                count_distribution=json.dumps(dict(sorted(dist.items())),separators=(',',':'))), details


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'results/revocation_sensitivity')
    args=parser.parse_args(); costs=validated_unit_costs()
    rows=[]; pairs=[]
    for name, config in scenarios():
        row, detail=analyze(name,config,costs); rows.append(row); pairs.extend(detail)
    args.out.mkdir(parents=True,exist_ok=True)
    csv_write(args.out/'scenarios.csv',rows)
    text=io.StringIO(newline='')
    writer=csv.DictWriter(text,fieldnames=list(pairs[0]),lineterminator='\n')
    writer.writeheader();writer.writerows(pairs)
    # Fixed mtime/filename and GzipFile avoid platform-dependent gzip headers.
    with (args.out/'pairs.csv.gz').open('wb') as f:
        with gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as z:
            z.write(text.getvalue().encode('utf-8'))
    summary=dict(status='PASS',scenarios=len(rows),pair_evaluations=len(pairs),
                 event_costs_sha256=hashlib.sha256(EVENT_COSTS.read_bytes()).hexdigest(),
                 model_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 assumptions=[
                     'Synthetic model-only sensitivity, not an EVM sweep, field prevalence or a confidence interval.',
                     'Regular n and spacing satisfy spacing=90/n days; frequency and count are not independent at a fixed horizon.',
                     'Uniform distinct days 1..89; clustered laws condition this grid on a gap <=1 or <=7 days. They are not empirical or Poisson arrival models.',
                     'Events after the last accepted access cannot affect its cost; expired accesses are ineligible and have no simulated receipt or renewal.',
                     'Fixed historical unit gas for cached paths; no family-wise direct/cache optimization, changed-state calibration, setup or rejected-transaction fees.',
                     'Gas ranking suppressed when the credential expires before all scheduled accesses. No assertion of workload equivalence after expiry.'
                 ])
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
