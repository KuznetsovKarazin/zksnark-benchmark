import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics
from model import (DAY, generate, infer, needs_refresh, likelihood_reference,
                   anonymous_label_posterior, availability_trace, heartbeat_masks,
                   admissible_accept_set)

ROOT = Path(__file__).resolve().parents[1]


def dump(path, x):
    path.write_text(json.dumps(x, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def csvwrite(path, rows):
    if not rows:
        raise ValueError('empty result table '+str(path))
    with path.open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def source_replay(out):
    arc=ROOT/'inputs/archive'
    source=json.loads((ROOT/'inputs/source_index.json').read_text())
    for entry in source['files']:
        b=(arc/entry['local']).read_bytes()
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==entry['sha'],entry['local']
    records=[]
    nr=json.loads((arc/'native_report.json').read_text())
    na=json.loads((arc/'native_accesses.json').read_text())
    nm=json.loads((arc/'econ08_native_pilot_manifest.json').read_text())
    for local, original in [('native_report.json','report.json'),('native_accesses.json','accesses.json')]:
        assert hashlib.sha256((arc/local).read_bytes()).hexdigest()==nm[original]
    for s in nr['design']['scenarios']:
        a=[x for x in na if x['scenario']==s['id'] and x['purpose']=='workload']
        records.append((s['id'],s['family'],s['groups'],s['delta'],s['updates'],s['accesses'],
                        nr['design']['authorization_ttl_seconds'],[(0,a)]))
    for f in sorted(arc.glob('N*_report.json')):
        r=json.loads(f.read_text());s=r['scenario']; stem=f.name[:-len('report.json')]
        m=json.loads((arc/(stem+'manifest.json')).read_text())
        for suffix in ['report.json','accesses.json']:
            assert hashlib.sha256((arc/(stem+suffix)).read_bytes()).hexdigest()==m[suffix]
        a=json.loads((arc/(stem+'accesses.json')).read_text())
        records.append((s['id'],s['family'],s['groups'],s['delta'],s['updates'],
                        r['design']['access_offsets_seconds'],r['design']['ttl_seconds'],
                        [(j,[x for x in a if x['holder_issuer']==j]) for j in range(4)]))
    checks, public, truth, shapes={},[],[],{}
    for sid,family,groups,delta,updates,accesses,ttl,holders in records:
        matched=0; authorizations=0
        for j,rows in holders:
            rows=sorted(rows,key=lambda r:r['at'])
            times=sorted(u['at'] for u in updates if family=='zk' and u['issuer']//(4//groups)==j//(4//groups))
            last=None
            for r in rows:
                needed=needs_refresh(r['at'],last,ttl,delta,times)
                event='first' if last is None else 'reauthorize' if needed else 'hit'
                assert event==r['event'],(sid,j,r['at'],event,r['event'])
                if needed:last=r['at'];authorizations+=1
                matched+=1
            candidates=list(range((j//(4//groups))*(4//groups),(j//(4//groups)+1)*(4//groups))) if family=='zk' else [j]
            oid=f'T{len(public):03d}'
            public.append({'target':oid, 'scenario':sid, 'family':family, 'public_candidates':candidates,
                'ttl':ttl,'delta':delta,'updates':[{'at':u['at'],'issuer':u['issuer']} for u in updates],
                'observations':[{'at':r['at'],'refresh':r['event']!='hit'} for r in rows]})
            truth.append({'target':oid,'issuer':j})
        checks[sid]={'scenario':sid,'holders':len(holders),'decisions':matched,'mismatches':0,
                     'authorizations':authorizations,'family':family,'groups':groups,'delta':delta}
        key=json.dumps([[(u['at'],u['issuer']) for u in updates],accesses,ttl,delta])
        if key not in shapes:
            shapes[key]={'id':f'W{len(shapes):02d}','source_example':sid,'updates':updates,
                          'accesses':accesses,'ttl':ttl,'delta':delta}
    csvwrite(out/'source_replay.csv',list(checks.values()))
    dump(out/'public_observations.json',public);dump(out/'evaluation_truth.json',truth)
    dump(out/'workloads.json',list(shapes.values()))
    assert len(checks)==54 and sum(x['decisions'] for x in checks.values())==8832
    return list(shapes.values()), {'source_files_verified':len(source['files']),
            'source_scenarios':len(checks),'source_decisions':8832,'source_mismatches':0,
            'public_target_histories':len(public),'unique_workloads':len(shapes)}


def policy_args(name):
    if name.startswith('coin_'):
        return 'one_coin', float(name.split('_')[1])
    if name.startswith('cover_'):
        return 'event_cover', float(name.split('_')[1])
    return ('selective',float(name.split('_')[1])) if name.startswith('dummy_') else (name,0.0)


def metrics(obs, post, truth, gas):
    last=post[-1]
    first=next((p['at'] for p in post if p['support']==1),None)
    n=sum(r['refresh'] for r in obs)
    return {'entropy':last['entropy'],'support':last['support'],'pmax':last['pmax'],
            'ptrue':last['posterior'][truth], 'singleton':int(last['support']==1),
            'confident_wrong':int(last['pmax']>=0.95 and last['posterior'][truth]<last['pmax']-1e-12),
            'first_singleton_day':first/DAY if first is not None else '',
            'authorizations':n,'gas_proxy':gas['first']+(n-1)*gas['reauthorize']+(len(obs)-n)*gas['hit']}


def aggregate(rows, keys, values):
    grouped={}
    for r in rows:grouped.setdefault(tuple(r[k] for k in keys),[]).append(r)
    ans=[]
    for key, group in grouped.items():
        row=dict(zip(keys,key));row['runs']=len(group)
        for v in values:
            x=[r[v] for r in group]
            row[v+'_mean']=statistics.fmean(x)
            row[v+'_sd']=statistics.stdev(x) if len(x)>1 else 0.0
        ans.append(row)
    return ans


def run_timing(out, shapes, plan, gas):
    policies=plan['timing_policies']; rows=[]; detailed=[]; decisions=0
    for w in shapes:
        for name in policies:
            policy,rho=policy_args(name)
            for j in range(4):
                reps=range(plan['seeds']) if name.startswith(('dummy','cover','coin')) and name not in ['cover_1.0','coin_0.0','coin_1.0'] else range(1)
                for seed in reps:
                    obs=generate(w['accesses'],w['updates'],j,ttl=w['ttl'],delta=w['delta'],policy=policy,rho=rho,seed=6000+seed)
                    post=infer(obs,w['updates'],ttl=w['ttl'],delta=w['delta'],policy=policy,rho=rho)
                    assert all(p['posterior'][j]>0 for p in post)
                    row={'workload':w['id'],'source_example':w['source_example'],'policy':name,'issuer':j,'seed':seed,
                         'accesses':len(obs),'updates':len(w['updates']),'delta':w['delta'],**metrics(obs,post,j,gas)}
                    rows.append(row);decisions+=len(obs)
                    if len(w['updates'])==12 and len(obs)==100 and w['delta']==0 and seed==0:
                        for o,p in zip(obs,post):detailed.append({'policy':name,'issuer':j,'at':o['at'],'refresh':int(o['refresh']),
                            'entropy':p['entropy'],'support':p['support'],'pmax':p['pmax'],'posterior':json.dumps(p['posterior'])})
    csvwrite(out/'timing_workload_runs.csv',rows)
    vals=['entropy','support','pmax','singleton','authorizations','gas_proxy','confident_wrong']
    csvwrite(out/'timing_workload_summary.csv',aggregate(rows,['workload','source_example','policy'],vals))
    csvwrite(out/'weekly_history.csv',detailed)
    return {'timing_workload_runs':len(rows),'timing_workload_decisions':decisions}


def poisson_updates(mean, seed, horizon=90*DAY, issuers=4):
    rng=random.Random(seed);result=[]
    if mean==0:return result
    for j in range(issuers):
        t=rng.expovariate(mean/horizon)
        while t<horizon:
            result.append({'at':int(t),'issuer':j})
            t+=rng.expovariate(mean/horizon)
    return sorted(result,key=lambda u:(u['at'],u['issuer']))


def run_synthetic(out, plan, gas):
    rows=[]; decisions=0
    for nu,a,ttl,delta in itertools.product(plan['synthetic_mean_updates_per_issuer'],plan['synthetic_accesses'],
                                           plan['synthetic_ttl_days'],plan['synthetic_delta_days']):
        for seed in range(plan['seeds']):
            updates=poisson_updates(nu,13000+seed)
            rng=random.Random(17000+seed)
            accesses=[0]+sorted(rng.sample(range(1,90*DAY),a-1))
            truth=seed%4
            for name in plan['timing_policies']:
                policy,rho=policy_args(name)
                obs=generate(accesses,updates,truth,ttl=ttl*DAY,delta=delta*DAY,policy=policy,rho=rho,seed=19000+seed)
                post=infer(obs,updates,ttl=ttl*DAY,delta=delta*DAY,policy=policy,rho=rho)
                assert all(p['posterior'][truth]>0 for p in post)
                if name in ['common','every','cover_1.0','coin_1.0'] or nu==0:
                    assert abs(post[-1]['entropy']-2)<1e-10
                if name in ['coin_0.0','coin_1.0']:
                    endpoint='selective' if name=='coin_0.0' else 'common'
                    assert obs==generate(accesses,updates,truth,ttl=ttl*DAY,delta=delta*DAY,policy=endpoint)
                rows.append({'nu':nu,'accesses':a,'ttl_days':ttl,'delta_days':delta,'seed':seed,'issuer':truth,
                             'policy':name,'realized_updates':len(updates),**metrics(obs,post,truth,gas)})
                decisions+=len(obs)
    csvwrite(out/'synthetic_timing_runs.csv',rows)
    csvwrite(out/'synthetic_timing_summary.csv',aggregate(rows,['nu','accesses','ttl_days','delta_days','policy'],
             ['entropy','pmax','singleton','authorizations','gas_proxy','confident_wrong']))
    return {'synthetic_timing_runs':len(rows),'synthetic_timing_decisions':decisions}


def run_outages(out, plan):
    rows=[];decisions=0
    for n,fail,rec,F in itertools.product(plan['outage_issuers'],plan['outage_fail_probability_per_day'],
                                        plan['outage_recovery_probability_per_day'],plan['outage_freshness_days']):
        for k in sorted({2,math.ceil(.75*n),n}):
            for seed in range(plan['seeds']):
                masks,pubs=heartbeat_masks(n,90,fail,rec,F,23000+seed)
                for policy in plan['outage_policies']:
                    histories=[availability_trace(masks,j,n,k,policy) for j in range(n)]
                    supports=[h[-1]['support'] for h in histories]
                    rows.append({'issuers':n,'k':k,'fail':fail,'recovery':rec,'freshness_days':F,'seed':seed,'policy':policy,
                        'availability':sum(r['accepted'] for h in histories for r in h)/(n*90),
                        'entropy':statistics.fmean(h[-1]['entropy'] for h in histories),
                        'singleton_fraction':sum(v==1 for v in supports)/n,
                        'below_k_fraction':sum(v<k for v in supports)/n,
                        'positive_singleton_fraction':sum(h[-1]['positive_support']==1 for h in histories)/n,
                        'min_support':min(supports),'heartbeat_publications':pubs})
                    decisions+=n*90
    csvwrite(out/'outage_runs.csv',rows)
    csvwrite(out/'outage_summary.csv',aggregate(rows,['issuers','k','fail','recovery','freshness_days','policy'],
             ['availability','entropy','singleton_fraction','below_k_fraction','positive_singleton_fraction','heartbeat_publications']))
    example=[]
    for policy in plan['outage_policies']:
        for j in range(4):
            h=availability_trace([[0,1,2],[1,2,3],[0,2,3]],j,4,3,policy)
            for row in h:example.append({'policy':policy,'issuer':j,**row})
    dump(out/'intersection_example.json',example)
    return {'outage_runs':len(rows),'outage_decisions':decisions}


def analytic_checks(out):
    # Exhaustive independent enumeration of safe deterministic accept sets.
    checked=0
    for n in range(2,7):
        universe=set(range(n))
        subsets=[{j for j in range(n) if mask>>j&1} for mask in range(1<<n)]
        for k in range(1,n+1):
            for c in subsets:
                if len(c)<k:continue
                for s in subsets:
                    a=admissible_accept_set(c,s,k,'guard_k')
                    possible=[b for b in subsets if b<=c&s and
                              (not b or b==c or (len(b)>=k and len(c-b)>=k))]
                    assert a<=c&s and (not a or a==c or (len(a)>=k and len(c-a)>=k))
                    assert len(a)==max(map(len,possible))
                    checked+=1
    # Toy exact posteriors against the independent likelihood evaluator.
    comparisons=0
    u=[{'at':2,'issuer':0},{'at':4,'issuer':1}]
    for ttl,delta,rho,policy in itertools.product([2,8],[0,1],[0,.25,.75,1],['selective','common','every','event_cover']):
        all_mass=0
        for bits in itertools.product([False,True],repeat=5):
            obs=[{'at':t,'refresh':b} for t,b in zip([0,1,3,5,7],bits)]
            l=[likelihood_reference(obs,u,j,ttl,delta,policy,rho) for j in range(4)]
            mass=sum(l)/4;all_mass+=mass
            if mass:
                p=infer(obs,u,ttl=ttl,delta=delta,policy=policy,rho=rho)[-1]['posterior']
                assert max(abs(x-y/sum(l)) for x,y in zip(p,l))<1e-12
                comparisons+=1
        assert abs(all_mass-1)<1e-12
    # Unknown issuer-label permutation restores named-issuer symmetry.
    obs=generate([0,3,5,7],u,0,ttl=8)
    hidden=anonymous_label_posterior(obs,u,4,8,0)
    assert max(abs(v-.25) for v in hidden)<1e-12
    # All issuers updated together, or TTL expires on every access: no timing information.
    for updates,ttl in [([{'at':2,'issuer':j} for j in range(4)],8),(u,1)]:
        obs=generate([0,3,5,7],updates,0,ttl=ttl)
        assert abs(infer(obs,updates,ttl=ttl)[-1]['entropy']-2)<1e-12
    result={'safe_accept_set_enumerations':checked,'exact_bayes_transcripts':comparisons,
            'anonymous_label_control_posterior':hidden,'simultaneous_updates_control':'PASS',
            'always_expired_ttl_control':'PASS','all_checks':'PASS'}
    dump(out/'analytic_checks.json',result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'results');a=parser.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    plan=json.loads((ROOT/'PLAN.json').read_text())
    gas={r['event']:int(r['median_gas']) for r in csv.DictReader((ROOT/'inputs/gas_coefficients.csv').open()) if r['mechanism']=='zk_B1'}
    shapes,stats=source_replay(a.out);print('Source replay PASS',stats,flush=True)
    stats.update(analytic_checks(a.out));print('Exact checks PASS',flush=True)
    stats.update(run_timing(a.out,shapes,plan,gas));print('Archived workload counterfactuals complete',flush=True)
    stats.update(run_synthetic(a.out,plan,gas));print('Synthetic timing complete',flush=True)
    stats.update(run_outages(a.out,plan));print('Availability experiments complete',flush=True)
    from extensions import run_extensions
    stats.update(run_extensions(a.out,shapes,plan,gas))
    stats.update({'numeric_status':'PASS','new_evm_measurements':0,'privacy_novelty_gate':'NOT_ESTABLISHED',
                  'plan_sha256':hashlib.sha256((ROOT/'PLAN.json').read_bytes()).hexdigest(),'gas_coefficients':gas,
                  'version':'0.2','new_contract':False,'anonymous_clustering_is_EF_attack':False})
    dump(a.out/'validation.json',stats);print(json.dumps(stats,indent=2))


if __name__=='__main__':main()
