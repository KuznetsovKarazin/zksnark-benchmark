#!/usr/bin/env python3
"""Run one sparse-clustering stress case, with immediate persistent result."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from sklearn.metrics import adjusted_rand_score,adjusted_mutual_info_score
from experiment import simulate,schedules
from observers import spectral,anchored_predictions


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--issuers',type=int,required=True);p.add_argument('--holders',type=int,default=10000);p.add_argument('--out',required=True)
    args=p.parse_args();rng=np.random.default_rng(20261117);b=args.issuers;n=args.holders
    pub=schedules(b,90,rng);truth=rng.integers(b,size=n)
    obs,_,_=simulate(pub,truth,np.full(n,.45),rng,label_error=.1,missing=.1)
    start=time.perf_counter();clusters=spectral(obs,b,seed=20261117)
    anchors={int(i):int(truth[i]) for i in rng.choice(n,size=n//10,replace=False)}
    guesses=anchored_predictions(clusters,anchors);test=np.array([i not in anchors for i in range(n)]);covered=test&(guesses>=0)
    result=dict(holders=n,issuers=b,seed=20261117,label_error=.1,missing=.1,seconds=time.perf_counter()-start,
                ari=float(adjusted_rand_score(truth,clusters)),ami=float(adjusted_mutual_info_score(truth,clusters)),
                truth_permutation_null_ari=float(adjusted_rand_score(rng.permutation(truth),clusters)),
                anchor_count=len(anchors),nonanchor_coverage=float(covered.sum()/test.sum()),
                nonanchor_accuracy=float((guesses[test]==truth[test]).mean()),
                caveat='One seed: scalability demonstration, not a confidence interval or privacy guarantee')
    Path(args.out).parent.mkdir(parents=True,exist_ok=True);Path(args.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
