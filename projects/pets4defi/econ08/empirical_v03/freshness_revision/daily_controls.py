"""Replay cost controls using the v0.3 daily access draws and cache simulator."""
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / "src"))
from experiment import simulate


def main():
    measured = json.loads((BASE / "results/calibrated/calibration.json").read_text())
    profiles = [p["credential_revocations_per_day"] for p in measured["profiles"]]
    start = dt.date.fromisoformat(measured["window_start"][:10])
    with (HERE / "results/base_daily_counts.csv").open("w") as file:
        writer = csv.writer(file)
        writer.writerow(["date_utc", "daily_source_revocations", "intermittent_source_revocations"])
        for day, counts in enumerate(zip(*profiles)):
            writer.writerow([start + dt.timedelta(days=day), *counts])
    rows = []
    for issuers in (2, 4, 16, 64):
        for seed in range(20):
            for policy in ("selective", "common", "batch_1d", "batch_7d"):
                rng = np.random.default_rng(seed)
                if issuers == 2:
                    schedules = np.asarray(profiles)
                else:
                    schedules = np.stack([np.roll(profiles[i % 2], rng.integers(90)) for i in range(issuers)])
                assignments = rng.integers(issuers, size=1000)
                model = "batch" if policy.startswith("batch") else policy
                _, full, accessed = simulate(schedules, assignments, np.full(1000, .45), rng,
                                             policy=model, period=7 if policy == "batch_7d" else 1)
                rows.append((issuers, seed, policy, accessed.mean(), full.mean(),
                             full[assignments % 2 == 0].mean(), full[assignments % 2 == 1].mean()))
    with (HERE / "results/daily_controls.csv").open("w") as file:
        writer = csv.writer(file)
        writer.writerow(["issuers", "seed", "policy", "accesses", "full", "full_daily_source", "full_intermittent_source"])
        writer.writerows(rows)
    baseline = json.loads((BASE / "results/calibrated/summary.json").read_text())
    for row in baseline:
        values = [r[4] for r in rows if r[0] == row["issuers"] and r[2] == "selective"]
        assert np.isclose(np.mean(values), row["full_per_holder"], rtol=0, atol=1e-12)
    assert all(r[3] == r[4] for r in rows if r[2] in ("common", "batch_1d"))
    print("320 paired daily cases, including reproduction of all three published selective means.")


if __name__ == "__main__":
    main()
