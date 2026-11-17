"""Negative controls on fully synthetic paths with issuer-independent common epochs."""
import argparse
import csv
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score
import scipy
import sklearn

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))
from experiment import simulate
from observers import hmm, spectral

FIELDS = ["seed", "issuer_labels", "clustering_n", "calibration_n", "estimated_label_error",
          "estimated_missing", "maximum_posterior_minus_prior", "null_ari", "null_ami"]


def common_epoch_control(seed, labels_n, count):
    calibration = np.random.default_rng([900, seed])
    hidden = calibration.random(1000) < .10
    flipped = calibration.random(1000) < .10
    missing = (hidden.sum() + .5) / (len(hidden) + 1)
    error = (flipped[~hidden].sum() + .5) / ((~hidden).sum() + 1)

    rng = np.random.default_rng([462, seed, labels_n])
    updates = np.zeros((labels_n, 90), dtype=int)
    updates[:, ::3] = 1
    labels = rng.integers(labels_n, size=count)
    activity = np.full(count, .45)
    obs, _, _ = simulate(updates, labels, activity, rng, policy="common", label_error=.10, missing=.10)
    prior = np.arange(1, labels_n + 1, dtype=float)
    prior /= prior.sum()
    post = hmm(obs[:32], updates, activity[:32], policy="common", prior=prior,
               label_error=error, missing=missing)
    drift = float(np.max(abs(post - prior)))
    if drift >= 1e-10:
        raise ValueError("Issuer-independent synthetic channel changed the prior")
    clusters = spectral(obs, labels_n, seed)
    return [seed, labels_n, count, 1000, error, missing, drift,
            adjusted_rand_score(labels, clusters), adjusted_mutual_info_score(labels, clusters)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clustering-n", type=int, choices=(1000, 10000), default=1000)
    parser.add_argument("--workers", type=int, choices=(1,2,3,4), default=1)
    parser.add_argument("--output", type=Path, help="Optional alternative aggregate CSV destination")
    parser.add_argument("--checkpoint-dir", type=Path, help="Save aggregate results from individual null cases for restart")
    args = parser.parse_args()
    cases = [(seed, labels, args.clustering_n) for seed in range(5) for labels in (4, 64)]
    completed = {}
    if args.checkpoint_dir:
        args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        sources = [Path(__file__), ROOT.parent / "src" / "experiment.py", ROOT.parent / "src" / "observers.py"]
        signature = hashlib.sha256(b"".join(f.read_bytes() for f in sources) +
            repr((np.__version__,scipy.__version__,sklearn.__version__)).encode()).hexdigest()[:16]
        for case in cases:
            path = args.checkpoint_dir / ("-".join(map(str, case)) + "-" + signature + ".json")
            if path.is_file():
                row = json.loads(path.read_text())
                if tuple(row[:3]) != case or len(row) != len(FIELDS):
                    raise ValueError("Invalid null-control checkpoint")
                completed[case] = row

    def record(row):
        case = tuple(row[:3])
        if args.checkpoint_dir:
            path = args.checkpoint_dir / ("-".join(map(str, case)) + "-" + signature + ".json")
            with NamedTemporaryFile("w", dir=path.parent, delete=False) as tmp:
                json.dump(row, tmp)
            os.replace(tmp.name, path)
        completed[case] = row
        print("Finished common-epoch control", case[:2], flush=True)

    remaining = [case for case in cases if case not in completed]
    if args.workers == 1:
        for case in remaining:
            record(common_epoch_control(*case))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(common_epoch_control, *case) for case in remaining]
            for future in as_completed(futures):
                record(future.result())
    default = "null_controls.csv" if args.clustering_n == 1000 else "null_controls_10000.csv"
    out = args.output or ROOT / "results" / default
    with NamedTemporaryFile("w", newline="", dir=out.parent, delete=False) as temporary:
        writer = csv.writer(temporary)
        writer.writerow(FIELDS)
        writer.writerows(completed[case] for case in cases)
    os.replace(temporary.name, out)


if __name__ == "__main__":
    main()
