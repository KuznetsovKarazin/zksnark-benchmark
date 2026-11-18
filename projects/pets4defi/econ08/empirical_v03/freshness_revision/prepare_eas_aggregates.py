"""Build anonymous hour/slot counts from the earlier Base indexer export and verify daily totals."""
import argparse
import collections
import csv
import datetime as dt
import gzip
import io
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
START=int(dt.datetime(2026,8,19,tzinfo=dt.timezone.utc).timestamp())
PERIODS=(3300,3600,21300,21600,86100,86400)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('private_base_export',type=Path);args=parser.parse_args()
    rows=json.loads((args.private_base_export/'revocations.json').read_text())
    report=json.loads((args.private_base_export/'report.json').read_text())
    assert report['indexer_pagination_complete'] and report['aggregate_matches_pagination']
    grouped=collections.defaultdict(list)
    for row in rows:
        when=row['revocationTime']-START
        assert 0<=when<90*86400 and not row['isOffchain']
        grouped[row['attester'].lower()].append(when)
    sources=sorted(grouped.values(),key=len,reverse=True)[:2]
    measured=json.loads((ROOT.parent/'results/calibrated/calibration.json').read_text())['profiles']
    for source,profile in zip(sources,measured):
        daily=collections.Counter(t//86400 for t in source)
        assert [daily[d] for d in range(90)]==profile['credential_revocations_per_day']
    hours=[collections.Counter(t//3600 for t in times) for times in sources]
    with (ROOT/'results/base_hourly_counts.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['hour_from_window_start','daily_source_count','intermittent_source_count'])
        for hour in range(2160):w.writerow([hour,*(a[hour] for a in hours)])
    buffer=io.StringIO(newline='')
    w=csv.writer(buffer);w.writerow(['period_s','cutoff_offset_s','daily_source_count','intermittent_source_count'])
    for period in PERIODS:
        counts=[collections.Counter((t//period+1)*period for t in times) for times in sources]
        for cutoff in sorted(set(counts[0])|set(counts[1])):
            w.writerow([period,cutoff,*(a[cutoff] for a in counts)])
    (ROOT/'results/eas_slot_counts.csv.gz').write_bytes(gzip.compress(buffer.getvalue().encode(),mtime=0))


if __name__=='__main__':main()
