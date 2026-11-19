#!/usr/bin/env python3
"""Counterfactual batching delay on observed EAS revocation timestamps.

L is a scenario assumption, not measured network lag. No holder linkage or
actual registry publication cost is inferred from credential-revocation counts.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def delays(times,period,lag):
    if period<=0 or lag<0:raise ValueError('Invalid cadence')
    times=np.asarray(times,dtype=np.int64)
    return (-times)%period+lag


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-indexer',required=True);p.add_argument('--out',required=True);args=p.parse_args()
    events=[];coalesced=set()
    for chain in ('ethereum','base','optimism'):
        folder=Path(args.private_indexer)/chain;report=json.loads((folder/'report.json').read_text())
        if not report['indexer_pagination_complete'] or not report.get('aggregate_matches_pagination'):raise SystemExit('Incomplete indexer source')
        for row in json.loads((folder/'revocations.json').read_text()):
            events.append(row['revocationTime']);coalesced.add((chain,row['attester'],row['revocationTime']))
    records=[]
    for period in (3300,3600,21300,21600,86100,86400,604800):
        lag=300;d=delays(events,period,lag);c=delays([r[2] for r in coalesced],period,lag)
        records.append(dict(period_seconds=period,assumed_lag_seconds=lag,worst_case_bound_seconds=period+lag,
                            event_weighted_median_seconds=float(np.median(d)),event_weighted_p95_seconds=float(np.quantile(d,.95)),
                            coalesced_publication_proxy_median_seconds=float(np.median(c)),
                            meets_one_hour_bound=period+lag<=3600,meets_one_day_bound=period+lag<=86400))
    result=dict(source='Complete on-chain-only EAS indexer screen; chain-log coverage not independently verified',
                observation_count=len(events),unique_issuer_timestamp_count=len(coalesced),
                interpretation='Computed scenario delays, not measured publication latency; cadence origin is Unix epoch',rows=records)
    Path(args.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
