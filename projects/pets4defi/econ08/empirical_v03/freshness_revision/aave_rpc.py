"""One public RPC acquisition for Aave Base. Local caches are private. Release aggregate bins."""
import argparse
import collections
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"src"))
from acquire import SUPPLY_AAVE, WITHDRAW_AAVE, SOURCES
from traces import decode

UTC=dt.timezone.utc
EPOCH=int(dt.datetime(2026,5,21,tzinfo=UTC).timestamp())
END=EPOCH+180*86400
RPC=os.environ.get("BASE_RPC_URL") or "https://base-rpc.publicnode.com"
POOL=SOURCES["aave_base"][2].lower()


def http(url,obj=None):
    req=urllib.request.Request(url,json.dumps(obj).encode() if obj else None,{"Content-Type":"application/json","User-Agent":"ECON08-aggregate-research/1"})
    with urllib.request.urlopen(req,timeout=22) as r:return json.load(r)


def rpc(method,params):
    reply=http(RPC,dict(jsonrpc="2.0",id=1,method=method,params=params))
    if reply.get("result") is None:raise ValueError(str(reply.get("error","missing result"))[:200])
    return reply["result"]


def header(number):
    h=rpc("eth_getBlockByNumber",[hex(number),False])
    return int(h["timestamp"],16),h["hash"]


def boundary(stamp):
    n=int(http("https://coins.llama.fi/block/base/"+str(stamp))["height"])
    at,_=header(n)
    if at<stamp:n+=1;at,_=header(n)
    before,_=header(n-1)
    if not before<stamp<=at:raise ValueError("Unbracketed timestamp")
    return n,at


