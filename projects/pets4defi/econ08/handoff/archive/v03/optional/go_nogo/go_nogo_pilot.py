#!/usr/bin/env python3
"""Conditional financing pilot; machine-readable research outputs, no EVM runs.

Uses Decimal for exact input arithmetic. CSVs are simulation result tables.
Default input is a frozen copy of the original 22-scenario cohort summary.
"""
from pathlib import Path
from decimal import Decimal as D, getcontext
import argparse, csv, hashlib, json

getcontext().prec = 40
Q0 = D('0.130658648')
EUR_ETH = D('2164.73')
Q_GRID = tuple(map(D, ['0', '0.01', '0.1', str(Q0), '1', '10', '100', '1000']))
POPULATIONS = (4, 32)
SPONSOR_FACTORS = tuple(map(D, ['0', '0.5', '1', '1.5', '2']))
EXPECTED = {1: (13817033, 10653405), 2: (16592944, 8930165), 4: (24791056, 8068512)}

def scale(q):
    assert q >= 0
    return q * D('1e-9') * EUR_ETH

def read_anchors(path):
    anchors = {}
    with path.open(newline='') as f:
        for r in csv.DictReader(f):
            for b in (1, 2, 4):
                if r['scenario'] == f'N16_zk_B{b}_d0_HIGH_weekly':
                    wallets = int(r['observed_wallets'])
                    shared = sum(D(r[k]) for k in ('operator_setup', 'initial_publication', 'status_publication'))
                    holder = D(r['holder_cohort']) / wallets
                    assert wallets == 4 and int(r['updates']) == 12
                    assert shared + wallets * holder == D(r['measured_boundary_gas'])
                    assert (shared, holder) == tuple(map(D, EXPECTED[b]))
                    anchors[b] = {'S_gas': shared, 'h_gas': holder, 'source_scenario': r['scenario']}
    assert set(anchors) == {1, 2, 4}
    return anchors

def cost(anchors, b, A, q):
    z=anchors[b]
    S=z['S_gas']*scale(q)
    h=z['h_gas']*scale(q)
    return S, h, S+A*h

def budget_min(anchors, b, A, q, s, architecture):
    assert A>0 and s>=0
    S,h,C=cost(anchors,b,A,q)
    if architecture == 'free_transfers': return max(D(0),(C-s)/A)
    if architecture == 'operator_only_sponsor': return h if s>=S else None
    raise ValueError(architecture)

def feasible_set(anchors,A,q,s,budget,architecture,minimum_issuer_set=1):
    return [b for b in anchors if 4//b>=minimum_issuer_set and
            (m:=budget_min(anchors,b,A,q,s,architecture)) is not None and m<=budget]

