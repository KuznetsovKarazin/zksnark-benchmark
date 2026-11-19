"""Load deduplicated Aave access times for the published overlap; private memory only."""
import datetime as dt
import gzip
import json
from collections import defaultdict
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"
DAY = 86400


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp())


def load_paths(path):
    coverage = json.loads((RESULTS / "aave_interval_coverage.json").read_text())
    lo = timestamp(coverage["aggregate_span_start"])
    hi = timestamp(coverage["aggregate_span_end_exclusive"])
    if (lo, hi) != (timestamp("2026-09-08"), timestamp("2026-11-05")):
        raise ValueError("This sensitivity is defined on the frozen 58-day overlap")
    days = sorted(coverage["ranges"], key=lambda day: day["day"])
    origin = timestamp(coverage["start_utc"])
    days = [d for d in days if lo <= origin + d["day"] * DAY < hi]
    if len(days) != (hi - lo) // DAY or any(b["day"] != a["day"] + 1 for a, b in zip(days, days[1:])):
        raise ValueError("Incomplete contiguous span")
    transactions = defaultdict(dict)
    for day in days:
        with gzip.open(path / f"{day['day']:03}.json.gz", "rt") as stream:
            cached = json.load(stream)
        for key in ("day", "start_block", "end_block", "first_hash", "last_hash"):
            if cached[key] != day[key]:
                raise ValueError("Archive manifest mismatch")
        if len(cached["events"]) != day["event_count"]:
            raise ValueError("Event count mismatch")
        for address, tx_hash, event_time in cached["events"]:
            if not lo <= event_time < hi:
                raise ValueError("Event outside observed span")
            seen = transactions[address.lower()].setdefault(tx_hash, event_time)
            if seen != event_time:
                raise ValueError("Conflicting time within transaction")
    paths = {who: sorted(entries.values()) for who, entries in transactions.items() if len(entries) >= 3}
    if len(transactions) != coverage["distinct_wallets"] or len(paths) != coverage["wallets_three_plus"]:
        raise ValueError("Cohort totals differ from published Base window")
    return paths, lo, hi, days[-1]