def main():
    p=argparse.ArgumentParser();p.add_argument("--private-dir",type=Path,required=True);path=p.parse_args().private_dir
    path.mkdir(exist_ok=True,parents=True,mode=0o700)
    # Calibrate the fixed block-time formula from a successfully checked dated Base header.
    reference_number=51471727
    reference_ts,_=header(reference_number)
    if not 0 <= reference_ts-int(dt.datetime(2026,9,18,12,tzinfo=UTC).timestamp()) < 2:
        raise ValueError("Anchor is not the selected Base noon header")
    first=reference_number+(EPOCH-reference_ts+1)//2
    first_ts=reference_ts+2*(first-reference_number)
    def read_day(day):
        lo=first+day*43200;hi=lo+43199
        cache=path/f"{day:03}.json.gz"
        if cache.exists():return json.loads(gzip.decompress(cache.read_bytes()))
        def logs(a,b):
            query=dict(address=POOL,fromBlock=hex(a),toBlock=hex(b),topics=[[SUPPLY_AAVE,WITHDRAW_AAVE]])
            r=rpc("eth_getLogs",[query])
            if len(r)>=10000 and b>a:
                m=(a+b)//2;return logs(a,m)+logs(m+1,b)
            return r
        # Independent H1/H2 endpoint checks for each day; anchor one returned log's block.
        left,lh=header(lo);last,rh=header(hi)
        if left!=first_ts+day*86400 or last!=left+86398:raise ValueError("Daily block timestamps inconsistent")
        all_logs=[]
        for a in range(lo,hi+1,10000):all_logs+=logs(a,min(a+9999,hi))
        if all_logs:
            selected=all_logs[len(all_logs)//2]
            n=int(selected["blockNumber"],16);when,h=header(n)
            if h!=selected["blockHash"] or when!=left+2*(n-lo):raise ValueError("Interior canonical anchor failed")
        ev=[];ids=set();raw_counts=collections.Counter()
        for row in all_logs:
            n=int(row["blockNumber"],16);ix=int(row["logIndex"],16)
            if row.get("removed") or not lo<=n<=hi or row["address"].lower()!=POOL:raise ValueError("Unexpected event")
            key=(row["blockHash"],ix)
            if key in ids:raise ValueError("Duplicated log")
            ids.add(key);event=decode(row,"aave_base");stamp=left+2*(n-lo)
            if row.get("blockTimestamp") and int(row["blockTimestamp"],16)!=stamp:raise ValueError("Unmatched log timestamp")
            raw_counts[event["kind"]]+=1
            ev.append([event["beneficiary"],row["transactionHash"],stamp])
        obj=dict(day=day,start_block=lo,end_block=hi,first_hash=lh,last_hash=rh,raw_counts=dict(raw_counts),events=ev)
        # NamedTemporaryFile is owner-readable/writable even under a permissive umask.
        with NamedTemporaryFile(dir=path, delete=False) as temporary:
            temporary.write(gzip.compress(json.dumps(obj,separators=(",",":")).encode(),mtime=0))
        os.replace(temporary.name, cache)
        return obj
    def attempt(day):
        for k in range(2):
            try:return read_day(day)
            except Exception as e:
                error=str(e)[:170]
                if "403" in error or "401" in error:break
                if k==0:time.sleep(1)
        return dict(day=day,error=error)
    manifest=[];events_by_wallet=collections.defaultdict(dict);errors=[];total=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as workers:
        for obj in workers.map(attempt,range(180)):
            if "error" in obj:errors.append(obj);continue
            obj=dict(obj);rows=obj.pop("events");total+=len(rows)
            obj["event_count"]=len(rows);manifest.append(obj)
            for wallet,tx,stamp in rows:
                if tx in events_by_wallet[wallet] and events_by_wallet[wallet][tx]!=stamp:raise ValueError("Conflicting tx timestamp")
                events_by_wallet[wallet][tx]=stamp
            if obj["day"]%15==0:print(f"Day {obj['day']}, {total} events",flush=True)
    result=dict(source="Aave v3 Pool, Base mainnet",start_utc="2026-05-21",end_exclusive_utc="2026-11-17",
                covered_days=len(manifest),days_requested=180,coverage="complete_single_provider" if not errors else "partial",
                timestamp_validation="Bracketing range endpoints and one interior event block per nonempty UTC day; fixed two-second Base block cadence.",
                intervals_are_complete=not errors,errors=errors,ranges=manifest)
    # Never join across unavailable days. A contiguous, explicitly dated subset is
    # a secondary descriptive result. Choose the longest block by coverage alone.
    valid=sorted(x["day"] for x in manifest)
    spans=[]
    for day in valid:
        if spans and spans[-1][-1]+1==day:spans[-1].append(day)
        else:spans.append([day])
    if valid:
        span=max(spans,key=lambda x:(len(x),-x[0]))
        lo=EPOCH+span[0]*86400;hi=EPOCH+(span[-1]+1)*86400
        events_by_wallet={w:{tx:t for tx,t in entries.items() if lo<=t<hi}
                          for w,entries in events_by_wallet.items()}
        events_by_wallet={w:e for w,e in events_by_wallet.items() if e}
        result.update(aggregate_span_start=dt.datetime.fromtimestamp(lo,UTC).isoformat(),
                      aggregate_span_end_exclusive=dt.datetime.fromtimestamp(hi,UTC).isoformat(),
                      aggregate_span_days=len(span),span_selection="Longest contiguous covered interval, ties resolved toward earlier start",
                      all_spans=[[s[0],s[-1]] for s in spans])
        total=sum(m["event_count"] for m in manifest if m["day"] in span)
        sizes=collections.Counter(map(len,events_by_wallet.values()));buckets=collections.Counter();same_day=0;total_gaps=0
        for ts in events_by_wallet.values():
            ordered=sorted(ts.values())
            if len(ordered)<3:continue
            for a,b in zip(ordered,ordered[1:]):
                gap=b-a;name=next((k for lim,k in [(1,'same_timestamp'),(3600,'under_1h'),(21600,'1h_to_6h'),(86400,'6h_to_1d'),(604800,'1d_to_7d'),(2592000,'7d_to_30d')] if gap<lim),'30d_or_more')
                buckets[name]+=1;total_gaps+=1;same_day+=a//86400==b//86400
        result.update(event_count=total,distinct_wallets=len(events_by_wallet),unique_wallet_transactions=sum(k*v for k,v in sizes.items()),
                      wallets_one=sizes[1],wallets_two=sizes[2],wallets_three_plus=sum(v for k,v in sizes.items() if k>=3),
                      gaps=total_gaps,gap_distribution=dict(buckets),same_utc_day_gaps=same_day)
        assert total_gaps==sum((k-1)*v for k,v in sizes.items() if k>=3)
    (HERE/"results/aave_interval_coverage.json").write_text(json.dumps(result,indent=2)+"\n")
    print('Covered',len(manifest),'of 180 days. Gaps:',result.get("gaps"),flush=True)


if __name__=="__main__":
    main()
