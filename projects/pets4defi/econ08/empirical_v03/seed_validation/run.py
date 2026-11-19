"""Replicate two published statistics on generated data, without external inputs."""
import argparse
import csv
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys

import numpy as np
from scipy.stats import t
from sklearn.metrics import adjusted_rand_score
from threadpoolctl import threadpool_limits

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
from experiment import metrics, schedules, simulate
from observers import anchored_predictions, hmm, spectral

SEEDS = range(30001, 30011)
SIZES = (4, 64)
RATE = 0.10
METRICS = ("known_accuracy", "estimated_accuracy", "paired_difference",
           "ari", "nonanchor_accuracy", "permuted_ari")


def one_run(case):
    seed, issuers = case
    with threadpool_limits(limits=1):
        # Independent calibration: missed events and errors among visible labels.
        calibration = np.random.default_rng([900, seed, issuers])
        missed = calibration.random(1000) < RATE
        flipped = calibration.random(1000) < RATE
        miss_est = (missed.sum() + 0.5) / 1001
        error_est = (flipped[~missed].sum() + 0.5) / ((~missed).sum() + 1)

        rng = np.random.default_rng([1, seed, issuers])
        updates = schedules(issuers, 90, rng)
        assignments = rng.integers(issuers, size=128)
        activity = np.full(128, 0.45)
        obs, _, _ = simulate(updates, assignments, activity, rng,
                             label_error=RATE, missing=RATE)
        scores = []
        for error, missing in ((RATE, RATE), (error_est, miss_est)):
            posterior = hmm(obs, updates, activity, label_error=error, missing=missing)
            scores.append(metrics(posterior, assignments)[0]["accuracy"])

        rng = np.random.default_rng([2, seed, issuers])
        updates = schedules(issuers, 90, rng)
        assignments = rng.integers(issuers, size=10000)
        obs, _, _ = simulate(updates, assignments, np.full(10000, 0.45), rng,
                             label_error=RATE, missing=RATE)
        clusters = spectral(obs, issuers, seed)
        disclosed = rng.choice(len(assignments), 1000, replace=False)
        heldout = np.ones(len(assignments), dtype=bool)
        heldout[disclosed] = False
        anchors = dict(zip(disclosed.tolist(), assignments[disclosed].tolist()))
        assigned = anchored_predictions(clusters, anchors)
        row = dict(seed=seed, issuers=issuers, estimated_error=error_est,
                   estimated_missing=miss_est, known_accuracy=scores[0],
                   estimated_accuracy=scores[1], paired_difference=scores[1]-scores[0],
                   ari=adjusted_rand_score(assignments, clusters),
                   nonanchor_accuracy=np.mean(assigned[heldout] == assignments[heldout]),
                   permuted_ari=adjusted_rand_score(rng.permutation(assignments), clusters))
        print(f"Completed seed {seed} for {issuers} simulated issuers", flush=True)
        return row


def write_csv(path, rows):
    temp = path.with_suffix(".tmp")
    with temp.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=1, choices=range(1, 5))
    args = parser.parse_args()
    cases = [(seed, issuers) for seed in SEEDS for issuers in SIZES]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(one_run, cases))
    write_csv(HERE / "seeds.csv", rows)
    summaries = []
    for issuers in SIZES:
        for metric in METRICS:
            values = [r[metric] for r in rows if r["issuers"] == issuers]
            sd = np.std(values, ddof=1)
            halfwidth = t.ppf(0.975, len(values)-1) * sd / np.sqrt(len(values))
            summaries.append(dict(issuers=issuers, metric=metric, seeds=len(values),
                                  mean=np.mean(values), sd=sd, ci95_halfwidth=halfwidth))
    write_csv(HERE / "summary.csv", summaries)


if __name__ == "__main__":
    main()
