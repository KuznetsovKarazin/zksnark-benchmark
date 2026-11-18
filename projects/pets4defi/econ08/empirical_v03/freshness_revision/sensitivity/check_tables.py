"""Check the public cohort partitions, ratio denominators and previous cost totals."""
import argparse
import csv
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "results"


def rows(file):
    with (DATA / file).open() as f:
        return list(csv.DictReader(f))


def same(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-11), (a, b)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--access-only", action="store_true")
    access_only = parser.parse_args().access_only
    info = json.loads((DATA / "aave_cohort_coverage.json").read_text())
    coverage = json.loads((DATA / "aave_interval_coverage.json").read_text())
    stats = {r["cohort"]: r for r in rows("aave_activity_cohorts.csv")}
    costs = {(r["cohort"], int(r["F_hours"])): r for r in rows("aave_cohort_frontier.csv")}
    count_fields = ("wallets", "accesses", "gaps", "short_gaps", "zero_gaps")
    cohorts = ("empty", "delegated", "other_code", "unknown")
    quartiles = tuple(f"quartile_{i}" for i in range(1, 5))
    partitions = [("all", cohorts), ("all", quartiles),
                  ("empty", tuple("empty_" + x for x in quartiles)),
                  ("empty_or_delegated", ("empty", "delegated"))]
    for target, parts in partitions:
        for name in count_fields:
            assert sum(int(stats[k][name]) for k in parts) == int(stats[target][name])
    for label, count in info["counts_by_code"].items():
        assert count == int(stats[label]["wallets"])
    assert info["observed_days"] == coverage["aggregate_span_days"]
    assert info["requested_days"] == coverage["days_requested"]
    assert info["closing_block_hash"] == max(coverage["ranges"], key=lambda d: d["end_block"])["last_hash"]
    assert int(stats["all"]["gaps"]) == coverage["gaps"]
    assert int(stats["all"]["short_gaps"]) == sum(coverage["gap_distribution"][k] for k in ("same_timestamp","under_1h"))
    previous = {int(r["F_s"])//3600: r for r in rows("trace_freshness.csv") if int(r["F_s"]) % 3600 == 0}
    for h in (1, 6, 24):
        full = costs["all", h]
        for field, old in (("selective_equal_full","selective_equal_source"), ("common_full","common"),
                           ("fixed_batch_full","always_batch")):
            same(full[field], previous[h][old])
        for target, parts in partitions:
            if not int(stats[target]["wallets"]):
                continue
            for field in ("daily_full_sum", "intermittent_full_sum", "common_full_sum", "batch_full_sum",
                          "selective_pair_disagreements"):
                total = sum(int(costs[k,h][field]) for k in parts if int(stats[k]["wallets"]))
                assert total == int(costs[target,h][field])
    for name, row in stats.items():
        n, a, g = [int(row[k]) for k in ("wallets","accesses","gaps")]
        assert g == a-n
        if not n:
            assert not row["pooled_short_fraction"]
            continue
        same(row["pooled_short_fraction"],int(row["short_gaps"])/g)
        assert 0 <= int(row["zero_gaps"]) <= int(row["short_gaps"]) <= g
        assert 0 <= float(row["wallet_mean_short_fraction"]) <= 1
        for h in (1,6,24):
            cost = costs[name,h]
            assert n == int(cost["wallets"]) and a == int(cost["accesses"])
            active,quiet,shared,batch,disagreements = [int(cost[k]) for k in
                ("daily_full_sum","intermittent_full_sum","common_full_sum","batch_full_sum","selective_pair_disagreements")]
            same(cost["selective_equal_full"], (active+quiet)/(2*n))
            same(cost["common_minus_selective"], (2*shared-active-quiet)/(2*n))
            same(cost["quiet_extra_under_common"], (shared-quiet)/n)
            same(cost["selective_switch_access_weighted"], disagreements/a)
            assert 0 <= float(cost["selective_switch_wallet_weighted"]) <= 1
            assert abs(active-quiet) <= disagreements <= a
            # Empirical nesting and common/daily agreement reported for this frozen 58-day sample.
            assert disagreements == active - quiet and shared == active
            assert all(n <= x <= a for x in (active,quiet,shared,batch))
            assert int(cost["shared_switch_access_weighted"]) == int(cost["fixed_switch_access_weighted"]) == 0
    for field in count_fields:
        for prefix in ("", "empty_"):
            seq = [int(stats[f"{prefix}cap_{cap}"][field]) for cap in (10,25,50)]
            assert seq == sorted(seq)
    if access_only:
        print("PASS: code strata, activity quartiles, gap weights, cohort replay and published baseline.")
        return
    nulls = rows("null_controls_10000.csv")
    assert len(nulls)==10 and {(int(r["issuer_labels"]),int(r["seed"])) for r in nulls} == {
        (b,seed) for b in (4,64) for seed in range(5)}
    for r in nulls:
        assert int(r["clustering_n"]) == 10000 and int(r["calibration_n"]) == 1000
        assert float(r["maximum_posterior_minus_prior"]) < 1e-10
        assert all(-1 <= float(r[k]) <= 1 for k in ("null_ari","null_ami"))
    print("PASS: code strata, activity quartiles, both gap weights, cohort replay, published baseline and ten large null runs.")


if __name__ == "__main__":
    main()
