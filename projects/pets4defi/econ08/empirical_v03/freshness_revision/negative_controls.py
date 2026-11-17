"""Defensive null controls with issuer-independent common epochs and synthetic accesses."""
import csv
import sys
from pathlib import Path
import numpy as np
from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'src'))
from experiment import simulate
from observers import hmm,spectral


def main():
    results=[]
    for seed in range(5):
        # Independent labelled synthetic logging calibration. Zero real addresses.
        calibration=np.random.default_rng([900,seed])
        hidden=calibration.random(1000)<.10
        flipped=calibration.random(1000)<.10
        missing=(hidden.sum()+.5)/(len(hidden)+1)
        error=(flipped[~hidden].sum()+.5)/((~hidden).sum()+1)
        for b in (4,64):
            rng=np.random.default_rng([462,seed,b])
            # All candidate issuers share the same epoch and the same access distribution.
            updates=np.zeros((b,90),dtype=int);updates[:,::3]=1
            labels=rng.integers(b,size=1000);activity=np.full(len(labels),.45)
            obs,_,_=simulate(updates,labels,activity,rng,policy='common',label_error=.10,missing=.10)
            prior=np.arange(1,b+1,dtype=float);prior/=prior.sum()
            holdout=obs[:32]
            post=hmm(holdout,updates,activity[:32],policy='common',prior=prior,label_error=error,missing=missing)
            dev=float(np.max(abs(post-prior)))
            assert dev<1e-10
            groups=spectral(obs,b,seed)
            results.append([seed,b,len(labels),1000,error,missing,dev,adjusted_rand_score(labels,groups),
                            adjusted_mutual_info_score(labels,groups)])
    with (ROOT/'results/null_controls.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['seed','issuer_labels','clustering_n','calibration_n','estimated_label_error',
            'estimated_missing','maximum_posterior_minus_prior','null_ari','null_ami']);w.writerows(results)


if __name__=='__main__':main()
