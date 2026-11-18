"""Independent arithmetic and coverage checks of the published economic packet."""
import collections
import csv
import gzip
import json
import math
import statistics
from pathlib import Path

P=Path(__file__).resolve().parent/'results'
def rows(name):
    file=P/name
    if file.exists():
        with file.open() as f:return list(csv.DictReader(f))
    with gzip.open(str(file)+'.gz','rt') as f:return list(csv.DictReader(f))
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=2e-10,abs_tol=1e-10),(a,b)
def main():
    daily=rows('base_daily_counts.csv')
    counts=[sum(int(r[c]) for r in daily) for c in list(daily[0])[1:]]
    assert len(daily)==90 and counts==[22969,95]
    with gzip.open(P/'eas_slot_counts.csv.gz','rt') as f:slots=list(csv.DictReader(f))
    for sec in {r['period_s'] for r in slots}:
        sl=[r for r in slots if r['period_s']==sec]
        assert [sum(int(r[k]) for r in sl) for k in ('daily_source_count','intermittent_source_count')]==counts
    daily_runs=rows('daily_controls.csv')
    assert len(daily_runs)==320
    for r in daily_runs:
        if r['policy'] in ('common','batch_1d'):close(r['full'],r['accesses'])
    base=json.loads((P.parent.parent/'results/calibrated/summary.json').read_text())
    for r in base:
        close(r['full_per_holder'],statistics.mean(float(s['full']) for s in daily_runs if s['policy']=='selective' and s['issuers']==str(r['issuers'])))
    runs=rows('subdaily_runs.csv');summary=rows('subdaily_summary.csv')
    groups=collections.defaultdict(list)
    key=lambda r:tuple(r[k] for k in ('issuers','access_model','period_s','policy','group_size'))
    for r in runs:
        groups[key(r)].append(r)
        assert 0<=float(r['full'])<=float(r['accesses']) and 0<=float(r['switch_disagreement'])<=1
        if r['policy'] in ('common','batch','issuer_heartbeats'):close(r['switch_disagreement'],0)
        if int(r['period_s']):
            close(int(r['freshness_bound_s']),int(r['period_s'])+300)
            close(float(r['writes_with_liveness']),float(r['empty_liveness_certificates'])+float(r['registry_writes']))
    assert len(runs)==4320 and len(groups)==len(summary)==216
    for row in summary:
        g=groups[key(row)];assert set(int(x['seed']) for x in g)==set(range(20))
        for metric in ('full','accesses','switch_disagreement','registry_writes'):
            v=[float(r[metric]) for r in g];close(row[metric],statistics.mean(v))
            if metric in ('full','switch_disagreement'):
                ci='full_ci95_halfwidth' if metric=='full' else 'disagreement_ci95_halfwidth'
                close(row[ci],2.093024054408263*statistics.stdev(v)/math.sqrt(20))
    coverage=json.loads((P/'aave_interval_coverage.json').read_text())
    assert coverage['covered_days']+len(coverage['errors'])==coverage['days_requested']
    assert coverage['gaps']==sum(coverage['gap_distribution'].values())
    assert coverage['unique_wallet_transactions']-coverage['wallets_one']-2*coverage['wallets_two']-coverage['wallets_three_plus']==coverage['gaps']
    sample=json.loads((P/'trace_costs.json').read_text())
    for r in rows('trace_freshness.csv'):
        close(r['mean_accesses'],sample['eligible_accesses']/sample['eligible_wallets'])
        close(r['selective_equal_source'],(float(r['selective_daily'])+float(r['selective_intermittent']))/2)
        assert float(r['selective_equal_source'])<=float(r['common'])<=float(r['always_batch'])
    q=rows('base_fee_quotes.csv')
    for r in q:
        if r['status']=='quoted':
            assert int(r['l2_plus_l1_wei'])==int(r['l1_data_wei'])+int(r['gas'])*int(r['l2_base_wei_per_gas'])
        else:assert not r['l2_plus_l1_wei']
    signed=json.loads((P/'issuer_epochs.json').read_text())
    assert signed['proof_verified'] and len(signed['checks'])==9
    for label,field in [('empty','empty_epoch_gas'),('one_revocation','changed_epoch_gas')]:
        legs=[v for v in signed['gas'] if v['stage']==label]
        assert len(legs)==4 and signed[field]==sum(leg['gas'] for leg in legs)
    nulls=rows('null_controls.csv')
    assert len(nulls)==10 and max(float(r['maximum_posterior_minus_prior']) for r in nulls)<1e-10
    print('PASS: 320 daily cases, 4,320 paired cases, 216 seed summaries/intervals, 10 null controls, access coverage, fee arithmetic and four-signer gas totals.')

if __name__=='__main__':main()
