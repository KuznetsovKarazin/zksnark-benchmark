"""Translate modeled access counts into paired historical Base execution and L1 data fees."""
import collections
import csv
import json
import statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
U=10**12  # wei per micro-ETH
def main():
    p=ROOT/'results'
    with (p/'base_fee_quotes.csv').open() as f:rows=list(csv.DictReader(f))
    days=collections.defaultdict(dict)
    for r in rows:
        if r['status']=='quoted':
            assert int(r['l2_plus_l1_wei'])==int(r['l2_wei'])+int(r['l1_data_wei'])
            assert int(r['l2_wei'])==int(r['gas'])*int(r['l2_base_wei_per_gas'])
            days[r['date']][r['kind']]=int(r['l2_plus_l1_wei'])
    kinds={r['kind'] for r in rows}
    paired={d:p for d,p in days.items() if set(p)==kinds}
    def percentiles(v):
        q=statistics.quantiles(v,n=10,method='inclusive') if len(v)>1 else v*9
        return [q[0]/U,statistics.median(v)/U,q[-1]/U]
    if not paired:raise ValueError('No complete paired fee checkpoints')
    with (p/'base_fee_components.csv').open('w') as f:
        wr=csv.writer(f);wr.writerow(['component','paired_days','p10_microETH','median_microETH','p90_microETH'])
        for k in sorted(kinds):wr.writerow([k,len(paired),*percentiles([v[k] for v in paired.values()])])
        wr.writerow(['four_signed_empty_updates_sum',len(paired),*percentiles([sum(v['issuer_'+str(i)] for i in range(1,5)) for v in paired.values()])])
    table=list(csv.DictReader((p/'trace_freshness.csv').open()))
    with (p/'base_access_costs.csv').open('w') as f:
        wr=csv.writer(f);wr.writerow(['F_s','policy','paired_fee_days','mean_accesses','full_per_holder','p10_microETH','median_microETH','p90_microETH'])
        for case in table:
            for k in ['selective_equal_source','common','always_batch']:
                total=float(case['mean_accesses']);full=float(case[k])
                costs=[full*v['full_zk']+(total-full)*v['hit'] for v in paired.values()]
                wr.writerow([case['F_s'],k,len(costs),total,full,*percentiles(costs)])
    print('Paired quote days',len(paired),'of',len(set(r['date'] for r in rows)))


if __name__=='__main__':main()
