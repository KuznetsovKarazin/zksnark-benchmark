"""Summarize the fixed paired cost and cache-response experiment by access cohort."""
import argparse
import csv
import gzip
import json
from pathlib import Path

import numpy as np

from access_paths import DAY, RESULTS, load_paths, timestamp

TTL = 30 * DAY
ORIGIN = timestamp("2026-08-19")
LAG = 300


def full_flags(times, starts, publications):
    epochs = np.searchsorted(publications, times, side="right")
    result = np.empty(len(times), dtype=bool)
    last_full = -TTL
    previous_epoch = -1
    for i, (t, first, current_epoch) in enumerate(zip(times, starts, epochs)):
        full = first or current_epoch != previous_epoch or t - last_full >= TTL
        result[i] = full
        if full:
            last_full = t
        previous_epoch = current_epoch
    return result


def schedules(lo, hi, period, rows):
    selected = [r for r in rows if int(r["period_s"]) == period]

    def updates(column):
        cutoffs = sorted({ORIGIN + int(r["cutoff_offset_s"]) + LAG for r in selected if int(r[column]) > 0})
        return np.array([s for s in cutoffs if lo <= s < hi], dtype=np.int64)

    active, quiet = (updates(c) for c in ("daily_source_count", "intermittent_source_count"))
    batch = np.arange(ORIGIN + period + LAG, hi, period)
    return active, quiet, np.union1d(active, quiet), batch[batch >= lo]


def summaries(paths, code, lo, hi):
    keys = sorted(paths)
    sizes = np.array([len(paths[k]) for k in keys])
    times = np.concatenate([paths[k] for k in keys])
    offsets = np.r_[0, np.cumsum(sizes[:-1])]
    starts = np.zeros(len(times), dtype=bool)
    starts[offsets] = True
    gaps = np.r_[0, np.diff(times)]
    short = np.add.reduceat((~starts & (gaps < 3600)).astype(int), offsets)
    same = np.add.reduceat((~starts & (gaps == 0)).astype(int), offsets)
    max_day = np.array([np.max(np.unique(np.asarray(paths[k]) // DAY, return_counts=True)[1]) for k in keys])
    cuts = np.quantile(sizes, [.25, .50, .75], method="inverted_cdf").astype(int)
    quartiles = np.searchsorted(cuts, sizes, side="left") + 1
    kind = np.array([code[k] for k in keys])
    empty = kind == "empty"
    masks = {"all": np.ones(len(keys), dtype=bool), "empty": empty,
             "delegated": kind == "delegated", "other_code": kind == "other_code",
             "unknown": kind == "unknown", "empty_or_delegated": np.isin(kind, ["empty", "delegated"])}
    for cap in (10, 25, 50):
        bounded = max_day <= cap
        masks[f"cap_{cap}"] = bounded
        masks[f"empty_cap_{cap}"] = empty & bounded
    for q in range(1, 5):
        masks[f"quartile_{q}"] = quartiles == q
        masks[f"empty_quartile_{q}"] = empty & (quartiles == q)
    descriptive, costs = [], []
    for name, mask in masks.items():
        n = int(mask.sum())
        gap_count = int((sizes[mask] - 1).sum())
        descriptive.append(dict(
            cohort=name, wallets=n, accesses=int(sizes[mask].sum()), gaps=gap_count,
            short_gaps=int(short[mask].sum()), zero_gaps=int(same[mask].sum()),
            pooled_short_fraction=float(short[mask].sum() / gap_count) if n else None,
            wallet_mean_short_fraction=float(np.mean(short[mask] / (sizes[mask] - 1))) if n else None,
            min_accesses=int(sizes[mask].min()) if n else None, max_accesses=int(sizes[mask].max()) if n else None,
        ))
    with gzip.open(RESULTS / "eas_slot_counts.csv.gz", "rt") as stream:
        rows = list(csv.DictReader(stream))
    for period in (3300, 21300, 86100):
        flags = [full_flags(times, starts, boundaries) for boundaries in schedules(lo, hi, period, rows)]
        active, intermittent, common, batch = [np.add.reduceat(a.astype(int), offsets) for a in flags]
        disagreements = np.add.reduceat((flags[0] != flags[1]).astype(int), offsets)
        if np.any(disagreements > sizes):
            raise ValueError("Invalid paired response count")
        for name, mask in masks.items():
            n = int(mask.sum())
            if not n:
                continue
            sums = [int(v[mask].sum()) for v in (active, intermittent, common, batch, disagreements)]
            daily_sum, quiet_sum, common_sum, batch_sum, different = sums
            accesses = int(sizes[mask].sum())
            selective = (daily_sum + quiet_sum) / (2 * n)
            costs.append(dict(
                cohort=name, F_hours=(period + LAG) // 3600, wallets=n, accesses=accesses,
                daily_full_sum=daily_sum, intermittent_full_sum=quiet_sum,
                common_full_sum=common_sum, batch_full_sum=batch_sum,
                selective_equal_full=selective, common_full=common_sum / n, fixed_batch_full=batch_sum / n,
                common_minus_selective=common_sum / n - selective,
                quiet_extra_under_common=(common_sum - quiet_sum) / n,
                selective_pair_disagreements=different, selective_switch_access_weighted=different / accesses,
                selective_switch_wallet_weighted=float(np.mean(disagreements[mask] / sizes[mask])),
                shared_switch_access_weighted=0, fixed_switch_access_weighted=0,
            ))
    return descriptive, costs, cuts.tolist()


def write_csv(path, rows):
    with path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-aave", required=True, type=Path)
    parser.add_argument("--private-code-cache", required=True, type=Path)
    args = parser.parse_args()
    paths, lo, hi, anchor = load_paths(args.private_aave)
    stored = json.loads(args.private_code_cache.read_text())
    if stored["block_hash"] != anchor["last_hash"] or stored["block_number"] != anchor["end_block"]:
        raise ValueError("Historical state and activity windows disagree")
    kinds = stored["kinds"]
    if set(paths) != set(kinds) or not set(kinds.values()) <= {"empty", "other_code", "delegated", "unknown"}:
        raise ValueError("Every eligible address needs an explicit lookup status")
    descriptive, costs, cuts = summaries(paths, kinds, lo, hi)
    write_csv(RESULTS / "aave_activity_cohorts.csv", descriptive)
    write_csv(RESULTS / "aave_cohort_frontier.csv", costs)
    info = dict(window_start_utc="2026-09-08", end_exclusive_utc="2026-11-05",
                observed_days=(hi-lo)//DAY, requested_days=180, eligible_wallets=len(paths),
                min_transactions=3, reference_chain_id=8453, closing_block=stored["block_number"],
                closing_block_hash=stored["block_hash"], code_state="eth_getCode at closing block",
                counts_by_code={label: list(kinds.values()).count(label)
                                for label in ("empty","delegated","other_code","unknown")},
                cap_max_per_utc_day=[10,25,50], activity_quartile_cutoffs=cuts,
                period_seconds=[3300,21300,86100], lag_seconds=LAG, ttl_days=30,
                response_units="same-access cache decision for two counterfactual issuer schedules",
                session_records_released=False)
    (RESULTS / "aave_cohort_coverage.json").write_text(json.dumps(info, indent=2) + "\n")


if __name__ == "__main__":
    main()
