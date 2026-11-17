#!/usr/bin/env python3
"""Exploratory indexer-calibrated SYNTHETIC schedules, never four real issuers.

The four-issuer real-data gate failed the indexer screen. This sensitivity uses
the two qualifying source profiles, assigns them equally to synthetic issuers,
and circularly shifts each profile. Accesses remain synthetic daily Bernoulli.
The assumptions deliberately differ from an empirical headline experiment.
"""
import argparse
import collections
import json
from pathlib import Path
import numpy as np
from acquire import timestamp
from experiment import simulate,metrics
from observers import hmm


def calibration(private_folder,spec):
    base=Path(private_folder)/'base';report=json.loads((base/'report.json').read_text())
    if not report['indexer_pagination_complete'] or not report.get('aggregate_matches_pagination'):
        raise ValueError('Indexer pagination and aggregate cross-check must complete')
    rows=json.loads((base/'revocations.json').read_text());grouped=collections.defaultdict(list)
    for row in rows:grouped[row['attester'].lower()].append(row)
    ordered=sorted(grouped.items(),key=lambda kv:(-len(kv[1]),kv[0]));profiles=[];start=timestamp(spec['window_start'])
    for (address,records),candidate in zip(ordered,report['candidates']):
        if candidate['qualifies'] is not True:continue
        counts=np.zeros(90,dtype=int)
        for row in records:counts[(row['revocationTime']-start)//86400]+=1
        profiles.append(dict(local_id=candidate['local_id'],credential_revocations_per_day=counts.tolist(),
                             active_days=int((counts>0).sum()),revocations=len(records)))
    return dict(source='Base EAS indexer',window_start=spec['window_start'],window_end_exclusive=spec['window_end_exclusive'],
                chain_verified=False,real_qualifying_issuers=len(profiles),profiles=profiles,
                caveats=['Credential revocation events are not measured registry-root publication transactions.',
                         'Daily coalescing removes within-day structure.',
                         'Circular shifts and duplicated template issuers are synthetic.',
                         'Template weights are equal by design, not estimated market shares.',
                         'Accesses remain synthetic and independent of issuer.'])


if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--private-indexer');g.add_argument('--calibration-file');p.add_argument('--out',required=True);p.add_argument('--holders',type=int,default=1000)
    args=p.parse_args();root=Path(__file__).parents[1];spec=json.loads((root/'config/protocol.json').read_text());out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    cal=json.loads(Path(args.calibration_file).read_text()) if args.calibration_file else calibration(args.private_indexer,spec)
    (out/'calibration.json').write_text(json.dumps(cal,indent=2)+'\n')
    profiles=[np.asarray(x['credential_revocations_per_day']) for x in cal['profiles']]
    if not profiles:raise SystemExit('No qualifying source templates')
    rows=[]
    for b in (4,16,64):
        for seed in range(20):
            rng=np.random.default_rng(seed);pub=np.stack([np.roll(profiles[i%len(profiles)],rng.integers(90)) for i in range(b)])
            truth=rng.integers(b,size=args.holders);activity=np.full(args.holders,.45)
            obs,full,accesses=simulate(pub,truth,activity,rng,label_error=.1,missing=.1)
            post=hmm(obs,pub,activity,label_error=.1,missing=.1)
            result,curve=metrics(post,truth)
            rows.append(dict(result,seed=seed,issuers=b,holders=args.holders,full_per_holder=float(full.mean()),
                             distinct_binary_schedules=int(len(np.unique(pub>0,axis=0))),
                             empirical_issuer_count=len(profiles),model='Indexer-calibrated synthetic daily profiles; synthetic accesses'))
        (out/'runs.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(issuers=b,runs=len(rows))),flush=True)
    summary=[]
    for b in (4,16,64):
        v=[r for r in rows if r['issuers']==b]
        summary.append(dict(issuers=b,holders_per_seed=args.holders,seeds=20,
                            **{k:float(np.mean([r[k] for r in v])) for k in ('accuracy','identified_fraction','full_per_holder','posterior_entropy_bits','distinct_binary_schedules')}))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
