#!/usr/bin/env python3
"""Bounded read-only endpoint check; never exports returned live addresses."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
from acquire import SOURCES,rpc,canonical


def probe(name):
    chain,url,addr,topics=SOURCES[name];result=dict(source=name,chain_id=chain,rpc=url,complete_window=False)
    try:
        actual=int(rpc(url,'eth_chainId',[],retries=0),16)
        if actual!=chain:raise ValueError('Wrong chain')
        block=rpc(url,'eth_getBlockByNumber',['finalized',False],retries=0);height=int(block['number'],16)
        logs=rpc(url,'eth_getLogs',[{'address':addr,'topics':[topics[0]],'fromBlock':hex(height-999),'toBlock':hex(height)}],retries=0)
        result.update(status='RECENT_RANGE_READ',first_block=height-999,last_block=height,latest_timestamp=int(block['timestamp'],16),
                      log_count=len(logs),response_sha256=hashlib.sha256(canonical(logs)).hexdigest())
    except Exception as exc:result.update(status='UNAVAILABLE',error=str(exc))
    return result


if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(probe,['eas_ethereum','eas_base','eas_optimism']))
    Path(sys.argv[1]).write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows),flush=True)
