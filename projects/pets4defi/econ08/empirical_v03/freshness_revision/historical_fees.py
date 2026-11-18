"""Historical Base L2 base-fee and L1 oracle quotes for fixed unsigned envelopes."""
import concurrent.futures
import csv
import datetime as dt
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
RPC = os.environ.get("BASE_RPC_URL") or "https://base-rpc.publicnode.com"
ORACLE = "0x420000000000000000000000000000000000000F"
START = dt.datetime(2026, 8, 19, 12, tzinfo=dt.timezone.utc)


def request(url, data=None):
    req = urllib.request.Request(url, json.dumps(data).encode() if data is not None else None,
                                 {"Content-Type":"application/json", "User-Agent":"ECON08-research/1.0"})
    with urllib.request.urlopen(req, timeout=12) as stream:
        return json.load(stream)


def rpc(method, params):
    obj = request(RPC, {"jsonrpc":"2.0","id":1,"method":method,"params":params})
    if obj.get("result") is None:
        raise ValueError(str(obj.get("error", "Missing RPC result"))[:160])
    return obj["result"]


def at_noon(i, templates):
    target = START + dt.timedelta(days=i)
    target_ts = int(target.timestamp())
    base = dict(date=target.date().isoformat(), checkpoint_utc=target.isoformat())
    try:
        # A chain-verified reference block avoids substituting a timestamp service
        # from another chain. Always verify the two bracketing headers.
        n = 51471727 + (target_ts - 1789732801 + 1) // 2
        header = rpc("eth_getBlockByNumber", [hex(n),False])
        if int(header["timestamp"],16) < target_ts:
            n += 1
            header = rpc("eth_getBlockByNumber", [hex(n),False])
        prev = rpc("eth_getBlockByNumber", [hex(n-1),False])
        if not (int(prev["timestamp"],16) < target_ts <= int(header["timestamp"],16) and
                header["parentHash"] == prev["hash"] and int(header["number"],16)==n):
            raise ValueError("Unverified bracketing blocks")
        base.update(block=n, block_hash=header["hash"], l2_base_wei_per_gas=int(header["baseFeePerGas"],16))
    except Exception as e:
        return [dict(base, kind=t["name"], gas=t["gas_used"], status="block_unavailable", detail=str(e)[:150]) for t in templates]
    rows = []
    for template in templates:
        row=dict(base, kind=template["name"], gas=template["gas_used"])
        row["l2_wei"]=row["gas"]*base["l2_base_wei_per_gas"]
        try:
            quoted=rpc("eth_call",[{"to":ORACLE,"data":template["oracle_calldata"]},hex(n)])
            if len(quoted)!=66:
                raise ValueError("Unexpected oracle output")
            row.update(l1_data_wei=int(quoted,16), status="quoted")
            row["l2_plus_l1_wei"]=row["l2_wei"]+row["l1_data_wei"]
        except Exception as e:
            row.update(status="oracle_unavailable",detail=str(e)[:150])
        rows.append(row)
    return rows


if __name__ == "__main__":
    templates=json.loads((ROOT/"results/quote_templates.json").read_text())
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for day in pool.map(lambda i:at_noon(i,templates),range(90)):
            rows.extend(day)
    fields=["date","checkpoint_utc","block","block_hash","l2_base_wei_per_gas","kind","gas","l2_wei",
            "l1_data_wei","l2_plus_l1_wei","status","detail"]
    with (ROOT/"results/base_fee_quotes.csv").open("w") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    print({k:sum(r["status"]==k for r in rows) for k in set(r["status"] for r in rows)})
