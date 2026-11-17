"""Linea Verax descriptive screen with no holder fields in the query or output."""
import collections
import json
import urllib.request
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent
URL="https://api.studio.thegraph.com/query/67521/verax-v2-linea/v0.0.1"
BACKUP="https://api.goldsky.com/api/public/project_clxx488osyuf501vygg71f86w/subgraphs/verax-v2-linea/0.0.1/gn"
START=int(datetime(2026,5,21,tzinfo=timezone.utc).timestamp())
END=int(datetime(2026,11,17,tzinfo=timezone.utc).timestamp())


def query(url,gql):
    r=urllib.request.Request(url,json.dumps({"query":gql}).encode(),{"Content-Type":"application/json"})
    with urllib.request.urlopen(r,timeout=15) as resp:j=json.load(resp)
    if "errors" in j:raise ValueError(str(j["errors"])[:190])
    return j["data"]


def screen(url):
    meta=query(url,'{_meta {hasIndexingErrors block {number hash timestamp}}}')['_meta']
    if meta['hasIndexingErrors'] or int(meta['block']['timestamp'])<END:raise ValueError("Subgraph watermark below window or indexing errors")
    by=collections.defaultdict(list);portals=set();cursor=""
    while True:
        rows=query(url,'{attestations(first:1000,orderBy:id,orderDirection:asc,where:{revoked:true,revocationDate_gte:"'+str(START)+'",revocationDate_lt:"'+str(END)+'",id_gt:"'+cursor+'"}){id attester portal{id} revocationDate}}')['attestations']
        if not rows:break
        for r in rows:
            if r['id']<=cursor:raise ValueError("Cursor did not advance")
            cursor=r['id'];at=int(r['revocationDate'])
            if not START<=at<END:raise ValueError("Invalid revocation date")
            by[r['attester']].append(at);portals.add(r['portal']['id'])
        if len(rows)<1000:break
    qual=[]
    for addr,events in by.items():
        if len({e//86400 for e in events})<10:continue
        # Existence threshold rather than interpreting a portal as an issuer.
        rows=query(url,'{attestations(first:1000,where:{attester:"'+addr+'",attestedDate_lt:"'+str(END)+'"}){id}}')['attestations']
        qual.append(len(rows)>=1000)
    return dict(status="indexer_observation",endpoint=url,meta=meta,revocations=sum(map(len,by.values())),
                unique_attesters=len(by),unique_portals=len(portals),qualifying_attesters=sum(qual))


if __name__=="__main__":
    attempts=[]
    for url in (URL,BACKUP):
        try:result=screen(url);break
        except Exception as e:attempts.append({'endpoint':url,'error':str(e)})
    else:result=dict(status="unavailable",revocations=None)
    result.update(failed_attempts=attempts,start_utc="2026-05-21",end_exclusive_utc="2026-11-17",source="Verax Linea v2 only")
    (ROOT/"results/verax180.json").write_text(json.dumps(result,indent=2)+"\n")
    print(result)
