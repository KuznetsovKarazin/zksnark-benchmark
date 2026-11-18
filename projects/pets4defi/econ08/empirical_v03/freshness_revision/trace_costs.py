"""Aggregate counterfactual proof demand from real access times and separate source panels."""
import argparse
import csv
import datetime as dt
import gzip
import json
import collections
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
DAY=86400
UTC=dt.timezone.utc


def instant(date):
    return int(dt.datetime.fromisoformat(date).replace(tzinfo=UTC).timestamp())


def full_count(times,starts,publications):
    epochs=np.searchsorted(publications,times,side="right")
    previous_epoch=-1;last_full=-10**18;total=0
    for t,start,epoch in zip(times,starts,epochs):
        if start or epoch!=previous_epoch or t-last_full>=30*DAY:
            last_full=t;total+=1
        previous_epoch=epoch
    return total


def main():
    p=argparse.ArgumentParser();p.add_argument("--private-aave",type=Path,required=True);args=p.parse_args()
    result=HERE/'results';coverage=json.loads((result/'aave_interval_coverage.json').read_text())
    if not coverage.get('aggregate_span_days'):raise ValueError("No usable contiguous access window")
    lo=max(instant(coverage["aggregate_span_start"]),instant("2026-08-19"))
    hi=min(instant(coverage["aggregate_span_end_exclusive"]),instant("2026-11-17"))
    if hi<=lo:raise ValueError("No overlap with original EAS calibration")
    wallets=collections.defaultdict(dict)
    for cache in sorted(args.private_aave.glob('*.json.gz')):
        data=json.loads(gzip.decompress(cache.read_bytes()))
        for w,tx,stamp in data['events']:
            if lo<=stamp<hi:wallets[w][tx]=stamp
    eligible=[np.sort(np.fromiter(v.values(),dtype=np.int64)) for v in wallets.values() if len(v)>=3]
    n=len(eligible);sizes=np.asarray([len(x) for x in eligible]);ts=np.concatenate(eligible)
    starts=np.zeros(len(ts),dtype=bool);starts[np.r_[0,np.cumsum(sizes[:-1])]]=True
    eas=list(csv.DictReader((result/'base_daily_counts.csv').open()))
    panels={'EAS_daily_counts':{name:sorted({instant(r['date_utc']) for r in eas if int(r[column])>0})
            for name,column in [('daily','daily_source_revocations'),('intermittent','intermittent_source_revocations')]}}
    inv=json.loads((result/'web_pki_inventory.json').read_text())
    available={r['cert_sha256']:[] for r in inv['records'] if r['status']=='signed_stock_only' and instant(r['this_update'])>=hi}
    for row in csv.DictReader((result/'web_pki_retained_dates.csv').open()):
        if row['cert_sha256'] in available:available[row['cert_sha256']].append(instant(row['effective_revocation_date']))
    panels['Web_PKI_retained_stock_sensitivity']=available
    def delayed(days):return np.asarray(sorted({d+DAY+300 for d in days if lo<=d+DAY+300<hi}),dtype=np.int64)
    rows=[]
    for label,sources in panels.items():
        if not sources:continue
        per=[full_count(ts,starts,delayed(v))/n for v in sources.values()]
        union=set().union(*(set(v) for v in sources.values()))
        common=full_count(ts,starts,delayed(union))/n
        batch=full_count(ts,starts,np.arange(lo+300,hi,DAY))/n
        rows.append(dict(source_panel=label,source_count=len(sources),selective_equal_source_full=np.mean(per),
                         selective_min=min(per),selective_max=max(per),common_full=common,batch_daily_full=batch,
                         source_specific_eas=dict(zip(sources,per)) if label.startswith("EAS") else None))
    origin=instant("2026-08-19")
    slot_rows=[]
    with gzip.open(result/'eas_slot_counts.csv.gz','rt') as f:
        slot_data=list(csv.DictReader(f))
    for period in (3300,3600,21300,21600,86100,86400):
        slots=[r for r in slot_data if int(r['period_s'])==period]
        def ticks(source):
            return np.asarray(sorted({origin+int(r['cutoff_offset_s'])+300 for r in slots if int(r[source])>0
                                      and lo<=origin+int(r['cutoff_offset_s'])+300<hi}),dtype=np.int64)
        daily=ticks('daily_source_count');quiet=ticks('intermittent_source_count')
        heartbeats=np.arange(origin+period+300,hi,period)
        heartbeats=heartbeats[heartbeats>=lo]
        sources=[full_count(ts,starts,t)/n for t in (daily,quiet)]
        common=full_count(ts,starts,np.union1d(daily,quiet))/n
        batch=full_count(ts,starts,heartbeats)/n
        slot_rows.append(dict(period_s=period,F_s=period+300,mean_accesses=len(ts)/n,selective_daily=sources[0],
                              selective_intermittent=sources[1],selective_equal_source=sum(sources)/2,
                              common=common,always_batch=batch,common_registry_writes=len(np.union1d(daily,quiet)),
                              batch_registry_writes=len(heartbeats)))
    with (result/'trace_freshness.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(slot_rows[0]));w.writeheader();w.writerows(slot_rows)
    payload=dict(window_start=dt.datetime.fromtimestamp(lo,UTC).isoformat(),end_exclusive=dt.datetime.fromtimestamp(hi,UTC).isoformat(),
                 complete_days=(hi-lo)//DAY,all_wallets_in_span=len(wallets),one_access=sum(len(v)==1 for v in wallets.values()),
                 two_access=sum(len(v)==2 for v in wallets.values()),eligible_wallets=n,eligible_accesses=len(ts),mean_accesses=len(ts)/n,
                 freshness_s=DAY+300,period_s=DAY,lag_s=300,ttl_days=30,cold_start=True,outcomes=rows,
                 estimand="Evaluate each eligible path under every source with equal source weights. No observed issuer membership. All policies use the same daily boundary and assumed lag.",
                 selection="Availability-selected contiguous Aave span intersected with original two-source EAS window. Require at least three transactions within that span.",
                 web_pki="Dated retained events in eligible signed snapshots. No complete historical issuance/revocation flows or CA-publication times asserted.")
    (result/'trace_costs.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload))


if __name__=='__main__':main()
