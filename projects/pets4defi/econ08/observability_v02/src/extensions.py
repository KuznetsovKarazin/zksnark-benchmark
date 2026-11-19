"""v0.2 exact checks, anonymous cohort attack, and economic quantity handoff."""
import csv
import heapq
import itertools
import json
import math
import random
import statistics
from collections import Counter
from model import (DAY, generate, infer, coin_likelihood_enumeration)


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def csvwrite(path, rows):
    with path.open('w', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def gas_cost(obs, gas):
    r=sum(x['refresh'] for x in obs)
    return gas['first']+(r-1)*gas['reauthorize']+(len(obs)-r)*gas['hit']


def summarize(rows, keys, metrics):
    groups={}
    for row in rows:groups.setdefault(tuple(row[k] for k in keys),[]).append(row)
    out=[]
    for key, values in groups.items():
        row=dict(zip(keys,key)); row['runs']=len(values)
        for metric in metrics:
            xs=[v[metric] for v in values]
            row[metric+'_mean']=statistics.fmean(xs)
            row[metric+'_sd']=statistics.stdev(xs) if len(xs)>1 else 0.0
        if 'anchor_assigned' in values[0]:
            assigned=sum(v['anchor_assigned'] for v in values)
            row['anchor_precision_pooled']=sum(v['anchor_correct'] for v in values)/assigned if assigned else ''
            row['anchor_predictions_total']=assigned
        out.append(row)
    return out


def exact_checks(out, gas):
    optimality=0
    for mask in itertools.product([0,1],repeat=6):
        pubs=[i+.5 for i,b in enumerate(mask) if b]
        updates=[{'at':u,'issuer':i%3} for i,u in enumerate(pubs)]
        for ttl,grace in itertools.product([1,2,4],[0,.75,2]):
            minimum=8
            for actions in itertools.product([0,1],repeat=6):
                last=0;valid=True
                for t,full in zip(range(1,7),actions):
                    if full:last=t
                    elif t>=last+ttl or any(last<u<=t and t>=u+grace for u in pubs):
                        valid=False;break
                if valid:minimum=min(minimum,1+sum(actions))
            obs=generate(range(7),updates,0,3,ttl,grace,'common')
            assert sum(x['refresh'] for x in obs)==minimum
            optimality+=1
    # Explicit latent-coin oracle versus sequential filter, including overlapping
    # grace periods, repeated hits, same-time publications and proactive TTL.
    updates=[{'at':1,'issuer':0},{'at':2,'issuer':1},
             {'at':2,'issuer':2},{'at':4,'issuer':0}]
    comparisons=0
    for ttl,delta,rho in itertools.product([2,10],[0,1,3],[0,.25,.75,.95,1]):
        mass=0
        for bits in itertools.product([False,True],repeat=6):
            obs=[{'at':t,'refresh':b} for t,b in zip([0,1,2,3,5,7],bits)]
            weights=[coin_likelihood_enumeration(obs,updates,j,ttl,delta,rho)/4 for j in range(4)]
            z=sum(weights);mass+=z
            if z:
                got=infer(obs,updates,4,ttl,delta,'one_coin',rho)[-1]['posterior']
                assert max(abs(p-w/z) for p,w in zip(got,weights))<1e-11
                comparisons+=1
        assert abs(mass-1)<1e-11
    # Time-varying prices: a counterexample to euro-cost optimality, NOT to the
    # authorization-count statement (both schedules have two full calls).
    dynamic={'access_times':[0,1,2],'publication_time':.5,'grace':1.5,
             'prices_at_1_and_2':[1,100],
             'greedy_after_launch_cost':gas['hit']+100*gas['reauthorize'],
             'proactive_after_launch_cost':gas['reauthorize']+100*gas['hit']}
    assert dynamic['proactive_after_launch_cost']<dynamic['greedy_after_launch_cost']
    result={'optimality_small_schedules':optimality,
            'coin_bayes_feasible_transcripts':comparisons,
            'coin_bayes_mass_check':'PASS','dynamic_price_counterexample':dynamic,
            'finite_pure_epsilon_for_informative_event_rho_below_one':False,
            'theorem_scope':'fixed attempts; mandatory invalidation; full/hit observable; zero-error safety; fixed costs',
            'independent_novelty_validation':False,'status':'PASS'}
    dump(out/'extension_checks.json',result)
    return result


def weekly_exact(out, gas):
    rows=[]
    for step in range(21):
        rho=step/20
        mass=EH=accuracy=single=ER=0.0
        for y in itertools.product([0,1],repeat=12):
            weights=[]
            for j in range(4):
                value=.25
                for event,full in enumerate(y):
                    probability=1.0 if event%4==j else rho
                    value*=probability if full else 1-probability
                weights.append(value)
            z=sum(weights)
            if not z:continue
            p=[w/z for w in weights]
            h=-sum(v*math.log2(v) for v in p if v)
            mass+=z;EH+=z*h;accuracy+=z*max(p);ER+=z*(1+sum(y))
            single+=z*int(sum(w>0 for w in weights)==1)
        q=rho**3
        theory_H=sum(math.comb(3,k)*q**k*(1-q)**(3-k)*math.log2(k+1) for k in range(4))
        assert abs(mass-1)<1e-10 and abs(ER-(4+9*rho))<1e-10
        assert abs(EH-theory_H)<1e-10 and abs(single-(1-q)**3)<1e-10
        # Evaluate cost using the closed form so serialized integer endpoints
        # are insensitive to summation noise in the independent enumeration.
        count=4+9*rho
        cost=gas['first']+(count-1)*gas['reauthorize']+(100-count)*gas['hit']
        common=gas['first']+12*gas['reauthorize']+87*gas['hit']
        rows.append({'rho':rho,'expected_authorizations':count,'gas_proxy':cost,
                     'saving_vs_common_fraction':(common-cost)/common,
                     'entropy_bits':theory_H,'information_bits':2-theory_H,
                     'bayes_identification_accuracy':accuracy,'singleton_probability':(1-q)**3,
                     'epsilon_worst_case':'infinite' if rho<1 else '0',
                     'one_event_minimum_additive_privacy_slack':1-rho})
    csvwrite(out/'weekly_one_coin_exact.csv',rows)
    return {'weekly_exact_rho_points':len(rows),'weekly_transcripts_per_point':4096}


def anonymous_features(records, updates, ttl, delta):
    """Only observable handles, access classes and anonymous update timestamps.

    Use a response only if exactly one new update deadline crosses the interval
    since the preceding access, it was not absorbed by the last full, and TTL
    is not expired. Missing opportunities stay missing, never become hits.
    """
    if any(set(u)!={'at'} for u in updates):
        raise ValueError('anonymous update input contains privileged fields')
    if any(set(r)!={'handle','observations'} for r in records):
        raise ValueError('cohort input contains privileged fields')
    deadlines=[u['at']+delta for u in updates]
    features=[]
    for record in records:
        row=[None]*len(updates); last=previous=None
        for o in record['observations']:
            if set(o)!={'at','refresh'}:raise ValueError('private observation fields')
            t=o['at']
            if previous is not None and last is not None and t<last+ttl:
                new=[e for e,d in enumerate(deadlines) if previous<d<=t]
                if len(new)==1 and updates[new[0]]['at']>last:
                    row[new[0]]=int(o['refresh'])
            if o['refresh']:last=t
            previous=t
        features.append(row)
    return features


def average_linkage(features, groups):
    """Deterministic, unsupervised; tie-breaking uses randomized public handles."""
    n=len(features); distance={}; heap=[]
    shared_counts=[]
    for i in range(n):
        for j in range(i+1,n):
            pairs=[(a,b) for a,b in zip(features[i],features[j]) if a is not None and b is not None]
            d=sum(a!=b for a,b in pairs)/len(pairs) if len(pairs)>=2 else .5
            distance[i,j]=d;heapq.heappush(heap,(d,i,j));shared_counts.append(len(pairs))
    original=dict(distance)
    members={i:[i] for i in range(n)};active=set(members);nxt=n
    while len(active)>groups:
        while True:
            d,i,j=heapq.heappop(heap)
            if i in active and j in active:break
        ai,aj=len(members[i]),len(members[j]);active.remove(i);active.remove(j)
        members[nxt]=members[i]+members[j]
        for k in sorted(active):
            v=(ai*distance[min(i,k),max(i,k)]+aj*distance[min(j,k),max(j,k)])/(ai+aj)
            distance[min(nxt,k),max(nxt,k)]=v
            heapq.heappush(heap,(v,min(nxt,k),max(nxt,k)))
        active.add(nxt);nxt+=1
    labels=[None]*n
    for label,c in enumerate(sorted(active)):
        for i in members[c]:labels[i]=label
    return labels,original,statistics.fmean(shared_counts) if shared_counts else 0.0


def auc_with_ties(scores, actual):
    positives=sum(actual);negatives=len(actual)-positives
    if not positives or not negatives:return .5
    ordered=sorted(zip(scores,actual));rank_sum=0.;a=0
    while a<len(ordered):
        b=a+1
        while b<len(ordered) and ordered[b][0]==ordered[a][0]:b+=1
        rank_sum+=((a+1+b)/2)*sum(y for _,y in ordered[a:b]);a=b
    return (rank_sum-positives*(positives+1)/2)/(positives*negatives)


def adjusted_rand(truth,pred):
    choose2=lambda n:n*(n-1)/2
    cells=Counter(zip(truth,pred));a=Counter(truth);b=Counter(pred)
    index=sum(choose2(v) for v in cells.values())
    sa=sum(choose2(v) for v in a.values());sb=sum(choose2(v) for v in b.values())
    expected=sa*sb/choose2(len(truth));maximum=(sa+sb)/2
    return (index-expected)/(maximum-expected) if maximum!=expected else 1.0


def cluster_metrics(truth,pred,distances):
    pairs=sorted(distances)
    actual=[int(truth[i]==truth[j]) for i,j in pairs]
    guessed=[int(pred[i]==pred[j]) for i,j in pairs]
    tp=sum(a*g for a,g in zip(actual,guessed));pp=sum(guessed);ap=sum(actual)
    peers=[i for i in range(1,len(truth)) if pred[i]==pred[0]]
    correct=sum(truth[i]==truth[0] for i in peers)
    return {'ari':adjusted_rand(truth,pred),
            'pair_auc':auc_with_ties([1-distances[p] for p in pairs],actual),
            'pair_precision':tp/pp if pp else 0.,'pair_recall':tp/ap if ap else 0.,
            'anchor_assigned':len(peers),'anchor_correct':correct,'anchor_wrong':len(peers)-correct,
            'anchor_coverage':len(peers)/(len(truth)-1),
            'anchor_wrong_fraction':(len(peers)-correct)/(len(truth)-1)}


def make_updates(means, seed):
    rng=random.Random(seed);updates=[]
    for j,mean in enumerate(means):
        if not mean:continue
        t=rng.expovariate(mean/(90*DAY))
        while t<90*DAY:
            updates.append({'at':int(t),'issuer':j})
            t+=rng.expovariate(mean/(90*DAY))
    return sorted(updates,key=lambda u:(u['at'],u['issuer']))


def run_clustering(out,plan):
    config=plan['clustering'];rows=[];decisions=0
    for h,a,nu,delta in itertools.product(config['holders_per_issuer'],config['accesses'],config['nu'],config['delta_days']):
        for seed in range(config['seeds']):
            updates=make_updates([nu]*4,31000+seed)
            public=[{'at':u['at']} for u in updates]
            order=list(range(4*h));random.Random(37000+seed).shuffle(order)
            accesses={i:[0]+sorted(random.Random(41000+seed*1000+i).sample(range(1,90*DAY),a-1)) for i in order}
            truth=[i//h for i in order]
            for name in config['policies']:
                policy='one_coin' if name.startswith('coin_') else name
                rho=float(name.split('_')[1]) if name.startswith('coin_') else 0.
                records=[{'handle':f'H{p:03d}','observations':generate(accesses[i],updates,i//h,4,
                    config['ttl_days']*DAY,delta*DAY,policy,rho,47000+seed*1000+i)} for p,i in enumerate(order)]
                feats=anonymous_features(records,public,config['ttl_days']*DAY,delta*DAY)
                pred,dist,shared=average_linkage(feats,4)
                met=cluster_metrics(truth,pred,dist)
                shuffled=truth[:];random.Random(53000+seed).shuffle(shuffled)
                rows.append({'holders_per_issuer':h,'holders':4*h,'accesses':a,'nu':nu,'delta_days':delta,
                    'seed':seed,'policy':name,'publications':len(public),'shared_features_mean':shared,
                    'observed_feature_fraction':sum(v is not None for f in feats for v in f)/(4*h*len(public)) if public else 0.,
                    'shuffled_truth_ari':adjusted_rand(shuffled,pred),**met})
                decisions+=4*h*a
                if (h,a,nu,delta,seed,name)==(8,100,12,0,0,'selective'):
                    dump(out/'clustering_example_public.json',{'updates':public,'holders':records,'ttl':config['ttl_days']*DAY,'delta':0})
                    dump(out/'clustering_example_truth.json',[{'handle':r['handle'],'issuer':j} for r,j in zip(records,truth)])
                    dump(out/'clustering_example_predictions.json',{'labels':pred,'metrics':met,'known_anchor_handle':'H000'})
    csvwrite(out/'clustering_runs.csv',rows)
    fields=['ari','pair_auc','pair_precision','pair_recall','anchor_coverage','anchor_wrong_fraction',
            'shared_features_mean','observed_feature_fraction','shuffled_truth_ari']
    csvwrite(out/'clustering_summary.csv',summarize(rows,['holders_per_issuer','accesses','nu','delta_days','policy'],fields))
    controls=[]
    truth=[j for j in range(4) for _ in range(8)]
    random.Random(83000).shuffle(truth)
    for label,features in [('all_common_responses',[[1]*12 for _ in truth]),
                           ('no_publications',[[] for _ in truth])]:
        pred,dist,_=average_linkage(features,4)
        value=cluster_metrics(truth,pred,dist)
        assert value['pair_auc']==.5
        controls.append({'control':label,'pair_auc':value['pair_auc'],'ari':value['ari'],
                         'interpretation':'forced clusters may be arbitrary; pair scores contain no information'})
    dump(out/'clustering_controls.json',{'controls':controls,
         'anonymous_API_rejects_issuer_fields':'unit tested',
         'issuer_name_permutation':'public projection and pairwise same-issuer truth invariant',
         'truth_shuffle':'included for every run in clustering_runs.csv'})
    return {'clustering_runs':len(rows),'clustering_decisions':decisions}


def run_economics(out,shapes,gas):
    weekly=next(w for w in shapes if len(w['updates'])==12 and len(w['accesses'])==100 and w['delta']==0)
    cases=[];coalitions=[];allocations=[];paired=[]
    for case,h in [('weekly_A4',1),('weekly_A32',8),('asymmetric_A32',8)]:
        updates=weekly['updates'] if case.startswith('weekly') else make_updates([1,3,6,12],61001)
        by_issuer={j:sum(u['issuer']==j for u in updates) for j in range(4)}
        totals={name:{'cost':0,'authorizations':0} for name in ['selective','common','coin_0.75','coin_0.95']}
        for target in range(4):
            schedules=[weekly['accesses'] if case.startswith('weekly') else
                [0]+sorted(random.Random(67000+target*100+p).sample(range(1,90*DAY),99)) for p in range(h)]
            foreign=[j for j in range(4) if j!=target];costs={}
            for bits in itertools.product([0,1],repeat=3):
                subset=tuple(j for j,b in zip(foreign,bits) if b)
                relevant=[u for u in updates if u['issuer']==target or u['issuer'] in subset]
                traces=[generate(a,relevant,target,4,30*DAY,0,'common') for a in schedules]
                costs[frozenset(subset)]=sum(gas_cost(obs,gas) for obs in traces)
            baseline=costs[frozenset()];extra=costs[frozenset(foreign)]-baseline
            assert extra>=0
            for subset,cost in sorted(costs.items(),key=lambda p:(len(p[0]),sorted(p[0]))):
                coalitions.append({'case':case,'target_issuer':target+1,'holders':h,
                    'foreign_issuers':';'.join(str(j+1) for j in sorted(subset)) or 'none',
                    'access_gas_proxy':cost,'extra_gas_vs_own_only':cost-baseline})
            shares={}
            for payer in foreign:
                share=0.
                others=[j for j in foreign if j!=payer]
                for bits in itertools.product([0,1],repeat=2):
                    subset=frozenset(j for j,b in zip(others,bits) if b)
                    marginal=costs[subset|{payer}]-costs[subset]
                    assert marginal>=0
                    share+=math.factorial(len(subset))*math.factorial(2-len(subset))/math.factorial(3)*marginal
                shares[payer]=share
            assert abs(sum(shares.values())-extra)<1e-7
            denominator=sum(by_issuer[j] for j in foreign)
            for payer in foreign:
                for rule,value in [('publication_frequency',extra*by_issuer[payer]/denominator if denominator else 0.),('shapley_externality',shares[payer])]:
                    allocations.append({'case':case,'rule':rule,'paying_issuer':payer+1,'holder_group_issuer':target+1,
                        'publication_count':by_issuer[payer],'reimbursement_gas_equivalent':value,
                        'resource_cost_effect':0,'scope':'transfer allocated to holders of target issuer; gas not reduced'})
            for p,a in enumerate(schedules):
                common=generate(a,updates,target,4,30*DAY,0,'common')
                selective=generate(a,updates,target,4,30*DAY,0,'selective')
                for c,s in zip(common,selective):
                    paired.append({'case':case,'holder':f'I{target+1}H{p+1}','holder_issuer':target+1,'at':c['at'],
                        'common_full':int(c['refresh']),'selective_full':int(s['refresh']),
                        'signed_incremental_gas':(int(c['refresh'])-int(s['refresh']))*(gas['reauthorize']-gas['hit'])})
                for name,obs in [('common',common),('selective',selective)]:
                    totals[name]['cost']+=gas_cost(obs,gas);totals[name]['authorizations']+=sum(x['refresh'] for x in obs)
                for rho in [.75,.95]:
                    # Paired Monte Carlo only for the asymmetric handoff; exact
                    # weekly expectations are inserted below.
                    traces=[generate(a,updates,target,4,30*DAY,0,'one_coin',rho,71000+p+100*target+1000*s) for s in range(20)]
                    totals[f'coin_{rho}']['cost']+=statistics.fmean(gas_cost(obs,gas) for obs in traces)
                    totals[f'coin_{rho}']['authorizations']+=statistics.fmean(sum(x['refresh'] for x in obs) for obs in traces)
        for name,values in totals.items():
            exact=case.startswith('weekly')
            if exact and name.startswith('coin_'):
                rho=float(name.split('_')[1]);r=4+9*rho
                values={'cost':4*h*(gas['first']+(r-1)*gas['reauthorize']+(100-r)*gas['hit']), 'authorizations':4*h*r}
            cases.append({'case':case,'policy':name,'active_holders':4*h,'accesses_per_holder':100,
                'authorizations_total':values['authorizations'],'holder_access_gas_proxy':values['cost'],
                'premium_gas_vs_selective':values['cost']-totals['selective']['cost'],
                'publication_count':len(updates),'evidence':'exact expectation' if exact and name.startswith('coin') else '20-seed mean' if name.startswith('coin') else 'deterministic model'})
        difference=totals['common']['cost']-totals['selective']['cost']
        assert sum(r['signed_incremental_gas'] for r in paired if r['case']==case)==difference
        for rule in ['publication_frequency','shapley_externality']:
            assert abs(sum(r['reimbursement_gas_equivalent'] for r in allocations if r['case']==case and r['rule']==rule)-difference)<1e-6
    csvwrite(out/'economic_cases.csv',cases)
    csvwrite(out/'coalition_costs.csv',coalitions)
    csvwrite(out/'compensation_reference.csv',allocations)
    csvwrite(out/'paired_cost_events.csv',paired)
    return {'economic_cases':3,'economic_coalitions':len(coalitions),'compensation_rows':len(allocations),'paired_cost_events':len(paired)}


def run_extensions(out,shapes,plan,gas):
    stats=exact_checks(out,gas);print('Conditional proof checks and exact coin filter PASS',flush=True)
    stats.update(weekly_exact(out,gas));print('Weekly exact frontier PASS',flush=True)
    stats.update(run_clustering(out,plan));print('Anonymous clustering complete',flush=True)
    stats.update(run_economics(out,shapes,gas));print('Economic quantities and budget balance PASS',flush=True)
    return stats
