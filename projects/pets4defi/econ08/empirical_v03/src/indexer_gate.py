#!/usr/bin/env python3
"""EAS indexer feasibility audit; distinct from complete chain-log validation."""
import argparse
import collections
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.request
from acquire import timestamp, canonical, save_json

ENDPOINTS={'ethereum':'https://easscan.org/graphql','base':'https://base.easscan.org/graphql','optimism':'https://optimism.easscan.org/graphql'}


def query(url,text,folder):
    key=hashlib.sha256(text.encode()).hexdigest()
    file=folder/(key+'.json')
    if file.exists():return json.loads(file.read_text())
    request=urllib.request.Request(url,canonical({'query':text}),{'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=35) as response:result=json.load(response)
    if result.get('errors'):raise ValueError(str(result['errors']))
    save_json(file,result)
    return result


def audit(name,folder,spec):
    url=ENDPOINTS[name];folder=Path(folder)/name;folder.mkdir(parents=True,exist_ok=True)
    start=timestamp(spec['window_start']);end=timestamp(spec['window_end_exclusive'])
    report=dict(chain=name,endpoint=url,start=spec['window_start'],end_exclusive=spec['window_end_exclusive'],
                indexer_pagination_complete=False,chain_log_coverage_verified=False,
                interpretation='Indexer candidate screen only; not a chain-completeness certificate',errors=[])
    all_rows=[];cursor=None
    try:
        latest=query(url,'{attestations(take:1,orderBy:{time:desc},where:{isOffchain:{equals:false}}){time}}',folder)
        report['latest_indexed_issuance_time']=latest['data']['attestations'][0]['time']
        for page in range(1000):
            after='' if cursor is None else ', id:{gt:'+json.dumps(cursor)+'}'
            where=f'revoked:{{equals:true}},isOffchain:{{equals:false}},revocationTime:{{gte:{start},lt:{end}}}{after}'
            text='{attestations(take:500,orderBy:{id:asc},where:{'+where+'}){id attester schemaId time revocationTime isOffchain}}'
            rows=query(url,text,folder)['data']['attestations']
            if any(r['isOffchain'] or not start<=r['revocationTime']<end for r in rows):raise ValueError('Indexer filter mismatch')
            if rows and (rows!=sorted(rows,key=lambda r:r['id']) or (cursor and rows[0]['id']<=cursor)):raise ValueError('Unstable pagination')
            all_rows.extend(rows)
            if len(rows)<500:
                report['indexer_pagination_complete']=True;break
            cursor=rows[-1]['id']
        else:raise ValueError('Pagination safety cap reached')
    except Exception as exc:report['errors'].append(str(exc))
    save_json(folder/'revocations.json',all_rows)
    by=collections.defaultdict(list)
    for row in all_rows:by[row['attester'].lower()].append(row)
    candidates=[]
    for index,(attester,rows) in enumerate(sorted(by.items(),key=lambda kv:(-len(kv[1]),kv[0]))):
        days=len({r['revocationTime']//86400 for r in rows})
        entry=dict(local_id=f'attester_{index+1}',revocations=len(rows),distinct_utc_days=days,schemas=len({r['schemaId'] for r in rows}),attestations_before_end=None,qualifies=False)
        if days>=spec['selection']['min_distinct_revocation_days_per_issuer']:
            try:
                q='{aggregateAttestation(where:{attester:{equals:'+json.dumps(rows[0]['attester'])+'},isOffchain:{equals:false},time:{lt:'+str(end)+'}}){_count{_all}}}'
                count=query(url,q,folder)['data']['aggregateAttestation']['_count']['_all']
                entry['attestations_before_end']=count
                entry['qualifies']=count>=spec['selection']['min_attestations_per_issuer_before_window_end']
            except Exception as exc:
                entry['count_error']=str(exc);entry['qualifies']=None
        candidates.append(entry)
    report.update(onchain_revocations_returned=len(all_rows),attesters_returned=len(by),candidates=candidates,
                  qualifying_attesters=sum(c['qualifies'] is True for c in candidates),
                  revocations_sha256=hashlib.sha256((folder/'revocations.json').read_bytes()).hexdigest())
    # Cross-check the paginated row count using a separate aggregate query.
    if report['indexer_pagination_complete']:
        try:
            q=f'{{aggregateAttestation(where:{{revoked:{{equals:true}},isOffchain:{{equals:false}},revocationTime:{{gte:{start},lt:{end}}}}}){{_count{{_all}}}}}}'
            count=query(url,q,folder)['data']['aggregateAttestation']['_count']['_all']
            report['aggregate_revocation_count']=count
            report['aggregate_matches_pagination']=count==len(all_rows)
        except Exception as exc:report['aggregate_count_error']=str(exc)
    save_json(folder/'report.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-out',required=True);p.add_argument('--summary',required=True)
    args=p.parse_args();spec=json.loads((Path(__file__).parents[1]/'config/protocol.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        reports=list(pool.map(lambda name:audit(name,args.private_out,spec),ENDPOINTS))
    complete=all(r['indexer_pagination_complete'] and r.get('aggregate_matches_pagination') and r.get('latest_indexed_issuance_time',0)>=timestamp(spec['window_end_exclusive']) for r in reports)
    qualified=sum(r['qualifying_attesters'] for r in reports)
    potential=sum(c['distinct_utc_days']>=spec['selection']['min_distinct_revocation_days_per_issuer'] for r in reports for c in r['candidates'])
    counts_known=all(c['qualifies'] is not None for r in reports for c in r['candidates'])
    gate='INDEXER_CANDIDATE_PASS' if qualified>=spec['selection']['min_issuers'] else 'INDEXER_INSUFFICIENT' if complete and (counts_known or potential<spec['selection']['min_issuers']) else 'UNKNOWN'
    summary=dict(date='2026-11-17',gate=gate,
                 chain_validated_gate='UNKNOWN',qualifying_attesters_returned=qualified,
                 reports=reports,notes=['Incomplete acquisition is not zero revocations.','Indexer counts require chain-log coverage validation.','No real EAS-to-DeFi holder mapping is inferred.'])
    save_json(Path(args.summary),summary);print(json.dumps(summary),flush=True)
