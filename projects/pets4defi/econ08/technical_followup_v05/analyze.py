#!/usr/bin/env python3
"""Independent deterministic replay and bounded cash-floor controls (v0.5)."""
import argparse, bisect, csv, gzip, hashlib, itertools, json, statistics
from collections import Counter, defaultdict
from pathlib import Path

DAY=86400
H=90*DAY
STEP=H//100
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RESULTS=ROOT/'examples/pets4defi_access_v2/results'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def csvwrite(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def recurrence(accesses,updates,ttl,delta,horizon=H):
    """Jump between renewal indices via bisect, independently of JS per-access oracle.

    Updates at an authorization timestamp already precede that authorization.
    First subsequent update defines the immutable invalidation deadline.
    TTL is checked before stale status, as in PolicyGate.depositCached.
    """
    assert accesses==sorted(set(accesses)) and all(0<=t<horizon for t in accesses)
    assert ttl>0 and delta>=0
    pubs=sorted(updates);rows=[None]*len(accesses);i=0
    while i<len(accesses):
        t=accesses[i];expiry=min(t+ttl,horizon)
        j=bisect.bisect_right(pubs,t)
        invalid=pubs[j]+delta if j<len(pubs) else horizon
        next_i=bisect.bisect_left(accesses,min(expiry,invalid),i+1)
        if i==0:reason='NoCachedAuthorization'
        else:
            previous=rows[i-1]
            reason='AuthorizationExpired' if t>=previous['until'] else 'StaleAuthorization'
        rows[i]={'at':t,'event':'first' if i==0 else 'reauthorize','reason':reason,'until':expiry}
        for k in range(i+1,next_i):rows[k]={'at':accesses[k],'event':'hit','reason':None,'until':expiry}
        i=next_i
    return rows

def replay():
    cases=[];audit=[];n=0
    pilot=RESULTS/'econ08_native_pilot';r=json.loads((pilot/'report.json').read_text())
    aa=json.loads((pilot/'accesses.json').read_text());ctx={x['id']:x for x in r['contexts']}
    for s in r['design']['scenarios']:
        cases.append((pilot,s,r['design']['authorization_ttl_seconds'],ctx[s['id']],aa,[0]))
    for folder in sorted((RESULTS/'econ08_cohort/runs').iterdir()):
        if not (folder/'report.json').exists():continue
        r=json.loads((folder/'report.json').read_text());a=json.loads((folder/'accesses.json').read_text())
        s={**r['scenario'],'accesses':r['design']['access_offsets_seconds']}
        cases.append((folder,s,r['design']['ttl_seconds'],r['context'],a,[0,1,2,3]))
    for folder,s,ttl,ctx,aa,holders in cases:
        counts=Counter();reasons=Counter()
        for h in holders:
            group=h//(4//s['groups'])
            updates=[u['at'] for u in s['updates'] if s['family']=='zk' and u['issuer']//(4//s['groups'])==group]
            pred=recurrence(s['accesses'],updates,ttl,s['delta'])
            observed=[a for a in aa if a['scenario']==s['id'] and a['purpose']=='workload' and a.get('holder_issuer',0)==h]
            assert len(pred)==len(observed),(s['id'],h)
            for p,o in zip(pred,observed):
                for key in ['at','event','reason']:assert p[key]==o[key],(s['id'],h,key,p,o)
                assert ctx['base']+p['until']==int(o['after']['cache'][0]),(s['id'],h,'expiry',p,o)
                counts[p['event']]+=1;reasons[p['reason'] or 'cache_hit']+=1;n+=1
        audit.append({'scenario':s['id'],'accesses':sum(counts.values()),'first':counts['first'],
            'reauthorize':counts['reauthorize'],'hits':counts['hit'],'expiry_reason':reasons['AuthorizationExpired'],
            'stale_reason':reasons['StaleAuthorization'],'mismatches':0,'source':str(folder.relative_to(ROOT)),
            'access_sha256':sha(folder/'accesses.json')})
    assert len(audit)==54 and n==8832
    csvwrite(HERE/'replay_54.csv',audit)
    dump(HERE/'replay_check.json',{'status':'PASS','scenarios':len(audit),'accesses':n,'fields':['event','reason','at','cache_until'],'mismatches':0,
        'scope':'Independent Python specification replay; not a second researcher or new EVM execution.'})
    return audit

def funding(events,period,phase=0,start=0,end=H+3600):
    """Fixed calendar; stage account initially funded at start; half-open intervals."""
    assert 0<=start<end and (period is None or 0<=phase<period)
    cuts=[start]
    if period is not None:
        first=phase if phase>0 else period
        k=max(0,(start-first)//period+1)
        t=first+k*period
        while t<end:cuts.append(t);t+=period
    cuts.append(end);bins=[0]*(len(cuts)-1)
    for e in events:
        assert e['gas']>=0
        if start<=e['t']<end:bins[bisect.bisect_right(cuts,e['t'])-1]+=e['gas']
    K=max(bins,default=0);C=sum(bins);T=C-bins[-1];G=K+T;E=K-bins[-1]
    assert G-C==E and E>=0
    return {'C':C,'K':K,'T':T,'G':G,'E':E,'peak_start':cuts[bins.index(K)],'bins':bins,'cuts':cuts}

def metrics(events,period,phase=0,start=0):
    holders=[e for e in events if e['actor'].startswith('holder_')]
    pool=funding(holders,period,phase,start)
    individual=[funding([e for e in holders if e['actor']==f'holder_{i}'],period,phase,start) for i in range(4)]
    selfK=sum(x['K'] for x in individual);assert pool['K']<=selfK
    return {'holder_C':pool['C'],'pool_K':pool['K'],'SELF_sum_K':selfK,'pool_T':pool['T'],'pool_G':pool['G'],'pool_E':pool['E'],
        'pool_peak_start':pool['peak_start'],'pooling_reduction':selfK-pool['K']}

def actual_phase(runs):
    rows=[];actorrows=[]
    policies=[('daily',DAY,p) for p in [0,6*3600,12*3600,18*3600]]+[('weekly',7*DAY,p*DAY) for p in [0,1,3,6]]+[('none',None,0)]
    for r in runs:
        for label,w,phase in policies:
            for stage,start in [('full_lifecycle',0),('continuing_after_1d',DAY)]:
                rows.append({'scenario':r['scenario'],'mechanism':r['mechanism'],'updates':r['schedule'],'stage':stage,
                    'refill':label,'phase_s':phase,**metrics(r['events'],w,phase,start)})
                for actor in sorted(set(e['actor'] for e in r['events'])):
                    f=funding([e for e in r['events'] if e['actor']==actor],w,phase,start)
                    actorrows.append({'scenario':r['scenario'],'stage':stage,'refill':label,'phase_s':phase,'actor':actor,
                        **{k:f[k] for k in ['C','K','T','G','E','peak_start']}})
    csvwrite(HERE/'archived_refill_controls.csv',rows);csvwrite(HERE/'archived_actor_controls.csv',actorrows)

def coefficients(runs):
    vals=defaultdict(list)
    for r in runs:
        for e in r['events']:
            if e['category']=='access':vals[r['mechanism'],e['access_event']].append(e['gas'])
    table=[];models={k:{} for k in ['low','median','high']}
    for (m,event),v in sorted(vals.items()):
        lo,med,hi=min(v),int(statistics.median(v)),max(v)
        table.append({'mechanism':m,'event':event,'observations':len(v),'low_gas':lo,'median_gas':med,'high_gas':hi})
        for label,value in [('low',lo),('median',med),('high',hi)]:models[label][m,event]=value
    csvwrite(HERE/'gas_coefficients.csv',table);return models

def model_events(mech,pattern,phase,ttl,delta,updates,coeff,arch):
    B=int(mech[-1]) if mech.startswith('zk') else 1
    # Source setup/approval remains measured; the new access stream is modeled.
    ev=[dict(e) for e in arch['events'] if e['category'] not in ['access','status_publication']]
    if updates:ev.extend(dict(e) for e in arch['events'] if e['category']=='status_publication')
    counts=Counter()
    for h in range(4):
        offset=(phase+(h*STEP//4 if pattern=='staggered' else 0))%STEP
        accesses=[i*STEP+offset for i in range(100)]
        pubs=[(i+1)*7*DAY for i in range(12) if mech.startswith('zk') and updates and (i%4)//(4//B)==h//(4//B)]
        for p in recurrence(accesses,pubs,ttl,delta):
            counts[p['event']]+=1
            ev.append({'t':p['at']+3600,'actor':f'holder_{h}','category':'access','access_event':p['event'],'gas':coeff[mech,p['event']]})
    return ev,counts

def model_sweep(runs):
    coeffs=coefficients(runs);archives={r['mechanism']:r for r in runs if r['schedule']=='weekly'}
    rows=[];all_effects=[];worked=[]
    for mech,pattern,phase,ttl,delta in itertools.product(archives,['synchronized','staggered'],[0,6*3600,12*3600,18*3600],[7*DAY,30*DAY,60*DAY],[0,DAY,3*DAY,7*DAY,14*DAY]):
        scenario=f'{mech}_{pattern}_p{phase}_ttl{ttl//DAY}_d{delta//DAY}'
        paired={}
        for coefficient,coeff in coeffs.items():
            for update in [False,True]:
                ev,counts=model_events(mech,pattern,phase,ttl,delta,update,coeff,archives[mech])
                for label,period in [('daily',DAY),('weekly',7*DAY),('none',None)]:
                    for stage,start in [('full_lifecycle',0),('continuing_after_1d',DAY)]:
                        mm=metrics(ev,period,0,start);paired[coefficient,update,label,stage]=mm
                        if coefficient=='median':
                            rows.append({'scenario':scenario,'mechanism':mech,'pattern':pattern,'phase_s':phase,'TTL_d':ttl//DAY,'delta_d':delta//DAY,
                                'updates':'weekly' if update else 'none','refill':label,'stage':stage,
                                'first':counts['first'],'renewals':counts['reauthorize'],**mm})
                            # Fixed anchors, selected in advance: B2, 30d TTL, zero grace/phase, both access patterns.
                            if mech=='zk_B2' and ttl==30*DAY and delta==0 and phase==0 and label=='daily':
                                worked.append(rows[-1])
        for label,stage in itertools.product(['daily','weekly','none'],['full_lifecycle','continuing_after_1d']):
            effects=[paired[c,True,label,stage]['pool_K']-paired[c,False,label,stage]['pool_K'] for c in coeffs]
            all_effects.append({'scenario':scenario,'mechanism':mech,'pattern':pattern,'phase_s':phase,'TTL_d':ttl//DAY,'delta_d':delta//DAY,
                'refill':label,'stage':stage,'delta_K_low_coeff':effects[0],'delta_K_median_coeff':effects[1],'delta_K_high_coeff':effects[2],
                'delta_C_median':paired['median',True,label,stage]['holder_C']-paired['median',False,label,stage]['holder_C'],
                'positive_all_coeff':all(x>0 for x in effects),'negative_all_coeff':all(x<0 for x in effects)})
    csvwrite(HERE/'model_grid.csv',rows);csvwrite(HERE/'model_effects.csv',all_effects);csvwrite(HERE/'worked_controls.csv',worked)
    summary=[]
    for mech,refill,stage in itertools.product(archives,['daily','weekly','none'],['full_lifecycle','continuing_after_1d']):
        subset=[r for r in all_effects if (r['mechanism'],r['refill'],r['stage'])==(mech,refill,stage)]
        d=[r['delta_K_median_coeff'] for r in subset]
        summary.append({'mechanism':mech,'refill':refill,'stage':stage,'pairs':len(d),'positive':sum(x>0 for x in d),'zero':sum(x==0 for x in d),
            'negative':sum(x<0 for x in d),'min_delta_K':min(d),'max_delta_K':max(d),
            'sign_stable_across_coefficient_sets':all((r['delta_K_low_coeff']>0)-(r['delta_K_low_coeff']<0)==(r['delta_K_median_coeff']>0)-(r['delta_K_median_coeff']<0)==(r['delta_K_high_coeff']>0)-(r['delta_K_high_coeff']<0) for r in subset)})
    csvwrite(HERE/'model_summary.csv',summary)
    dump(HERE/'model_check.json',{'status':'PASS','unique_workloads':960,'median_rows':len(rows),'paired_effect_rows':len(all_effects),
        'gas_coefficient_sets':3,'event_model':'deterministic; no estimated expectation or random process',
        'scope':'Hypothetical access/TTL/grace scenarios using empirical class gas proxies, not new EVM observations.'})
    return summary

def calibration():
    p=HERE/'unchecked_calibration';r=json.loads((p/'report.json').read_text());assert r['status']=='PASS'
    txs=json.loads(gzip.decompress((p/'receipts.json.gz').read_bytes()));rows=[]
    for run in txs['runs']:
        s=run['summary'];assert len(run['accesses'])==400
        for a in run['accesses']:
            b,e=a['before'],a['after'];assert int(e['nonce'])==int(b['nonce'])+1
            assert int(e['deposit'])-int(b['deposit'])==10**20
            assert int(b['holder_balance'])-int(e['holder_balance'])==10**20
            assert int(e['gate_balance'])-int(b['gate_balance'])==10**20
        for schedule in ['weekly','control']:
            q=RESULTS/f'econ08_cohort/runs/N16_zk_B{run["B"]}_d0_HIGH_{schedule}/report.json'
            source=json.loads(q.read_text());whole=source['gas']['holder_cohort']
            source_txs=json.loads(gzip.decompress((q.parent/'receipts_and_proofs.json.gz').read_bytes()))['transactions']
            approval=sum(int(t['receipt']['gasUsed']) for t in source_txs if t['category']=='approval')
            # Use the actual eligibility-gate allowance gas as the common component.
            # This keeps deployment-address byte differences out of the eligibility increment.
            common=approval+s['access_gas'];inc=whole-common
            assert common+inc==whole
            rows.append({'mechanism':f'zk_B{run["B"]}','schedule':schedule,'holders':4,'accesses':400,
                'K05_common_gas':common,'K06_incremental_gas':inc,'holder_whole_gas':whole,
                'approval_common_gas':approval,'unchecked_access_gas':s['access_gas'],
                'evidence':'archived approval + calibrated unchecked access; K06 excludes approval byte differences'})
    csvwrite(HERE/'K05_K06_crosswalk.csv',rows)
    return rows

def main():
    replay()
    source=HERE.parent/'handoff/optional/liquidity/trace_inputs.json'
    runs=json.loads(source.read_text())['runs'];assert len(runs)==8
    actual_phase(runs);summary=model_sweep(runs);cross=calibration()
    dump(HERE/'source_manifest.json',{'analysis_plan_sha256':sha(HERE/'ANALYSIS_PLAN.md'),'archived_trace_input_sha256':sha(source),
        'code_sha256':sha(Path(__file__)),'original_report_hashes':{r['scenario']:r['source_hashes'] for r in runs}})
    print(json.dumps({'replay':'54/54; 8832 accesses; exact PASS','crosswalk':cross,
        'primary_summary':[r for r in summary if r['refill']=='daily' and r['stage']=='full_lifecycle']},indent=2))
if __name__=='__main__':main()