def serialize(v):
    if isinstance(v,D): return str(v)
    if isinstance(v,dict): return {str(k):serialize(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [serialize(x) for x in v]
    return v

def write_csv(path, rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader()
        for r in rows:w.writerow(serialize(r))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,default=Path(__file__).with_name('source_cohort_summary.csv'))
    ap.add_argument('--out',type=Path,default=Path(__file__).parent)
    args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    anchors=read_anchors(args.source)
    rows=[]; comparisons=[]; tested=0; free_reversals=0; restricted_reversals=0
    # Fixed scenario caps are parameterized from an observed cost, not treated as budgets evidence.
    S2_ref=cost(anchors,2,4,Q0)[0]
    for A in POPULATIONS:
        for q in Q_GRID:
            for b in anchors:
                S,h,C=cost(anchors,b,A,q)
                comparisons.append({'A_active':A,'q_gwei':q,'B':b,'shared_eur':S,
                    'holder_direct_eur':h,'total_resource_eur':C,'total_per_holder_eur':C/A,
                    'evidence':'measured_A4_anchor' if A==4 else 'linear_projection_not_EVM',
                    'source_scenario':anchors[b]['source_scenario']})
            for factor in SPONSOR_FACTORS:
                s=factor*S2_ref
                for architecture in ('free_transfers','operator_only_sponsor'):
                    for b in anchors:
                        bm=budget_min(anchors,b,A,q,s,architecture)
                        rows.append({'architecture':architecture,'A_active':A,'q_gwei':q,'B':b,
                            'sponsor_cap_eur':s,'sponsor_factor_of_B2_shared_at_q0':factor,
                            'holder_min_budget_eur':'' if bm is None else bm,
                            'operator_cap_sufficient':s>=cost(anchors,b,A,q)[0],
                            'status':'feasible_at_reported_holder_budget' if bm is not None else 'operator_funding_gap',
                            'scope':'gas_only_synthetic_funding_rules'})
                # Check every exact frontier boundary and each interval midpoint, not an arbitrary budget grid.
                thresholds={D(0)}
                for arch in ('free_transfers','operator_only_sponsor'):
                    thresholds.update(m for b in anchors if (m:=budget_min(anchors,b,A,q,s,arch)) is not None)
                thresholds=sorted(thresholds)
                points=set(thresholds)|{(x+y)/2 for x,y in zip(thresholds,thresholds[1:])}
                points.add(thresholds[-1]+D(1))
                for minset in (1,2,4):
                    allowed=[b for b in anchors if 4//b>=minset]
                    minC=min(cost(anchors,b,A,q)[2] for b in allowed)
                    for cap in points:
                        for arch in ('free_transfers','operator_only_sponsor'):
                            feasible=feasible_set(anchors,A,q,s,cap,arch,minset)
                            reversal=bool(feasible) and min(cost(anchors,b,A,q)[2] for b in feasible)>minC
                            tested+=1
                            if arch=='free_transfers':
                                free_reversals+=int(reversal)
                                # Closed-form feasibility equivalence and no-reversal theorem.
                                for b in allowed:
                                    assert (b in feasible)==(cost(anchors,b,A,q)[2]<=s+A*cap)
                                assert not reversal
                            else: restricted_reversals+=int(reversal)
    write_csv(args.out/'budget_frontiers.csv',rows)
    write_csv(args.out/'cost_anchors.csv',comparisons)
    S4,h4,_=cost(anchors,4,4,Q0)
    _,h2,_=cost(anchors,2,4,Q0)
    witness=[]
    for A,s,cap,label in [(4,S4,(h2+h4)/2,'holder_route_limit'),
                          (32,(S2_ref+S4)/2,h2,'operator_funding_limit')]:
        raw_min=min(anchors,key=lambda b:cost(anchors,b,A,Q0)[2])
        restricted=feasible_set(anchors,A,Q0,s,cap,'operator_only_sponsor')
        free=feasible_set(anchors,A,Q0,s,cap,'free_transfers')
        assert raw_min not in restricted and raw_min in free
        assert restricted
        witness.append({'case':label,'A_active':A,'q_gwei':Q0,'sponsor_cap_eur':s,
            'holder_cap_eur':cap,'unconstrained_cheapest_B':raw_min,
            'restricted_feasible_B':restricted,'free_transfer_feasible_B':free,
            'interpretation':'constructed existence example; not empirical funding limits or a journal-ready result'})
    # q=0, exact boundaries, privacy singleton and negative-input safeguards.
    for A in POPULATIONS:
        for b in anchors:
            assert budget_min(anchors,b,A,D(0),D(0),'free_transfers')==0
            assert budget_min(anchors,b,A,D(0),D(0),'operator_only_sponsor')==0
            S,h,C=cost(anchors,b,A,Q0)
            assert budget_min(anchors,b,A,Q0,S,'operator_only_sponsor')==h
            assert budget_min(anchors,b,A,Q0,S-D('1e-20'),'operator_only_sponsor') is None
            assert budget_min(anchors,b,A,Q0,C,'free_transfers')==0
            assert budget_min(anchors,b,A,Q0,D(0),'free_transfers')==C/A
    corrections=[]
    for A in POPULATIONS:
        for i,j in [(1,2),(2,4)]:
            si,hi,ci=cost(anchors,i,A,Q0);sj,hj,cj=cost(anchors,j,A,Q0)
            corrections.append({'A_active':A,'comparison':f'B{i}_minus_B{j}',
                'direct_holder_eur':hi-hj,'full_boundary_per_holder_eur':(ci-cj)/A})
    report={'scope':'pre-experiment algebraic financing pilot; no EVM, no off-chain prices, no L2 fee evidence',
        'reference_price':{'q0_gwei':Q0,'eur_per_eth':EUR_ETH,'kind':'historical_ECON07_reference_not_current_quote'},
        'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'anchors':anchors,'q_grid_gwei':Q_GRID,'active_holder_grid':POPULATIONS,
        'cost_corrections':corrections,'constructed_witnesses':witness,
        'checks':{'scenario_threshold_checks':tested,'free_transfer_reversals':free_reversals,
            'restricted_rule_reversal_checks':restricted_reversals,'boundary_checks':'passed',
            'raw_anchor_reconciliation':'passed'},
        'decision':'NO-GO for the claim that a gas-price sweep with unrestricted transfers changes the optimal design. Conditional GO only for a justified restricted-payment/liquidity model and independently demonstrated materiality; frontier and no-reversal result are useful diagnostics, not sufficient publication novelty.',
        'limitations':['A=32 is a frozen-cost projection from the four-wallet N16 workload, not an EVM result. It is not an N16/A32 deployment: an actual cohort needs N>=32 and remeasurement of shared costs.',
            'S includes deployment and all shared publications; it is not initial liquidity.',
            'Operator-only sponsorship is a deliberately explicit scenario restriction, not observed practice.',
            'Sponsor caps in the sweep are scenarios expressed as multiples of observed B2 shared cost.',
            'No empirical threshold X gwei, L2 comparison or market viability is established.',
            'Dynamic liquidity needs timed events and receipts; terminal costs cannot measure it.']}
    (args.out/'go_nogo_results.json').write_text(json.dumps(serialize(report),indent=2)+'\n')
    print(json.dumps({'rows':len(rows),'cost_rows':len(comparisons),'checks':tested,
        'free_reversals':free_reversals,'restricted_reversal_checks':restricted_reversals,
        'witnesses':serialize(witness)},indent=2))

if __name__=='__main__': main()
