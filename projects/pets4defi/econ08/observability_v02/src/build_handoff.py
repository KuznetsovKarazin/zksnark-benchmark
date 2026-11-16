"""Generate the small economic handoff from verified technical results."""
import argparse
import csv
import math
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(root, name):
    with (root/name).open(newline='') as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(results, out):
    out.mkdir(parents=True, exist_ok=True)
    coalitions = read(results, 'coalition_costs.csv')
    transfers = read(results, 'compensation_reference.csv')
    cases = read(results, 'economic_cases.csv')
    rows = []
    for case in ['weekly_A4', 'weekly_A32', 'asymmetric_A32']:
        common = next(r for r in cases if r['case']==case and r['policy']=='common')
        resource_total = float(common['holder_access_gas_proxy'])
        for rule in ['SELF', 'publication_frequency', 'shapley_externality']:
            tx = [r for r in transfers if r['case']==case and r['rule']==rule]
            block = []
            for kind in ['holder_group', 'issuer']:
                for issuer in range(1,5):
                    full = ';'.join(str(i) for i in range(1,5) if i!=issuer)
                    c = next(r for r in coalitions if r['case']==case
                             and r['target_issuer']==str(issuer)
                             and r['foreign_issuers']==full)
                    resource = int(c['access_gas_proxy']) if kind=='holder_group' else 0
                    paid = sum(float(r['reimbursement_gas_equivalent']) for r in tx
                               if r['paying_issuer']==str(issuer)) if kind=='issuer' else 0
                    received = sum(float(r['reimbursement_gas_equivalent']) for r in tx
                                   if r['holder_group_issuer']==str(issuer)) if kind=='holder_group' else 0
                    block.append(dict(case=case, rule=rule, actor=f'{kind}_{issuer}',
                        holder_access_gas=resource, compensation_paid_gas_eq=paid,
                        compensation_received_gas_eq=received,
                        net_cost_gas_eq=resource+paid-received, euro_per_gas='',
                        net_cost_eur='', notes=(f"{c['holders']} active holders; access-only scope"
                            if kind=='holder_group' else
                            'publication/setup/settlement costs excluded, not zero lifecycle cost')))
            assert math.isclose(sum(r['holder_access_gas'] for r in block), resource_total, abs_tol=1e-6)
            assert math.isclose(sum(r['net_cost_gas_eq'] for r in block), resource_total, abs_tol=1e-6)
            assert math.isclose(sum(r['compensation_paid_gas_eq'] for r in block),
                                sum(r['compensation_received_gas_eq'] for r in block), abs_tol=1e-6)
            rows.extend(block)
    write(out/'payment_comparison_REFERENCE.csv', rows)
    fee=json.loads((ROOT/'handoff/price_source_fee_snapshot.json').read_text())
    fx=json.loads((ROOT/'handoff/price_source_fx_quote.json').read_text())
    eth=next(n for n in fee['networks'] if n['network']=='ethereum')
    q0=int(eth['summary']['within_block_effective_p50_block_weighted']['p50_wei'])/1e9
    e0=float(fx['value'])
    prices = []
    for multiplier in [1,10,100]:
        prices.append(dict(scenario=('historical_reference' if multiplier==1 else f'hypothetical_x{multiplier}'),
            gas_price_gwei=q0*multiplier, eth_price_eur=e0,
            euro_per_gas=q0*multiplier*1e-9*e0,
            status=('historical October 2026 reference; not a current quote' if multiplier==1 else
                    'sensitivity only; common multiplier across actors and rules'),
            sources='Repository examples/pets4defi_access_v2/results/fee_snapshot.json and projects/pets4defi/data/fx_quote.json; see PRICE_SOURCES.md'))
    write(out/'price_inputs.csv', prices)
    print('Handoff PASS: 72 actor rows, 9 balanced comparisons, 3 price scenarios', flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',type=Path,default=ROOT/'results')
    parser.add_argument('--out',type=Path,default=ROOT/'handoff')
    args=parser.parse_args()
    build(args.results,args.out)
