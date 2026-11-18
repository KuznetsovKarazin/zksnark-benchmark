"""Paired operating-cost experiment. Only aggregate mechanism responses leave the simulator."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import t as student

ROOT = Path(__file__).resolve().parent
DAY, LAG, HORIZON = 86400, 300, 90 * 86400
TTL = 30 * DAY
PERIODS = [3300, 3600, 21300, 21600, 86100, 86400]


def windows(hourly, issuers, seed):
    """Measured hour counts, synthetic seconds inside each hour; distinguish cloned sources."""
    rng = np.random.default_rng([1001, seed])
    times = []
    for issuer in range(issuers):
        bins = hourly[:, issuer % 2]
        if issuers > 2:
            bins = np.roll(bins, 24 * rng.integers(90))
        hours = np.repeat(np.arange(len(bins)), bins)
        times.append(np.sort(hours * 3600 + rng.integers(0, 3600, len(hours))))
    return times


def access_paths(seed, session, n):
    rng = np.random.default_rng([302, seed])
    active = rng.random((90, n)) < (.225 if session else .45)
    spacing = 1200 if session else 0
    starts = np.arange(90)[:, None] * DAY + rng.integers(0, DAY - spacing, (90, n))
    dates = np.where(active, starts, HORIZON + 1)
    if session:
        dates = np.concatenate((dates, np.where(active, starts + spacing, HORIZON + 1)))
    dates.sort(axis=0)
    dates = dates[:int(active.sum(axis=0).max()) * (2 if session else 1)]
    coins = np.random.default_rng([513, seed]).random(dates.shape)
    return dates, coins


def publish(events, period):
    events = events[events > 0]  # the genesis root already covers the origin
    if period:
        # Right-closed cutoff, then deterministic ingestion/publication lag.
        times = ((events + period - 1) // period) * period + LAG
    else:
        times = events + LAG
    return np.unique(times[times < HORIZON])


def grouped_streams(streams, order, size):
    groups = []
    for start in range(0, len(order), size):
        indices = order[start:start + size]
        groups.append((indices, np.unique(np.concatenate([streams[i] for i in indices]))))
    return groups


def interval_counts(stream, dates):
    cumulative = np.searchsorted(stream, dates, side="right")
    return np.diff(cumulative, axis=0, prepend=0)


def proofs(dates, changes):
    active = dates < HORIZON
    last = np.full(dates.shape[1], -TTL, dtype=np.int64)
    decisions = np.zeros(dates.shape, dtype=bool)
    for idx, current in enumerate(dates):
        full = active[idx] & (changes[idx] | (current - last >= TTL))
        last[full] = current[full]
        decisions[idx] = full
    return decisions


def evaluate(groups, dates, total_issuers, cover_coins=None):
    """Uniform issuer weighting, identical paths. Common coins couple randomized cover."""
    total = np.zeros(dates.shape, dtype=int)
    by_class = np.zeros(2)
    n = dates.shape[1]
    counts = [interval_counts(stream, dates) for _, stream in groups]
    summed = sum(counts) if cover_coins is not None else None
    for (indices, _), own in zip(groups, counts):
        changed = own > 0
        if cover_coins is not None:
            cover_prob = 1 - np.exp2(-(summed - own).astype(float))
            changed |= cover_coins < cover_prob
        full = proofs(dates, changed)
        total += len(indices) * full
        for k in (0, 1):
            by_class[k] += np.count_nonzero(indices % 2 == k) * full.sum() / n
    active_count = np.count_nonzero(dates < HORIZON)
    # Two distinct possible issuers, same path and random cover coin at each access.
    disagreement = (2 * total * (total_issuers - total)).sum() / (total_issuers * (total_issuers-1) * active_count)
    return [active_count/n, total.sum()/(n*total_issuers), *list(by_class/(total_issuers/2)),
            disagreement, sum(len(s) for _, s in groups)]


def cases(issuers, seed, dates, coins, streams, period):
    order = np.arange(issuers)
    singleton = grouped_streams(streams, order, 1)
    yield "selective", 1, evaluate(singleton, dates, issuers)
    yield "cover_0.5", 1, evaluate(singleton, dates, issuers, coins)
    common = grouped_streams(streams, order, issuers)
    yield "common", issuers, evaluate(common, dates, issuers)
    random_order = np.random.default_rng([835, seed]).permutation(issuers)
    sorted_order = np.argsort(order % 2, kind="stable")
    for size in (2, 4, 8):
        if size >= issuers:
            continue
        for label, perm in (("random", random_order), ("like_rate", sorted_order)):
            groups = grouped_streams(streams, perm, size)
            yield "group_" + label, size, evaluate(groups, dates, issuers)
    if period:
        # Origin includes a valid root; skip a duplicate first heartbeat at time zero.
        heartbeats = np.arange(period + LAG, HORIZON, period)
        result = evaluate([(order, heartbeats)], dates, issuers)
        yield "batch", issuers, result
        # B independent direct signatures and a common epoch; access counts unchanged.
        independent = result.copy()
        independent[-1] *= issuers
        yield "issuer_heartbeats", issuers, independent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--paths", type=int, default=256)
    p.add_argument("--out", type=Path, default=ROOT/"results")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    hourly = np.loadtxt(ROOT/"results/base_hourly_counts.csv", delimiter=",", skiprows=1, dtype=int)[:, 1:]
    header = ["issuers","access_model","period_s","freshness_bound_s","policy","group_size","seed",
              "accesses","full","full_daily","full_intermittent","switch_disagreement","registry_writes","empty_liveness_certificates","writes_with_liveness"]
    rows = []
    for seed in range(args.seeds):
        for b in (2,16):
            events = windows(hourly, b, seed)
            paths = [(name, *access_paths(seed, session, args.paths))
                     for name,session in (("single",False),("session",True))]
            for period in [0] + PERIODS:
                streams = [publish(e, period) for e in events]
                for name, dates, coins in paths:
                    for policy, size, values in cases(b,seed,dates,coins,streams,period):
                        # A hard silence deadline also requires a signed no-change message.
                        # Such messages authenticate freshness without invalidating caches.
                        # Direct heartbeat/batch invalidate on every slot by definition.
                        if period:
                            slots=(HORIZON-1-LAG)//period
                            groups=b//size if policy not in ("common","batch") else 1
                            if policy=="issuer_heartbeats":groups=b
                            empty=slots*groups-values[-1]
                            assert empty>=0
                        else:
                            empty=float("nan")  # prompt feed alone assumes bounded reliable notification
                        rows.append([b,name,period,period+LAG,policy,size,seed,*values,empty,empty+values[-1]])
        print(f"Completed seed {seed}", flush=True)
    with (args.out/"subdaily_runs.csv").open("w") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[:6])].append(r[7:])
    with (args.out/"subdaily_summary.csv").open("w") as file:
        writer = csv.writer(file)
        writer.writerow(header[:6]+["seeds"]+header[7:]+["full_ci95_halfwidth","disagreement_ci95_halfwidth"])
        for key, vals in groups.items():
            a = np.asarray(vals)
            se = a[:, [1,4]].std(axis=0,ddof=1)/np.sqrt(len(a)) if len(a)>1 else np.full(2,np.nan)
            writer.writerow(list(key)+[len(a)]+list(a.mean(axis=0))+list(student.ppf(.975,len(a)-1)*se))


if __name__ == "__main__":
    main()
