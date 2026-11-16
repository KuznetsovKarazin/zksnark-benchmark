"""Generate the small economic handoff from verified technical results."""
import argparse
import csv
import math
import json
from fractions import Fraction
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


def beneficiary_transfers(groups):
    """Net settlement giving every active holder the same privacy premium.

    Each group initially pays its common-policy access gas. Settlement changes
    that burden to its selective reference plus its per-holder share of the
    aggregate common-minus-selective premium. Issuers do not fund this rule.
    Fractions preserve exact budget balance before CSV/monetary rounding.
    """
    count = sum(g['holders'] for g in groups.values())
    if count <= 0 or any(g['holders'] <= 0 for g in groups.values()):
        raise ValueError('Beneficiary allocation requires positive holder counts')
    extra = sum(g['common'] - g['selective'] for g in groups.values())
    settlement = {}
    for issuer, g in groups.items():
        premium = Fraction(extra * g['holders'], count)
        net = premium - (g['common'] - g['selective'])
        settlement[issuer] = dict(premium=premium, paid=max(net, 0),
                                  received=max(-net, 0))
    assert sum(s['paid'] - s['received'] for s in settlement.values()) == 0
    return settlement


def build(results, out):
    out.mkdir(parents=True, exist_ok=True)
    coalitions = read(results, 'coalition_costs.csv')
    transfers = read(results, 'compensation_reference.csv')
    cases = read(results, 'economic_cases.csv')
    rows = []
    for case in ['weekly_A4', 'weekly_A32', 'asymmetric_A32']:
        common = next(r for r in cases if r['case']==case and r['policy']=='common')
        resource_total = float(common['holder_access_gas_proxy'])
        groups = {}
        for issuer in range(1, 5):
            full = ';'.join(str(i) for i in range(1, 5) if i != issuer)
            group_rows = [r for r in coalitions if r['case'] == case
                          and r['target_issuer'] == str(issuer)]
            all_updates = next(r for r in group_rows if r['foreign_issuers'] == full)
            own_only = next(r for r in group_rows if r['foreign_issuers'] == 'none')
            groups[issuer] = dict(holders=int(all_updates['holders']),
                                 common=int(all_updates['access_gas_proxy']),
                                 selective=int(own_only['access_gas_proxy']))
        beneficiary = beneficiary_transfers(groups)
        for rule in ['SELF', 'publication_frequency', 'shapley_externality',
                     'beneficiary_equal_per_holder']:
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
                    note = (f"{c['holders']} active holders; access-only scope"
                            if kind=='holder_group' else
                            'publication/setup/settlement costs excluded, not zero lifecycle cost')
                    if rule == 'beneficiary_equal_per_holder' and kind == 'holder_group':
                        s = beneficiary[issuer]
                        paid, received = float(s['paid']), float(s['received'])
                        note += (f"; selective baseline {groups[issuer]['selective']} gas"
                                 f"; allocated premium {float(s['premium'])} gas eq"
                                 '; paid/received are net settlement among holder groups')
                    block.append(dict(case=case, rule=rule, actor=f'{kind}_{issuer}',
                        holder_access_gas=resource, compensation_paid_gas_eq=paid,
                        compensation_received_gas_eq=received,
                        net_cost_gas_eq=resource+paid-received, euro_per_gas='',
                        net_cost_eur='', notes=note))
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
    print('Handoff PASS: 96 actor rows, 12 balanced comparisons, 3 price scenarios', flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',type=Path,default=ROOT/'results')
    parser.add_argument('--out',type=Path,default=ROOT/'handoff')
    args=parser.parse_args()
    build(args.results,args.out)
