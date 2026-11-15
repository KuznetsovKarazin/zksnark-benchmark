#!/usr/bin/env python3
"""Conditional fee and cash summaries; all arithmetic in integer wei."""
import json
from decimal import Decimal as D
from analyze import HERE,DAY,metrics,csvwrite,dump,sha

p=json.loads((HERE/'op_projection/projection.json').read_text())
rows=[];components=[];factor=D('2164.73')/D(10**18)
for schedule in ['weekly','control']:
    txs=[r for r in p['rows'] if r['schedule']==schedule]
    for scope in ['holders','shared','system']:
        part=[r for r in txs if scope=='system' or (r['actor'].startswith('holder_'))==(scope=='holders')]
        fees={k:sum(int(r[k+'_wei']) for r in part) for k in ['execution','l1_data','operator','total']}
        assert fees['execution']+fees['l1_data']+fees['operator']==fees['total']
        components.append({'schedule':schedule,'scope':scope,'transactions':len(part),
            **{k+'_wei':v for k,v in fees.items()},'total_eur':str(D(fees['total'])*factor)})
    events=[{'actor':r['actor'],'t':r['t'],'gas':int(r['total_wei'])} for r in txs]
    for stage,start in [('full_lifecycle',0),('continuing_after_1d',DAY)]:
        for refill,period in [('daily',DAY),('weekly',7*DAY),('none',None)]:
            m=metrics(events,period,0,start)
            rows.append({'updates':schedule,'stage':stage,'refill':refill,'holders':4,
                'expense_eur':str(D(m['holder_C'])*factor),'pool_target_eur':str(D(m['pool_K'])*factor),
                'SELF_targets_sum_eur':str(D(m['SELF_sum_K'])*factor),'pool_topups_eur':str(D(m['pool_T'])*factor),
                'pool_ending_cash_eur':str(D(m['pool_E'])*factor),'scope':'OP direct-transaction proxy; not actual AA execution'})
csvwrite(HERE/'op_projection/fee_components.csv',components)
csvwrite(HERE/'op_projection/funding_summary.csv',rows)
dump(HERE/'op_projection/manifest.json',{'inputs':{f:sha(HERE/'op_projection'/f) for f in ['projection.json','rpc_evidence.json']},
    'scripts':{f:sha(HERE/f) for f in ['summarize_op.py','analyze.py']},'source':'Pinned historical OP oracle; integer-wei accounting; EUR/ETH=2164.73'})
print(json.dumps({'components':components,'daily':[r for r in rows if r['refill']=='daily']},indent=2))
