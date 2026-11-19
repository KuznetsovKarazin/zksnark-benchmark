#!/usr/bin/env python3
"""Actual-debit funding floor, not an ERC-4337 paymaster measurement."""
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
import argparse,csv,hashlib,json

DAY=86400
Q0=D('0.130658648');EUR_ETH=D('2164.73');EUR_PER_GAS=Q0*D('1e-9')*EUR_ETH

def prefix_capital(ordered_net_debits):
    """Minimum starting cash for ordered actual debits minus external receipts."""
    balance=peak=0
    for x in ordered_net_debits:
        balance+=x;peak=max(peak,balance)
    return peak

def serial_admission_floor(actual_fees,requirements):
    """Serial diagnostic only; not the bundle prevalidation algorithm."""
    if len(actual_fees)!=len(requirements):raise ValueError('length mismatch')
    spent=peak=0
    for c,m in zip(actual_fees,requirements):
        if c<0 or m<c:raise ValueError('need nonnegative fees and requirement >= actual fee')
        peak=max(peak,spent+m);spent+=c
    return peak

def target_and_funding(events,interval,horizon):
    """Reset-to-target at 0, interval,... <horizon, before boundary debits.

    Pure nonnegative debits. All events retain their actual timestamps and order.
    Values in gas-equivalent units at one constant price. Treasury transfers have
    zero modeled delay/fee and are reported explicitly; costs are not reduced.
    """
    if horizon<=0 or (interval is not None and interval<=0):raise ValueError('bad duration')
    for e in events:
        if not 0<=e['t']<horizon or e['gas']<0:raise ValueError('event outside horizon or negative debit')
    total=sum(e['gas'] for e in events)
    if interval is None:
        return {'target':total,'total_debit':total,'initial_transfer':total,'refill_transfers':0,
            'gross_treasury_funding':total,'end_balance':0,'positive_refill_count':0,
            'peak_window':0,'windows':[{'start':0,'end':horizon,'debit':total}]}
    bins=defaultdict(int)
    for e in events:bins[e['t']//interval]+=e['gas']
    n=(horizon+interval-1)//interval
    target=max(bins.values(),default=0)
    balance=target;refills=0;count=0;windows=[]
    for k in range(n):
        if k:
            add=target-balance;assert add>=0
            refills+=add;count+=int(add>0);balance+=add
        debit=bins[k];balance-=debit;assert balance>=0
        windows.append({'start':k*interval,'end':min((k+1)*interval,horizon),'debit':debit})
    gross=target+refills
    assert gross-total==balance
    return {'target':target,'total_debit':total,'initial_transfer':target,'refill_transfers':refills,
        'gross_treasury_funding':gross,'end_balance':balance,'positive_refill_count':count,
        'peak_window':next((k for k in range(n) if bins[k]==target),0),'windows':windows}

def s(v):
    if isinstance(v,D):return str(v)
    if isinstance(v,dict):return {k:s(x) for k,x in v.items()}
    if isinstance(v,list):return [s(x) for x in v]
    return v

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,default=Path(__file__).with_name('trace_inputs.json'))
    ap.add_argument('--out',type=Path,default=Path(__file__).parent)
    a=ap.parse_args();a.out.mkdir(exist_ok=True,parents=True)
    source=json.loads(a.input.read_text());summary=[];accounts=[]
    for run in source['runs']:
        for label,period in [('daily_24h_primary',DAY),('weekly_7d_sensitivity',7*DAY),('no_refill_sensitivity',None)]:
            models={}
            for family in ['SELF','PM']:
                grouped=defaultdict(list)
                for event in run['events']:
                    actor='paymaster_holder_pool' if family=='PM' and event['actor'].startswith('holder_') else event['actor']
                    grouped[actor].append(event)
                metrics={actor:target_and_funding(ev,period,run['horizon_seconds']) for actor,ev in grouped.items()}
                models[family]=metrics
                for actor,m in metrics.items():
                    accounts.append({'scenario':run['scenario'],'family':family,'refill_policy':label,'assigned_account':actor,
                        'actual_debit_gas':m['total_debit'],'target_floor_gas':m['target'],
                        'target_floor_eur_at_q0':D(m['target'])*EUR_PER_GAS,
                        'initial_transfer_gas_equiv':m['initial_transfer'],
                        'refill_transfers_gas_equiv':m['refill_transfers'],
                        'gross_treasury_funding_gas_equiv':m['gross_treasury_funding'],
                        'end_balance_gas_equiv':m['end_balance'],
                        'peak_window_start_seconds':m['windows'][m['peak_window']]['start'],
                        'status':'actual_debit_floor_only_admission_prefund_unknown'})
            holder_self={k:v for k,v in models['SELF'].items() if k.startswith('holder_')}
            shared={k:v for k,v in models['SELF'].items() if not k.startswith('holder_')}
            pm=models['PM']['paymaster_holder_pool']
            # Descriptive secondary outcome only: a fixed first-window cutoff.
            # It does not replace the full-lifecycle target or change funding policy.
            tail_windows=pm['windows'][1:] if period is not None else []
            assert pm['total_debit']==sum(m['total_debit'] for m in holder_self.values())
            assert pm['target']<=sum(m['target'] for m in holder_self.values())
            assert all(models['PM'][k]==v for k,v in shared.items())
            summary.append({'scenario':run['scenario'],'mechanism':run['mechanism'],'update_schedule':run['schedule'],
                'refill_policy':label,'A_active':4,'holder_total_actual_gas':pm['total_debit'],
                'holder_SELF_sum_target_floor_gas':sum(m['target'] for m in holder_self.values()),
                'holder_SELF_max_individual_target_floor_gas':max(m['target'] for m in holder_self.values()),
                'PM_holder_pool_target_floor_gas':pm['target'],'PM_holder_pool_target_floor_eur_q0':D(pm['target'])*EUR_PER_GAS,
                'shared_sum_account_target_floor_gas':sum(m['target'] for m in shared.values()),
                'PM_gross_treasury_funding_gas_equiv':pm['gross_treasury_funding'],
                'PM_end_deposit_balance_gas_equiv':pm['end_balance'],
                'PM_first_window_debit_gas':pm['windows'][0]['debit'],
                'PM_later_window_max_debit_gas':max((w['debit'] for w in tail_windows),default=''),
                'secondary_cutoff_seconds':'' if period is None else period,
                'scope':'hindsight_debit_floor_no_AA_overhead_no_fee_volatility'})
    for name,rows in [('liquidity_summary.csv',summary),('liquidity_accounts.csv',accounts)]:
        with (a.out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(s(rows))
    summary_json={'kind':'new_cashflow_diagnostic_on_existing_receipts_not_new_EVM',
        'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'reference_price':{'q0_gwei':str(Q0),'eur_eth':str(EUR_ETH),'kind':'historical'},
        'origin':'report.context.base - 3600; initial funding before setup; access begins at +3600s',
        'refill':'reset each account to its fixed target before events at 0,k*period; no unrequested emergency refill',
        'scope':'all approvals and access operation gas; shared operator/issuer costs separate; token principals and fixture costs excluded',
        'limitations':['No external customer collections, reimbursement, sponsor revenue or operating-account refunds modeled.',
            'Gross treasury funding = initial + refills; end balance is retained, not expensed.',
            'Ideal instantaneous costless replenishment; adequacy of external treasury is not asserted.',
            'Targets use hindsight actual gas at constant q0; not safe deployment buffers or UserOperation prefunds.',
            'ERC4337 validation reservations, bundle prevalidation, extra fees and stake are unknown.',
            'Role accounts are a financing assignment; fixture issuer transactions may use one administrative signer.',
            'No own-holder revocation, reissuance, new holder count, or extended-delay EVM run.'],
        'results':summary}
    (a.out/'liquidity_results.json').write_text(json.dumps(s(summary_json),indent=2)+'\n')
    print(json.dumps({'runs':len(source['runs']),'summary_rows':len(summary),'account_rows':len(accounts),'results':s(summary)},indent=2))

if __name__=='__main__':main()
